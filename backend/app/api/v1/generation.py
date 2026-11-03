"""인증된 3D 작업 등록·조회와 증빙 기반 관리자 권한 검토."""

import hashlib
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select, update

from app.api.v1.garments import database, owned, require_admin
from app.core.errors import AppError
from app.models import Garment, RightsEvidence, RightsReview
from app.schemas.garments import RightsDecision
from app.services.auth import current_user
from app.services.generation import (
    enqueue,
    generation_read,
    invalidate_generation,
    model_asset,
    now,
    selected_mode,
    suspend_rights,
)
from app.services.pants_silhouette import PANTS, analyze_pants
from app.services.top_silhouette import TOPS, analyze_top
from app.services.uploads import validate_image

router = APIRouter()


class EmptyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


@router.post("/garments/{garment_id}/silhouette")
async def analyze_silhouette(garment_id: str, request: Request):
    if (
        request.headers.get("x-upload-rights") != "confirmed"
        or request.headers.get("x-image-processing-consent") != "confirmed"
    ):
        raise AppError(
            "CONSENT_REQUIRED", "사진 처리 권한과 형태 분석을 위한 서버 전송에 동의해 주세요."
        )
    with database(request) as db:
        garment = owned(db, current_user(request, db).id, garment_id)
        if not selected_mode(garment):
            raise AppError("RIGHTS_REQUIRED", "현재 사진 처리 권한을 확인해 주세요.", 403)
        if garment.data.get("garment_type") not in PANTS | TOPS:
            raise AppError(
                "UNSUPPORTED_GARMENT",
                "현재 형태 분석은 티셔츠·청바지·슬랙스·반바지를 지원합니다.",
                422,
            )
        revision, rights_version = garment.revision, garment.rights_version
        analyze = analyze_top if garment.data.get("garment_type") in TOPS else analyze_pants
    data = await request.body()
    if len(data) > request.app.state.settings.max_upload_bytes:
        raise AppError("FILE_TOO_LARGE", "사진은 10 MiB 이하여야 합니다.", 413)
    validate_image(
        data,
        request.headers.get("content-type", "").split(";")[0],
        request.app.state.settings.max_image_pixels,
    )
    # CPU 사진 처리 동안 이벤트 루프를 막지 않는다. 원본 픽셀은 저장하지 않는다.
    from starlette.concurrency import run_in_threadpool

    shape = await run_in_threadpool(analyze, data)
    with database(request) as db:
        garment = owned(db, current_user(request, db).id, garment_id)
        if (
            garment.revision != revision
            or garment.rights_version != rights_version
            or not selected_mode(garment)
        ):
            raise AppError(
                "CONFLICT", "분석 중 의류나 권한이 변경되었습니다. 다시 시도해 주세요.", 409
            )
        changed = db.execute(
            update(Garment)
            .where(
                Garment.id == garment.id,
                Garment.revision == revision,
                Garment.rights_version == rights_version,
            )
            .values(analysis={**garment.analysis, "silhouette": shape}, revision=revision + 1)
        )
        if not changed.rowcount:
            raise AppError("CONFLICT", "다른 변경이 저장되었습니다. 다시 시도해 주세요.", 409)
        invalidate_generation(db, garment, "SILHOUETTE_UPDATED")
        db.commit()
        return {
            "silhouette": shape,
            "generation": generation_read(db, garment),
            "revision": garment.revision,
        }


@router.post("/garments/{garment_id}/generate-3d", status_code=202)
def generate(garment_id: str, body: EmptyInput, request: Request):
    with database(request) as db:
        garment = owned(db, current_user(request, db).id, garment_id)
        enqueue(db, garment)
        db.commit()
        return generation_read(db, garment)


@router.get("/garments/{garment_id}/generation-status")
@router.get("/garments/{garment_id}/rights-status")
def status(garment_id: str, request: Request):
    with database(request) as db:
        garment = owned(db, current_user(request, db).id, garment_id)
        return generation_read(db, garment)


@router.get("/garments/{garment_id}/model")
def download_model(garment_id: str, request: Request):
    with database(request) as db:
        garment = owned(db, current_user(request, db).id, garment_id)
        asset = model_asset(db, garment)
        return Response(
            asset.content,
            media_type="model/gltf-binary",
            headers={"Content-Disposition": f'attachment; filename="{garment.id}.glb"'},
        )


@router.delete("/garments/{garment_id}/model", status_code=204)
def remove_model(garment_id: str, request: Request):
    with database(request) as db:
        garment = owned(db, current_user(request, db).id, garment_id)
        invalidate_generation(db, garment, "USER_DELETED")
        db.commit()


@router.post("/garments/{garment_id}/photo-rights-confirmation")
def confirm_photo(garment_id: str, body: EmptyInput, request: Request):
    if request.headers.get("x-upload-rights") != "confirmed":
        raise AppError("CONSENT_REQUIRED", "사진 입력·처리에 필요한 이용 권한을 확인해 주세요.")
    with database(request) as db:
        garment = owned(db, current_user(request, db).id, garment_id)
        statuses = (
            garment.photo_rights_status,
            garment.detailed_rights_status,
            garment.output_rights_status,
        )
        if any(s in {"disputed", "rejected"} for s in statuses):
            raise AppError(
                "RIGHTS_REVIEW_REQUIRED", "권리 신고·철회 상태는 관리자의 재검토가 필요합니다.", 403
            )
        if garment.photo_rights_status not in {"confirmed", "verified"}:
            changed = db.execute(
                update(Garment)
                .where(Garment.id == garment.id, Garment.rights_version == garment.rights_version)
                .values(
                    photo_rights_status="confirmed",
                    rights_version=Garment.rights_version + 1,
                    updated_at=now(),
                )
            )
            if not changed.rowcount:
                raise AppError("CONFLICT", "권한 상태가 변경되었습니다. 다시 확인해 주세요.", 409)
            db.commit()
        return generation_read(db, garment)


