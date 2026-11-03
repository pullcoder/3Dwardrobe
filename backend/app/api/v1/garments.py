import base64
import binascii
import hmac
import json
from datetime import UTC, datetime
from io import BytesIO
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import Response
from PIL import Image, ImageOps
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from app.core.errors import AppError
from app.models import Asset, Garment, LoginSession, Report, User
from app.schemas.garments import (
    Credentials,
    GarmentCreate,
    GarmentPatch,
    ReportInput,
    ReportStatus,
    RightsReviewRequest,
)
from app.services.auth import (
    current_user,
    issue_session,
    limit_auth,
    password_hash,
    token_hash,
    verify_password,
)
from app.services.garment_ai import INFERENCE_LOCK, image_from_bytes
from app.services.generation import invalidate_generation, model_asset, suspend_rights
from app.services.pants_silhouette import PANTS, analyze_pants
from app.services.reconstruction import POLICY_FIELDS, request_rights_review
from app.services.top_silhouette import TOPS, analyze_top
from app.services.uploads import validate_image

router = APIRouter()
SLOTS = {"front", "back", "size", "material", "cutout_front", "cutout_back"}


def database(request):
    return request.app.state.session_factory()


def owned(db, user_id, garment_id):
    row = db.scalar(select(Garment).where(Garment.id == garment_id, Garment.user_id == user_id))
    if not row:
        raise AppError("NOT_FOUND", "의류를 찾을 수 없습니다.", 404)
    return row


def garment_read(db, garment):
    assets = db.scalars(select(Asset).where(Asset.garment_id == garment.id)).all()
    return {
        "id": garment.id,
        "user_id": garment.user_id,
        "info": garment.data,
        "analysis": garment.analysis,
        "created_at": garment.created_at,
        "revision": garment.revision,
        "analysis_status": garment.analysis.get("processing_status", "manual"),
        "model_3d_status": garment.model_3d_status,
        "model_3d_asset_id": garment.model_3d_asset_id,
        **{field: getattr(garment, field) for field in POLICY_FIELDS},
        **{
            field: getattr(garment, field)
            for field in (
                "photo_rights_status",
                "detailed_rights_status",
                "output_rights_status",
                "rights_version",
                "generation_status",
                "generation_job_id",
                "model_format",
                "model_version",
                "generation_error",
                "updated_at",
            )
        },
        "assets": {
            a.slot: {"id": a.id, "content_type": a.mime} for a in assets if a.slot != "model_3d"
        },
    }


@router.post("/auth/register", status_code=201)
def register(body: Credentials, request: Request):
    limit_auth("register")
    with database(request) as db:
        user = User(
            id=str(uuid4()), username=body.username.lower(), password=password_hash(body.password)
        )
        db.add(user)
        try:
            db.flush()
            token = issue_session(db, user.id)
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise AppError("ACCOUNT_UNAVAILABLE", "사용할 수 없는 계정명입니다.", 409) from exc
        return {"token": token, "user": {"id": user.id, "username": user.username}}


@router.post("/auth/login")
def login(body: Credentials, request: Request):
    limit_auth("login")
    with database(request) as db:
        user = db.scalar(select(User).where(User.username == body.username.lower()))
        # 없는 계정도 동일한 비용의 해시를 실행한다.
        valid = verify_password(
            body.password, user.password if user else password_hash("invalid-password")
        )
        if not user or not valid:
            raise AppError("LOGIN_FAILED", "계정명 또는 암호를 확인해 주세요.", 401)
        token = issue_session(db, user.id)
        db.commit()
        return {"token": token, "user": {"id": user.id, "username": user.username}}


@router.post("/auth/logout", status_code=204)
def logout(request: Request):
    with database(request) as db:
        current_user(request, db)
        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        db.execute(delete(LoginSession).where(LoginSession.token_hash == token_hash(token)))
        db.commit()


@router.delete("/auth/account", status_code=204)
def delete_account(body: Credentials, request: Request):
    with database(request) as db:
        user = current_user(request, db)
        if body.username.lower() != user.username or not verify_password(
            body.password, user.password
        ):
            raise AppError("LOGIN_FAILED", "계정명과 암호를 확인해 주세요.", 401)
        db.delete(user)
        db.commit()


@router.get("/garments/capabilities")
def capabilities(request: Request):
    return request.app.state.garment_ai.status()


async def read_image(request: Request):
    if (
        request.headers.get("x-upload-rights") != "confirmed"
        or request.headers.get("x-image-processing-consent") != "confirmed"
    ):
        raise AppError("CONSENT_REQUIRED", "사진 권리와 로컬 서버 처리 안내를 확인해 주세요.")
    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > request.app.state.settings.max_upload_bytes:
            raise AppError("FILE_TOO_LARGE", "사진은 장당 10 MiB 이하여야 합니다.", 413)
        content.extend(chunk)
    mime = request.headers.get("content-type", "").split(";")[0].lower()
    validate_image(bytes(content), mime, request.app.state.settings.max_image_pixels)
    return bytes(content)


