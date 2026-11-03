"""마네킹 스냅샷·피팅·코디의 저장 모델."""

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


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