@router.post("/garments/{garment_id}/rights-withdraw", status_code=204)
def withdraw(garment_id: str, body: EmptyInput, request: Request):
    with database(request) as db:
        garment = owned(db, current_user(request, db).id, garment_id)
        suspend_rights(db, garment, "RIGHTS_WITHDRAWN")
        db.commit()


@router.post("/garments/{garment_id}/rights-evidence", status_code=201)
async def upload_evidence(garment_id: str, request: Request):
    with database(request) as db:
        owned(db, current_user(request, db).id, garment_id)
    if request.headers.get("x-evidence-storage-consent") != "confirmed":
        raise AppError("CONSENT_REQUIRED", "권리 증빙의 비공개 보관에 동의해 주세요.")
    data = await request.body()
    mime = request.headers.get("content-type", "").split(";")[0].lower()
    if not data or len(data) > 5 * 1024 * 1024:
        raise AppError("INVALID_EVIDENCE", "증빙 파일은 5 MiB 이하로 제출해 주세요.", 413)
    if mime == "application/pdf":
        if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-1024:]:
            raise AppError("INVALID_EVIDENCE", "PDF 파일 형식을 확인해 주세요.")
    elif mime in {"image/png", "image/jpeg", "image/webp"}:
        validate_image(data, mime, request.app.state.settings.max_image_pixels)
    else:
        raise AppError("INVALID_EVIDENCE", "PDF·JPG·PNG·WebP 증빙만 지원합니다.", 415)
    with database(request) as db:
        garment = owned(db, current_user(request, db).id, garment_id)
        if (
            db.scalar(
                select(func.count())
                .select_from(RightsEvidence)
                .where(RightsEvidence.garment_id == garment.id)
            )
            >= 10
        ):
            raise AppError(
                "EVIDENCE_LIMIT", "의류 한 벌당 증빙은 10개까지 제출할 수 있습니다.", 413
            )
        evidence = RightsEvidence(
            id=str(uuid4()),
            garment_id=garment.id,
            content=data,
            mime=mime,
            sha256=hashlib.sha256(data).hexdigest(),
            created_at=now(),
        )
        db.add(evidence)
        db.commit()
        return {"id": evidence.id, "sha256": evidence.sha256}


@router.get("/admin/garments/{garment_id}/rights-evidence")
def list_evidence(garment_id: str, request: Request):
    require_admin(request)
    with database(request) as db:
        return [
            {"id": e.id, "sha256": e.sha256, "content_type": e.mime, "created_at": e.created_at}
            for e in db.scalars(
                select(RightsEvidence).where(RightsEvidence.garment_id == garment_id)
            )
        ]


@router.get("/admin/rights-evidence/{evidence_id}")
def read_evidence(evidence_id: str, request: Request):
    require_admin(request)
    with database(request) as db:
        evidence = db.get(RightsEvidence, evidence_id)
        if not evidence:
            raise AppError("NOT_FOUND", "증빙을 찾을 수 없습니다.", 404)
        return Response(
            evidence.content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{evidence.id}"'},
        )


@router.patch("/admin/garments/{garment_id}/rights-review")
def decide_rights(garment_id: str, body: RightsDecision, request: Request):
    require_admin(request)
    with database(request) as db:
        garment = db.get(Garment, garment_id)
        if not garment:
            raise AppError("NOT_FOUND", "의류를 찾을 수 없습니다.", 404)
        statuses = {
            key: getattr(body, key)
            for key in ("photo_rights_status", "detailed_rights_status", "output_rights_status")
        }
        if "verified" in statuses.values():
            evidence = db.get(RightsEvidence, body.evidence_id) if body.evidence_id else None
            if not evidence or evidence.garment_id != garment.id:
                raise AppError(
                    "EVIDENCE_REQUIRED",
                    "해당 의류의 실제 증빙 문서를 확인하고 판단 근거를 기록해 주세요.",
                )
        invalidate_generation(db, garment, "RIGHTS_CHANGED")
        changed = db.execute(
            update(Garment)
            .where(Garment.id == garment.id, Garment.rights_version == body.rights_version)
            .values(
                **statuses,
                rights_version=Garment.rights_version + 1,
                rights_reviewed_at=now(),
                rights_status="approved"
                if all(s == "verified" for s in statuses.values())
                else "rejected"
                if any(s in {"rejected", "disputed"} for s in statuses.values())
                else "unverified",
            )
        )
        if not changed.rowcount:
            raise AppError("CONFLICT", "권한 상태가 변경되었습니다. 다시 확인해 주세요.", 409)
        garment.reconstruction_mode = selected_mode(garment) or "A"
        db.add(
            RightsReview(
                id=str(uuid4()),
                garment_id=garment.id,
                evidence_id=body.evidence_id,
                decision={**statuses, "rights_version": garment.rights_version},
                notes=body.notes,
                created_at=now(),
            )
        )
        db.commit()
        return generation_read(db, garment)


@router.get("/admin/garments/{garment_id}/rights-reviews")
def review_history(garment_id: str, request: Request):
    require_admin(request)
    with database(request) as db:
        return [
            {
                "id": r.id,
                "evidence_id": r.evidence_id,
                "decision": r.decision,
                "notes": r.notes,
                "created_at": r.created_at,
            }
            for r in db.scalars(
                select(RightsReview)
                .where(RightsReview.garment_id == garment_id)
                .order_by(RightsReview.created_at)
            )
        ]