@router.post("/garments/{operation}")
async def infer(
    operation: str, request: Request, kind: str = "size", x: float = 0.5, y: float = 0.5
):
    if operation not in {"analyze", "segment", "ocr"}:
        raise AppError("NOT_FOUND", "작업을 찾을 수 없습니다.", 404)
    with database(request) as db:
        current_user(request, db)
    if kind not in {"size", "material"} or not (0 <= x <= 1 and 0 <= y <= 1):
        raise AppError("INVALID_INPUT", "분석 영역을 확인해 주세요.")
    data = await read_image(request)
    if not INFERENCE_LOCK.acquire(blocking=False):
        raise AppError("AI_BUSY", "다른 분석을 처리 중입니다. 잠시 후 재시도해 주세요.", 429)
    try:
        ai = request.app.state.garment_ai
        if operation == "analyze":
            return await run_in_threadpool(ai.classify, image_from_bytes(data))
        if operation == "segment":
            return await run_in_threadpool(ai.segment, image_from_bytes(data), x, y)
        return await run_in_threadpool(ai.ocr, data, kind)
    except AppError:
        raise
    except Exception as exc:
        # 모델/라이브러리 내부 예외에 이미지·경로·OCR 원문이 포함될 수 있어 노출하지 않는다.
        raise AppError(
            "AI_FAILED",
            "로컬 AI 처리에 실패했습니다. 모델 설치 상태를 확인하고 재시도해 주세요.",
            503,
        ) from exc
    finally:
        INFERENCE_LOCK.release()


@router.post("/garments", status_code=201)
def create_garment(body: GarmentCreate, request: Request):
    if (
        request.headers.get("x-upload-rights") != "confirmed"
        or request.headers.get("x-image-storage-consent") != "confirmed"
    ):
        raise AppError("CONSENT_REQUIRED", "사진 권리와 비공개 저장 안내를 확인해 주세요.")
    if "front" not in body.images or set(body.images) - SLOTS:
        raise AppError("INVALID_IMAGES", "앞면 사진 한 장과 허용된 사진만 등록해 주세요.")
    if len(json.dumps(body.analysis)) > 200_000:
        raise AppError("INVALID_ANALYSIS", "분석 정보가 너무 큽니다.", 413)
    with database(request) as db:
        user = current_user(request, db)
        count = len(db.scalars(select(Garment.id).where(Garment.user_id == user.id)).all())
        if count >= 100:
            raise AppError(
                "STORAGE_LIMIT", "로컬 개발 계정은 의류 100벌까지 저장할 수 있습니다.", 413
            )
        garment = Garment(
            id=str(uuid4()),
            user_id=user.id,
            data=body.info.model_dump(),
            # 외곽 분석은 서버가 사진에서 계산한 결과만 채택한다.
            analysis={
                key: value
                for key, value in body.analysis.items()
                if key not in {"silhouette", "silhouette_error"}
            },
            created_at=datetime.now(UTC).isoformat(),
            source_type=body.source_type,
            original_image_retention=body.original_image_retention,
            photo_rights_status="confirmed",
            updated_at=datetime.now(UTC).isoformat(),
        )
        db.add(garment)
        db.flush()
        shape_input = None
        for slot, image in body.images.items():
            try:
                content = base64.b64decode(image.data, validate=True)
            except (ValueError, binascii.Error) as exc:
                raise AppError("INVALID_IMAGE", "이미지 데이터를 확인해 주세요.") from exc
            if len(content) > request.app.state.settings.max_upload_bytes:
                raise AppError("FILE_TOO_LARGE", "사진은 장당 10 MiB 이하여야 합니다.", 413)
            validate_image(content, image.content_type, request.app.state.settings.max_image_pixels)
            if slot.startswith("cutout") and image.content_type != "image/png":
                raise AppError("INVALID_IMAGE", "누끼는 투명 PNG로 등록해 주세요.")
            # EXIF/위치/원래 파일명 제거. JPEG/WebP도 픽셀만 다시 인코딩한다.
            with Image.open(BytesIO(content)) as source:
                clean = ImageOps.exif_transpose(source).convert(
                    "RGBA" if slot.startswith("cutout") else "RGB"
                )
                buffer = BytesIO()
                # 원본 해상도·디코딩된 픽셀을 보존하고 메타데이터만 제거한다.
                clean.save(buffer, format="PNG")
            if slot == "cutout_front" or (slot == "front" and shape_input is None):
                shape_input = buffer.getvalue()
            # 임시 선택 시 누끼를 포함한 모든 픽셀 파생물도 요청 종료 후 폐기한다.
            if body.original_image_retention == "consented_storage":
                db.add(
                    Asset(
                        id=str(uuid4()),
                        garment_id=garment.id,
                        slot=slot,
                        content=buffer.getvalue(),
                        mime="image/png",
                    )
                )
        if body.info.garment_type in PANTS | TOPS and shape_input:
            analysis = dict(garment.analysis)
            try:
                analysis["silhouette"] = (
                    analyze_top if body.info.garment_type in TOPS else analyze_pants
                )(shape_input)
            except AppError as error:
                analysis["silhouette_error"] = error.code
            garment.analysis = analysis
        db.commit()
        return garment_read(db, garment)


