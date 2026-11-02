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
