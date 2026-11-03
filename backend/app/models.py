"""3단계 사용자·비공개 의류 저장 스키마. 사진은 공개 파일 경로 없이 DB에 저장한다."""

from sqlalchemy import JSON, Float, ForeignKey, LargeBinary, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(40), unique=True)
    password: Mapped[str] = mapped_column(String(256))


class LoginSession(Base):
    __tablename__ = "login_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    expires_at: Mapped[float] = mapped_column(Float)


class Garment(Base):
    __tablename__ = "garments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    data: Mapped[dict] = mapped_column(JSON)
    analysis: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String(40))
    revision: Mapped[int] = mapped_column(default=1)
    model_3d_status: Mapped[str] = mapped_column(String(20), default="not_implemented")
    model_3d_asset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reconstruction_mode: Mapped[str] = mapped_column(String(1), default="A", server_default="A")
    source_type: Mapped[str] = mapped_column(String(20), default="other", server_default="other")
    rights_status: Mapped[str] = mapped_column(
        String(20), default="unverified", server_default="unverified"
    )
    license_reference: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    original_image_retention: Mapped[str] = mapped_column(
        String(20), default="temporary", server_default="temporary"
    )
    generated_model_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    model_visibility: Mapped[str] = mapped_column(
        String(20), default="private", server_default="private"
    )
    rights_reviewed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    photo_rights_status: Mapped[str] = mapped_column(
        String(20), default="unverified", server_default="unverified"
    )
    detailed_rights_status: Mapped[str] = mapped_column(
        String(20), default="unverified", server_default="unverified"
    )
    output_rights_status: Mapped[str] = mapped_column(
        String(20), default="unverified", server_default="unverified"
    )
    rights_version: Mapped[int] = mapped_column(default=1, server_default="1")
    generation_status: Mapped[str] = mapped_column(
        String(20), default="idle", server_default="idle"
    )
    generation_job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    model_format: Mapped[str | None] = mapped_column(String(10), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    generation_error: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


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
    created_at: Mapped[str] = mapped_column(String(40))
    updated_at: Mapped[str] = mapped_column(String(40))


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


class Asset(Base):
    __tablename__ = "garment_assets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    garment_id: Mapped[str] = mapped_column(
        ForeignKey("garments.id", ondelete="CASCADE"), index=True
    )
    slot: Mapped[str] = mapped_column(String(30))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    mime: Mapped[str] = mapped_column(String(30))


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    garment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reason: Mapped[str] = mapped_column(String(2000))
    status: Mapped[str] = mapped_column(String(20), default="received")
    kind: Mapped[str] = mapped_column(String(20), default="rights", server_default="rights")


class SavedMannequin(Base):
    __tablename__ = "saved_mannequins"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    profile: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String(40))


class Fitting(Base):
    __tablename__ = "fittings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    mannequin_id: Mapped[str | None] = mapped_column(
        ForeignKey("saved_mannequins.id", ondelete="SET NULL"), nullable=True
    )
    slots: Mapped[dict] = mapped_column(JSON)
    adjustments: Mapped[dict] = mapped_column(JSON)
    revision: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[str] = mapped_column(String(40))
    updated_at: Mapped[str] = mapped_column(String(40))


class Outfit(Base):
    __tablename__ = "outfits"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    mannequin_id: Mapped[str | None] = mapped_column(
        ForeignKey("saved_mannequins.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(80))
    slots: Mapped[dict] = mapped_column(JSON)
    adjustments: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String(40))
