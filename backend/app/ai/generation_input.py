"""3단계 누끼를 재사용한다. A는 알파 실루엣만 사용하고 원본 세부 픽셀은 버린다."""

from io import BytesIO

from PIL import Image, ImageOps

from app.core.errors import AppError
from app.services.uploads import validate_image


def prepare_input(content, mime, mode, segment=None):
    validate_image(content, mime, 20_000_000)
    image = ImageOps.exif_transpose(Image.open(BytesIO(content))).convert("RGBA")
    if image.getchannel("A").getextrema()[0] == 255:
        if segment is None:
            raise AppError(
                "CUTOUT_REQUIRED", "3단계에서 배경을 제거한 의류 이미지가 필요합니다.", 422
            )
        image = segment(image).convert("RGBA")
    alpha = image.getchannel("A")
    mask = alpha.point(lambda value: 255 if value > 32 else 0)
    box = mask.getbbox()
    if not box or min(box[2] - box[0], box[3] - box[1]) < 16:
        raise AppError("INVALID_SILHOUETTE", "의류 실루엣이 비어 있거나 너무 작습니다.", 422)
    foreground = sum(mask.histogram()[1:]) / (image.width * image.height)
    if not 0.01 < foreground < 0.98:
        raise AppError("INVALID_SILHOUETTE", "배경 제거 결과를 확인해 주세요.", 422)
    if mode == "A":
        plain = Image.new("RGBA", image.size, (150, 150, 150, 0))
        plain.putalpha(alpha)
        image = plain
    elif mode != "B":
        raise AppError("RIGHTS_REQUIRED", "유효한 권리 모드가 필요합니다.", 403)
    cropped = image.crop(box)
    cropped.thumbnail((768, 768), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (896, 896))
    canvas.paste(cropped, ((896 - cropped.width) // 2, (896 - cropped.height) // 2))
    return canvas, {
        "source_size": list(image.size),
        "crop": list(box),
        "input_size": [896, 896],
        "aspect_ratio_preserved": True,
        "texture_policy": "silhouette_only" if mode == "A" else "verified_source_details",
    }
