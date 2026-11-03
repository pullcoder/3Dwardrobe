"""3단계 복원 정책. 증빙 참조 접수는 권한 승인이나 B모드 활성화가 아니다."""

from sqlalchemy import update

from app.core.errors import AppError
from app.models import Garment, RightsEvidence
from app.services.generation import invalidate_generation

POLICY_FIELDS = (
    "reconstruction_mode",
    "source_type",
    "rights_status",
    "license_reference",
    "original_image_retention",
    "generated_model_path",
    "model_visibility",
    "rights_reviewed_at",
)


def request_rights_review(db, garment, body):
    if body.evidence_id:
        evidence = db.get(RightsEvidence, body.evidence_id)
        if not evidence or evidence.garment_id != garment.id:
            raise AppError("NOT_FOUND", "해당 의류의 증빙을 찾을 수 없습니다.", 404)
    if garment.rights_status == "pending":
        raise AppError("REVIEW_PENDING", "이미 권한 검토를 요청했습니다.", 409)
    invalidate_generation(db, garment, "RIGHTS_REVIEW_REQUESTED", bump_rights=True)
    result = db.execute(
        update(Garment)
        .where(Garment.id == garment.id, Garment.revision == body.revision)
        .values(
            license_reference=body.license_reference,
            rights_status="pending",
            rights_reviewed_at=None,
            reconstruction_mode="A",
            revision=body.revision + 1,
        )
    )
    if not result.rowcount:
        raise AppError("CONFLICT", "의류를 다시 불러온 뒤 검토를 요청해 주세요.", 409)
    db.execute(
        update(Garment)
        .where(Garment.id == garment.id)
        .values(detailed_rights_status="pending", output_rights_status="pending")
    )
