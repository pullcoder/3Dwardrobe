from fastapi import APIRouter, Request

from app.core.errors import AppError
from app.schemas.uploads import UploadValidationRead
from app.services.uploads import validate_image

router = APIRouter()


@router.get("/health")
def health(request: Request) -> dict:
    """실제 제공 중인 기능만 반환한다. DB·AI 연결을 의미하지 않는다."""
    return {
        "status": "ok",
        "mode": "local_preview",
        "features": {
            "image_validation": True,
            "ai": all(
                request.app.state.garment_ai.status()[key]
                for key in ("classification", "segmentation", "ocr")
            ),
            "storage": True,
            "auth": True,
        },
    }


@router.post("/uploads/validate", response_model=UploadValidationRead)
async def validate_upload(request: Request) -> UploadValidationRead:
    """원시 이미지 스트림을 제한 크기 안에서 받아 검증 후 폐기한다."""
    if request.headers.get("x-upload-rights") != "confirmed":
        raise AppError("RIGHTS_REQUIRED", "사진 이용 권리와 서버 전송 안내를 확인해 주세요.")
    settings = request.app.state.settings
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    declared_size = request.headers.get("content-length")
    if declared_size:
        try:
            length = int(declared_size)
        except ValueError as exc:
            raise AppError("INVALID_LENGTH", "파일 크기를 확인할 수 없습니다.") from exc
        if length < 0:
            raise AppError("INVALID_LENGTH", "파일 크기를 확인할 수 없습니다.")
        if length > settings.max_upload_bytes:
            raise AppError("FILE_TOO_LARGE", "사진은 한 장당 10 MiB 이하여야 합니다.", 413)
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > settings.max_upload_bytes:
            raise AppError("FILE_TOO_LARGE", "사진은 한 장당 10 MiB 이하여야 합니다.", 413)
        data.extend(chunk)
    return validate_image(bytes(data), content_type, settings.max_image_pixels)