@router.get("/garments")
def list_garments(request: Request):
    with database(request) as db:
        user = current_user(request, db)
        return [
            garment_read(db, g)
            for g in db.scalars(
                select(Garment)
                .where(Garment.user_id == user.id)
                .order_by(Garment.created_at.desc())
            )
        ]


@router.get("/garments/{garment_id}")
def get_garment(garment_id: str, request: Request):
    with database(request) as db:
        user = current_user(request, db)
        return garment_read(db, owned(db, user.id, garment_id))


@router.patch("/garments/{garment_id}")
def patch_garment(garment_id: str, body: GarmentPatch, request: Request):
    with database(request) as db:
        user = current_user(request, db)
        garment = owned(db, user.id, garment_id)
        invalidate_generation(db, garment, "GARMENT_UPDATED")
        result = db.execute(
            update(Garment)
            .where(
                Garment.id == garment_id,
                Garment.user_id == user.id,
                Garment.revision == body.revision,
            )
            .values(data=body.info.model_dump(), revision=body.revision + 1)
        )
        if not result.rowcount:
            raise AppError(
                "CONFLICT", "다른 편집이 저장되었습니다. 목록을 다시 불러온 뒤 수정해 주세요.", 409
            )
        db.commit()
        return garment_read(db, db.get(Garment, garment_id))


@router.delete("/garments/{garment_id}", status_code=204)
def delete_garment(garment_id: str, request: Request):
    with database(request) as db:
        user = current_user(request, db)
        db.delete(owned(db, user.id, garment_id))
        db.commit()


@router.post("/garments/{garment_id}/rights-review")
def submit_rights_review(garment_id: str, body: RightsReviewRequest, request: Request):
    with database(request) as db:
        user = current_user(request, db)
        garment = owned(db, user.id, garment_id)
        request_rights_review(db, garment, body)
        db.commit()
        return garment_read(db, garment)


@router.get("/assets/{asset_id}")
def get_asset(asset_id: str, request: Request):
    with database(request) as db:
        user = current_user(request, db)
        asset = db.scalar(
            select(Asset).join(Garment).where(Asset.id == asset_id, Garment.user_id == user.id)
        )
        if not asset:
            raise AppError("NOT_FOUND", "이미지를 찾을 수 없습니다.", 404)
        if asset.slot == "model_3d":
            current = model_asset(db, db.get(Garment, asset.garment_id))
            if current.id != asset.id:
                raise AppError("NOT_FOUND", "모델을 찾을 수 없습니다.", 404)
        return Response(
            asset.content,
            media_type=asset.mime,
            headers={"Content-Disposition": f'inline; filename="{asset.id}"'},
        )


@router.post("/reports", status_code=201)
def create_report(body: ReportInput, request: Request):
    with database(request) as db:
        user = current_user(request, db)
        if body.garment_id:
            garment = owned(db, user.id, body.garment_id)
            if body.kind == "rights":
                suspend_rights(db, garment, "RIGHTS_REPORTED")
        row = Report(id=str(uuid4()), user_id=user.id, **body.model_dump())
        db.add(row)
        db.commit()
        return {"id": row.id, "status": row.status}


@router.get("/reports")
def my_reports(request: Request):
    with database(request) as db:
        user = current_user(request, db)
        return [
            {"id": r.id, "status": r.status}
            for r in db.scalars(select(Report).where(Report.user_id == user.id))
        ]


def require_admin(request):
    secret = request.app.state.settings.admin_review_key
    supplied = request.headers.get("x-admin-review-key", "")
    if not secret or not hmac.compare_digest(secret, supplied):
        raise AppError("FORBIDDEN", "관리자 권한이 필요합니다.", 403)


@router.get("/admin/reports")
def admin_reports(request: Request):
    require_admin(request)
    with database(request) as db:
        return [
            {"id": r.id, "reason": r.reason, "status": r.status, "garment_id": r.garment_id}
            for r in db.scalars(select(Report))
        ]


@router.patch("/admin/reports/{report_id}")
def review_report(report_id: str, body: ReportStatus, request: Request):
    require_admin(request)
    with database(request) as db:
        report = db.get(Report, report_id)
        if not report:
            raise AppError("NOT_FOUND", "신고를 찾을 수 없습니다.", 404)
        report.status = body.status
        db.commit()
        return {"id": report.id, "status": report.status}
