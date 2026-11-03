"""사진의 외곽만 수치화한다. 패턴 픽셀·로고·학습 모델을 복사하지 않는다."""

from io import BytesIO

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from app.core.errors import AppError

PANTS = {"청바지", "슬랙스", "반바지"}


def _runs(row):
    changes = np.diff(np.pad(row.astype(np.int8), (1, 1)))
    return list(
        zip(
            np.flatnonzero(changes == 1).tolist(),
            np.flatnonzero(changes == -1).tolist(),
            strict=True,
        )
    )


def _largest(mask):
    """행 구간 연결 성분으로 작은 배경 잡음을 제외한다."""
    parents, spans = [], []
    previous = []

    def root(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for y, row in enumerate(mask):
        current = []
        for left, right in _runs(row):
            index = len(parents)
            parents.append(index)
            spans.append((y, left, right))
            for a, b, parent in previous:
                if a <= right and b >= left:
                    parents[root(index)] = root(parent)
            current.append((left, right, index))
        previous = current
    if not parents:
        raise AppError(
            "SILHOUETTE_UNCERTAIN", "의류 외곽을 찾지 못했습니다. 누끼 PNG를 사용해 주세요.", 422
        )
    areas = {}
    for index, (_, left, right) in enumerate(spans):
        key = root(index)
        areas[key] = areas.get(key, 0) + right - left
    chosen = max(areas, key=areas.get)
    if areas[chosen] < sum(areas.values()) * 0.80:
        raise AppError(
            "MULTIPLE_OBJECTS",
            "분리된 물체가 여러 개입니다. 바지 한 벌의 누끼를 사용해 주세요.",
            422,
        )
    result = np.zeros_like(mask)
    for index, (y, left, right) in enumerate(spans):
        if root(index) == chosen:
            result[y, left:right] = True
    return result


def analyze_pants(data):
    """알파 마스크 우선, 단색 배경 대조는 제한적 대안이다. 실제 cm 측정이 아니다."""
    with Image.open(BytesIO(data)) as source:
        image = ImageOps.exif_transpose(source).convert("RGBA")
    image.thumbnail((768, 1024))
    rgba = np.asarray(image)
    alpha = rgba[:, :, 3]
    warnings = []
    if np.mean(alpha < 32) > 0.01 and np.mean(alpha > 192) > 0.02:
        mask = alpha > 128
        method = "alpha_mask"
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
                "SILHOUETTE_UNCERTAIN",
                "배경이 복잡합니다. 3단계 누끼 PNG나 단색 배경 사진을 사용해 주세요.",
                422,
            )
        raw = Image.fromarray(
            (np.linalg.norm(rgb - background, axis=2) > 30).astype(np.uint8) * 255
        )
        mask = (
            np.asarray(raw.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))) > 128
        )
        method = "flat_background_contrast"
        warnings.append("단색 배경 대조로 분리한 외곽입니다. 3단계 누끼보다 부정확할 수 있습니다.")
    mask = _largest(mask)
    # 체크 내부의 밝은 칸은 구멍으로 보지 않는다. 바깥에서 연결되는 다리 사이는 유지한다.
    padded = ImageOps.expand(Image.fromarray(mask.astype(np.uint8) * 255), border=1, fill=0)
    ImageDraw.floodfill(padded, (0, 0), 128)
    filled = np.asarray(padded)[1:-1, 1:-1]
    mask = filled != 128
    ys, xs = np.nonzero(mask)
    x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)
    cropped = mask[y0:y1, x0:x1]
    height, width = cropped.shape
    if (
        height < 80
        or width < 40
        or not 0.20 < width / height < 1.8
        or not 0.15 < cropped.mean() < 0.96
    ):
        raise AppError(
            "SILHOUETTE_UNCERTAIN",
            "바지 전신 외곽을 확인하기 어렵습니다. 펼친 바지 한 벌을 정면에서 촬영해 주세요.",
            422,
        )
    center = width / 2
    split_rows = []
    for y in range(int(height * 0.14), int(height * 0.65)):
        runs = [(a, b) for a, b in _runs(cropped[y]) if b - a > width * 0.08]
        if (
            len(runs) == 2
            and runs[0][1] < center < runs[1][0]
            and runs[1][0] - runs[0][1] > max(2, width * 0.015)
        ):
            split_rows.append(y)
    rise = None
    split_set = set(split_rows)
    for y in split_rows:
        if sum((y + j) in split_set for j in range(8)) >= 7:
            rise = max(0.18, min(0.52, y / height))
            break
    if rise is None:
        raise AppError(
            "PANTS_SPLIT_UNCLEAR",
            "밑위와 두 바지통 경계를 찾지 못했습니다. "
            "다리 사이가 보이는 정면 사진이나 누끼를 사용해 주세요.",
            422,
        )
    rows = []
    for t in np.linspace(0, 1, 49):
        y = min(height - 1, max(0, round(t * (height - 1))))
        row = cropped[max(0, y - 2) : min(height, y + 3)].mean(axis=0) > 0.35
        positions = np.flatnonzero(row)
        if len(positions) < 4:
            continue
        outer = (positions[-1] - positions[0] + 1) / width / 2
        left, right = positions[positions < center], positions[positions >= center]
        inner = (
            0
            if t <= rise or not len(left) or not len(right)
            else max(0, (right[0] - left[-1] - 1) / width / 2)
        )
        if outer - inner < 0.04:
            raise AppError(
                "SILHOUETTE_UNCERTAIN",
                "바지통 외곽이 불안정합니다. 정면 누끼를 확인해 주세요.",
                422,
            )
        rows.append([round(float(t), 5), round(float(outer), 5), round(float(inner), 5)])
    if len(rows) < 40:
        raise AppError("SILHOUETTE_UNCERTAIN", "기장 전체의 외곽을 찾지 못했습니다.", 422)
    if min(x0, y0, image.width - x1, image.height - y1) <= 1:
        warnings.append("외곽이 이미지 끝에 닿습니다. 일부가 잘렸는지 확인해 주세요.")
    return {
        "method": "pants_silhouette_v1",
        "mask_method": method,
        "rows": rows,
        "aspect_ratio": round(width / height, 5),
        "rise_ratio": round(rise, 5),
        "bbox": [x0, y0, x1, y1],
        "image_size": [image.width, image.height],
        "source": "photo_silhouette_estimate",
        "warnings": warnings,
        "back_geometry": "estimated",
        "physical_measurement": False,
    }


def valid_shape(value):
    if not isinstance(value, dict) or value.get("method") != "pants_silhouette_v1":
        return False
    rows = value.get("rows")
    try:
        return (
            isinstance(rows, list)
            and 40 <= len(rows) <= 64
            and 0.2 < float(value["aspect_ratio"]) < 1.8
            and 0.18 <= float(value["rise_ratio"]) <= 0.52
            and all(
                len(row) == 3
                and all(np.isfinite(v) for v in row)
                and 0 <= row[0] <= 1
                and 0 <= row[2] < row[1] <= 0.65
                for row in rows
            )
            and all(rows[i][0] < rows[i + 1][0] for i in range(len(rows) - 1))
        )
    except (TypeError, ValueError, KeyError):
        return False
