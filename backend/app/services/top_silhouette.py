"""펼친 티셔츠 외곽의 상대 폭/소매 범위. 실제 치수나 목 구조를 확정하지 않는다."""

from io import BytesIO

import numpy as np
from PIL import Image, ImageFilter, ImageOps

from app.core.errors import AppError
from app.services.pants_silhouette import _largest

TOPS = {"티셔츠"}


def analyze_top(data):
    with Image.open(BytesIO(data)) as source:
        image = ImageOps.exif_transpose(source).convert("RGBA")
    image.thumbnail((768, 1024))
    rgba = np.asarray(image)
    if np.mean(rgba[:, :, 3] < 32) > 0.01:
        mask, method = rgba[:, :, 3] > 128, "alpha_mask"
    else:
        rgb = rgba[:, :, :3].astype(float)
        border = np.concatenate(
            [
                rgb[:4].reshape(-1, 3),
                rgb[-4:].reshape(-1, 3),
                rgb[:, :4].reshape(-1, 3),
                rgb[:, -4:].reshape(-1, 3),
            ]
        )
        background = np.median(border, axis=0)
        if np.percentile(np.linalg.norm(border - background, axis=1), 85) > 35:
            raise AppError(
                "SILHOUETTE_UNCERTAIN", "펼친 티셔츠의 누끼나 단색 배경을 사용해 주세요.", 422
            )
        raw = Image.fromarray(
            (np.linalg.norm(rgb - background, axis=2) > 30).astype(np.uint8) * 255
        )
        mask = (
            np.asarray(raw.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))) > 128
        )
        method = "flat_background_contrast"
    mask = _largest(mask)
    ys, xs = np.nonzero(mask)
    x0, x1, y0, y1 = int(xs.min()), int(xs.max() + 1), int(ys.min()), int(ys.max() + 1)
    cropped = mask[y0:y1, x0:x1]
    h, w = cropped.shape
    if h < 80 or not 0.45 < w / h < 2.8 or cropped.mean() < 0.20:
        raise AppError("SILHOUETTE_UNCERTAIN", "티셔츠 전체를 정면에서 펼쳐 촬영해 주세요.", 422)
    widths = []
    for row in cropped[int(h * 0.48) : int(h * 0.90)]:
        occupied = np.flatnonzero(row)
        if len(occupied):
            widths.append(int(occupied[-1] - occupied[0] + 1))
    body = float(np.median(widths))
    if not 0.35 < body / h < 1.3 or w < body * 1.1:
        raise AppError(
            "SILHOUETTE_UNCERTAIN",
            "몸판과 소매를 구분하기 어렵습니다. 누끼를 다시 확인해 주세요.",
            422,
        )
    return {
        "kind": "top",
        "method": method,
        "source": "photo_silhouette_estimate",
        "body_width_ratio": body / h,
        "sleeve_extent_ratio": (w - body * 0.9) / (2 * h),
        "aspect_ratio": w / h,
        "bbox": [x0, y0, x1, y1],
        "image_size": list(image.size),
        "landmarks": {
            "hem_left": [float((w - body) / 2 / w), 1.0],
            "hem_right": [float((w + body) / 2 / w), 1.0],
            "sleeve_left": [0.0, None],
            "sleeve_right": [1.0, None],
        },
        "physical_measurement": False,
        "neck_structure": "unknown",
        "back_geometry": "estimated",
    }


def valid_top(shape):
    return (
        isinstance(shape, dict)
        and shape.get("kind") == "top"
        and isinstance(shape.get("body_width_ratio"), (float, int))
        and 0.35 < shape["body_width_ratio"] < 1.3
        and isinstance(shape.get("sleeve_extent_ratio"), (float, int))
        and 0.02 < shape["sleeve_extent_ratio"] < 1
    )
