from typing import Literal

from pydantic import BaseModel


class UploadValidationRead(BaseModel):
    """이미지의 형식만 확인한 결과이며 AI 분석 결과가 아니다."""

    content_type: str
    size_bytes: int
    width: int
    height: int
    retained: Literal[False] = False
    ai_processed: Literal[False] = False
