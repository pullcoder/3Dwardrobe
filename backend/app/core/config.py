from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """루트 .env를 명시적으로 읽으며 현재 앱의 로컬 실행만 허용한다."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    app_env: Literal["development", "test"] = "development"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    max_upload_bytes: int = 10 * 1024 * 1024
    max_image_pixels: int = 20_000_000
    max_request_bytes: int = 85_000_000
    database_url: str = "sqlite:///storage/stylefit.db"
    admin_review_key: str = ""
