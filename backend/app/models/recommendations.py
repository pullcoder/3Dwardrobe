"""계정별 취향과 비공개 추천·저장·피드백. 원본 사진과 체형 수치는 보관하지 않는다."""

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class StylePreference(Base):
    __tablename__ = "style_preferences"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    data: Mapped[dict] = mapped_column(JSON)
    revision: Mapped[int] = mapped_column(default=1)
    updated_at: Mapped[str] = mapped_column(String(40))


class Recommendation(Base):
    __tablename__ = "recommendations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    slots: Mapped[dict] = mapped_column(JSON)
    model_refs: Mapped[dict] = mapped_column(JSON)
    details: Mapped[dict] = mapped_column(JSON)
    mannequin_id: Mapped[str | None] = mapped_column(
        ForeignKey("saved_mannequins.id", ondelete="SET NULL"), nullable=True
    )
    feedback: Mapped[str] = mapped_column(String(12), default="none")
    feedback_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    saved_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[str] = mapped_column(String(40))
