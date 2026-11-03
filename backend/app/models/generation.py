"""생성 작업과 권리 증빙·검토의 저장 모델."""

from sqlalchemy import JSON, Float, ForeignKey, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GenerationJob(Base):
    __tablename__ = "generation_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    garment_id: Mapped[str] = mapped_column(
        ForeignKey("garments.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    stage: Mapped[str] = mapped_column(String(30), default="queued")
    mode: Mapped[str] = mapped_column(String(1))
    snapshot: Mapped[dict] = mapped_column(JSON)
    result_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rights_version: Mapped[int] = mapped_column()
    garment_revision: Mapped[int] = mapped_column()
    lease_until: Mapped[float | None] = mapped_column(Float, nullable=True)
    claim_token: Mapped[str | None] = mapped_column(String(36), nullable=True)
    attempts: Mapped[int] = mapped_column(default=0)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    failure_stage: Mapped[str | None] = mapped_column(String(30), nullable=True)
    exception_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[str] = mapped_column(String(40))
    updated_at: Mapped[str] = mapped_column(String(40))


class GenerationWorker(Base):
    __tablename__ = "generation_workers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    engine_version: Mapped[str] = mapped_column(String(40))
    last_seen: Mapped[float] = mapped_column(Float, index=True)


class RightsEvidence(Base):
    __tablename__ = "rights_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    garment_id: Mapped[str] = mapped_column(
        ForeignKey("garments.id", ondelete="CASCADE"), index=True
    )
    content: Mapped[bytes] = mapped_column(LargeBinary)
    mime: Mapped[str] = mapped_column(String(30))
    sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[str] = mapped_column(String(40))


class RightsReview(Base):
    __tablename__ = "rights_reviews"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    garment_id: Mapped[str] = mapped_column(
        ForeignKey("garments.id", ondelete="CASCADE"), index=True
    )
    evidence_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    decision: Mapped[dict] = mapped_column(JSON)
    notes: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[str] = mapped_column(String(40))
