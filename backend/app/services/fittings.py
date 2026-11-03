"""본인 소유권·현재 모델 권한·고정 모델 버전을 검사하는 피팅 저장 서비스."""

from uuid import uuid4

from sqlalchemy import delete, func, select, update

from app.core.errors import AppError
from app.models import Fitting, Garment, GenerationJob, Outfit, SavedMannequin
from app.schemas.fittings import FitAdjustment
from app.services.generation import model_asset, now

PARTS = ("top", "bottom", "outer")


def owned_row(db, model, user_id, row_id):
    row = db.scalar(select(model).where(model.id == row_id, model.user_id == user_id))
    if not row:
        raise AppError("NOT_FOUND", "본인 데이터를 찾을 수 없습니다.", 404)
    return row


def resource(db, user_id, garment_id):
    garment = owned_row(db, Garment, user_id, garment_id)
    asset = model_asset(db, garment)
    job = db.get(GenerationJob, garment.generation_job_id) if garment.generation_job_id else None
    metadata = job.result_metadata if job else None
    if (
        not metadata
        or metadata.get("unit") != "meter"
        or metadata.get("coordinate_system") != "y_up_z_front"
        or metadata.get("category") != garment.data["category"]
    ):
        raise AppError(
            "INCOMPATIBLE_MODEL", "모델 좌표계·단위·카테고리 메타데이터가 호환되지 않습니다.", 422
        )
    return {
        "garment_id": garment.id,
        "name": garment.data["name"],
        "category": garment.data["category"],
        "info": garment.data,
        "model_asset_id": asset.id,
        "metadata": metadata,
        "reconstruction_mode": garment.reconstruction_mode,
        "rights_version": garment.rights_version,
        "status": "available",
    }


def validate_slots(db, user_id, slots):
    result = {}
    for part in PARTS:
        garment_id = slots.get(part)
        if not garment_id:
            result[part] = None
            continue
        model = resource(db, user_id, garment_id)
        if model["category"] != part:
            raise AppError("CATEGORY_MISMATCH", "의류 카테고리와 피팅 슬롯을 확인해 주세요.", 422)
        result[part] = {"garment_id": garment_id, "model_asset_id": model["model_asset_id"]}
    return result


def read_state(db, row):
    mannequin = db.get(SavedMannequin, row.mannequin_id) if row.mannequin_id else None
    warnings = []
    if not mannequin or mannequin.user_id != row.user_id:
        warnings.append("저장된 마네킹이 없습니다. 체형을 다시 선택해 주세요.")
        mannequin = None
    slots = {}
    for part in PARTS:
        reference = row.slots.get(part)
        if not reference:
            slots[part] = None
            continue
        try:
            model = resource(db, row.user_id, reference["garment_id"])
            if model["category"] != part or model["model_asset_id"] != reference["model_asset_id"]:
                raise AppError("MODEL_CHANGED", "저장 이후 의류 모델이 변경되었습니다.", 409)
            slots[part] = model
        except AppError as error:
            slots[part] = {
                "garment_id": reference["garment_id"],
                "status": "unavailable",
                "reason": error.code,
            }
            warnings.append(f"{part}: 삭제·권한 변경·모델 재생성으로 사용할 수 없는 의류입니다.")
    return {
        "id": row.id,
        "mannequin_id": row.mannequin_id,
        "mannequin": mannequin.profile if mannequin else None,
        "slots": slots,
        "adjustments": row.adjustments,
        "created_at": row.created_at,
        "warnings": warnings,
        "revision": row.revision if isinstance(row, Fitting) else None,
        "name": row.name if isinstance(row, Outfit) else None,
    }


def prune_mannequins(db, user_id):
    db.flush()
    db.execute(
        delete(SavedMannequin).where(
            SavedMannequin.user_id == user_id,
            SavedMannequin.id.not_in(
                select(Fitting.mannequin_id).where(Fitting.mannequin_id.is_not(None))
            ),
            SavedMannequin.id.not_in(
                select(Outfit.mannequin_id).where(Outfit.mannequin_id.is_not(None))
            ),
        )
    )


def save_fitting(db, user_id, body, row=None):
    if not body.body_storage_consent:
        raise AppError(
            "BODY_STORAGE_CONSENT",
            "코디 복원을 위한 최소 체형 수치의 비공개 서버 저장에 동의해 주세요.",
        )
    if (
        row is None
        and db.scalar(select(func.count()).select_from(Fitting).where(Fitting.user_id == user_id))
        >= 100
    ):
        raise AppError("STORAGE_LIMIT", "피팅 세션은 계정당 100개까지 저장할 수 있습니다.", 413)
    slots = validate_slots(db, user_id, body.slots)
    adjustments = {part: body.adjustments.get(part, FitAdjustment()).model_dump() for part in PARTS}
    mannequin = SavedMannequin(
        id=str(uuid4()), user_id=user_id, profile=body.mannequin.model_dump(), created_at=now()
    )
    db.add(mannequin)
    db.flush()
    if row is None:
        row = Fitting(
            id=str(uuid4()),
            user_id=user_id,
            mannequin_id=mannequin.id,
            slots=slots,
            adjustments=adjustments,
            created_at=now(),
            updated_at=now(),
        )
        db.add(row)
    else:
        changed = db.execute(
            update(Fitting)
            .where(
                Fitting.id == row.id, Fitting.user_id == user_id, Fitting.revision == body.revision
            )
            .values(
                mannequin_id=mannequin.id,
                slots=slots,
                adjustments=adjustments,
                revision=Fitting.revision + 1,
                updated_at=now(),
            )
        )
        if not changed.rowcount:
            raise AppError("CONFLICT", "피팅 설정이 변경되었습니다. 다시 불러와 주세요.", 409)
    db.flush()
    prune_mannequins(db, user_id)
    return row


def save_outfit(db, user_id, body):
    fitting = owned_row(db, Fitting, user_id, body.fitting_id)
    if not any(fitting.slots.values()):
        raise AppError("EMPTY_OUTFIT", "코디에 의류를 한 벌 이상 선택해 주세요.")
    current = read_state(db, fitting)
    if current["warnings"]:
        raise AppError(
            "STALE_FITTING", "사용할 수 없는 의류/마네킹을 확인하고 피팅을 다시 저장해 주세요.", 409
        )
    if db.scalar(select(func.count()).select_from(Outfit).where(Outfit.user_id == user_id)) >= 100:
        raise AppError("STORAGE_LIMIT", "코디는 계정당 100개까지 저장할 수 있습니다.", 413)
    row = Outfit(
        id=str(uuid4()),
        user_id=user_id,
        mannequin_id=fitting.mannequin_id,
        name=body.name,
        slots=fitting.slots.copy(),
        adjustments=fitting.adjustments.copy(),
        created_at=now(),
    )
    db.add(row)
    db.flush()
    return row
