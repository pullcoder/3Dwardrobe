"""검증된 의류 사진의 앞뒤 투영. 보이지 않는 면을 원본처럼 만들어 내지 않는다."""

from io import BytesIO

import numpy as np
from PIL import Image, ImageOps

from app.core.errors import AppError


def panel(content, size=None, bbox=None):
    with Image.open(BytesIO(content)) as source:
        image = ImageOps.exif_transpose(source).convert("RGBA")
    # 분석용 저해상도에 사진 자체를 맞추지 않고 bbox만 재투영한다.
    # 후면 20MP 원본도 배열화 전에 제한해 CPU 메모리 사용을 줄인다.
    image.thumbnail((1536, 2048), Image.Resampling.LANCZOS)
    if bbox and size:
        bbox = [
            round(value * image.size[index % 2] / size[index % 2])
            for index, value in enumerate(bbox)
        ]
    rgba = np.asarray(image).copy()
    if rgba[:, :, 3].min() == 255:
        rgb = rgba[:, :, :3].astype(float)
        border = np.concatenate(
            [
                rgb[:3].reshape(-1, 3),
                rgb[-3:].reshape(-1, 3),
                rgb[:, :3].reshape(-1, 3),
                rgb[:, -3:].reshape(-1, 3),
            ]
        )
        background = np.median(border, axis=0)
        if np.percentile(np.linalg.norm(border - background, axis=1), 85) > 35:
            raise AppError(
                "CUTOUT_REQUIRED", "사진 질감을 위해 3단계 누끼 이미지를 저장해 주세요.", 422
            )
        rgba[:, :, 3] = (np.linalg.norm(rgb - background, axis=2) > 30) * 255
        image = Image.fromarray(rgba)
    alpha_box = image.getchannel("A").point(lambda a: 255 if a > 128 else 0).getbbox()
    if not alpha_box:
        raise AppError(
            "CUTOUT_REQUIRED", "의류 영역이 없는 이미지입니다. 누끼를 확인해 주세요.", 422
        )
    image = image.crop(tuple(bbox) if bbox else alpha_box)
    image.thumbnail((768, 1280), Image.Resampling.LANCZOS)
    rgba = np.asarray(image)
    known = rgba[:, :, 3] > 128
    if not known.any():
        raise AppError("CUTOUT_REQUIRED", "의류 영역을 찾지 못했습니다.", 422)
    # 흰 배경을 섞지 않고 가장자리 원단 픽셀을 확장해 UV 오차/밉맵 흰 테두리를 줄인다.
    pixels = rgba[:, :, :3].astype(float)
    median = np.median(pixels[known], axis=0)
    pixels[~known] = median
    for _ in range(12):
        neighbors, weights = np.zeros_like(pixels), np.zeros(known.shape, dtype=float)
        padded_pixels = np.pad(pixels, ((1, 1), (1, 1), (0, 0)), mode="edge")
        padded_known = np.pad(known, 1)
        h, w = known.shape
        for dy, dx in ((0, 1), (2, 1), (1, 0), (1, 2)):
            valid = padded_known[dy : dy + h, dx : dx + w]
            neighbors += padded_pixels[dy : dy + h, dx : dx + w] * valid[:, :, None]
            weights += valid
        grow = ~known & (weights > 0)
        if not grow.any():
            break
        pixels[grow] = neighbors[grow] / weights[grow, None]
        known |= grow
    return Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8)).resize(
        (768, 1280), Image.Resampling.LANCZOS
    )


def photo_atlas(spec, fallback):
    if not spec.get("_verified_projection") or not spec.get("_front_png"):
        raise AppError("RIGHTS_REQUIRED", "검증된 사진과 세부 표현 권한이 필요합니다.", 403)
    front = panel(spec["_front_png"], spec.get("_front_size"), spec.get("_front_bbox"))
    if spec.get("_back_png"):
        back = panel(spec["_back_png"])
    else:
        back = fallback.resize(front.size, Image.Resampling.LANCZOS)
    atlas = Image.new("RGB", (1536, 1280))
    atlas.paste(front, (0, 0))
    atlas.paste(back, (768, 0))
    output = BytesIO()
    # 기존 스튜디오의 2MiB GLB 한도를 위해 사진 아틀라스에 1MiB 예산을 둔다.
    for width in (1536, 1152, 768, 576, 384):
        output = BytesIO()
        atlas.resize((width, width * 5 // 6), Image.Resampling.LANCZOS).save(
            output, format="PNG", optimize=True
        )
        if output.tell() <= 1024 * 1024:
            break
    return output.getvalue(), "verified_front_projection"
