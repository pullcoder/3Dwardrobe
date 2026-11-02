import warnings
from io import BytesIO

from PIL import Image, UnidentifiedImageError

from app.core.errors import AppError
from app.schemas.uploads import UploadValidationRead

IMAGE_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


def validate_image(data: bytes, content_type: str, max_pixels: int) -> UploadValidationRead:
    """파일 시그니처·디코딩·해상도를 검증하고 이미지를 저장하지 않는다."""
    if content_type not in IMAGE_FORMATS.values():
        raise AppError("UNSUPPORTED_IMAGE", "JPEG, PNG, WebP 사진만 사용할 수 있습니다.", 415)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                width, height = image.size
                if width * height > max_pixels:
                    raise AppError(
                        "IMAGE_TOO_LARGE", "사진 해상도는 2천만 화소 이하여야 합니다.", 413
                    )
                detected_type = IMAGE_FORMATS.get(image.format)
                if detected_type != content_type:
                    raise AppError(
                        "IMAGE_TYPE_MISMATCH", "파일 내용과 이미지 형식이 다릅니다.", 415
                    )
                if getattr(image, "is_animated", False):
                    raise AppError(
                        "ANIMATED_IMAGE", "움직이는 이미지 대신 정지 사진을 선택해 주세요."
                    )
                image.verify()
            with Image.open(BytesIO(data)) as image:
                image.load()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise AppError("IMAGE_TOO_LARGE", "사진 해상도가 너무 큽니다.", 413) from exc
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise AppError(
            "INVALID_IMAGE", "사진을 읽을 수 없습니다. 다른 사진을 선택해 주세요."
        ) from exc
    return UploadValidationRead(
        content_type=detected_type, size_bytes=len(data), width=width, height=height
    )
