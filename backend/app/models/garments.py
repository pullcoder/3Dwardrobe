"""비공개 의류와 에셋의 저장 모델."""

from sqlalchemy import JSON, ForeignKey, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


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


class Asset(Base):
    __tablename__ = "garment_assets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    garment_id: Mapped[str] = mapped_column(
        ForeignKey("garments.id", ondelete="CASCADE"), index=True
    )
    slot: Mapped[str] = mapped_column(String(30))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    mime: Mapped[str] = mapped_column(String(30))
