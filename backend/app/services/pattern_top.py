"""앞뒤 몸판·소매가 한 외곽 패널로 이어지는 직접 제작 티셔츠 패턴 템플릿."""

import math

import numpy as np

from app.core.errors import AppError
from app.services.garment_templates import top_template
from app.services.pants_mesh import _mesh


def configure_top(spec, shape=None):
    key, template = top_template(spec)
    dims = spec["dimensions"]
    h = dims["length"]["value"]
    observed = isinstance(shape, dict) and shape.get("kind") == "top"
    if observed and dims["width"]["source"] == "estimated":
        dims["width"] = {
            "value": min(0.90, max(0.3, h * shape["body_width_ratio"])),
            "source": "photo_silhouette_estimate",
        }
    elif dims["width"]["source"] == "estimated":
        dims["width"]["value"] *= template["ease"]
    if observed and dims["sleeve"]["source"] == "estimated":
        dims["sleeve"] = {
            "value": min(0.45, max(0.10, h * shape["sleeve_extent_ratio"])),
            "source": "photo_silhouette_estimate",
        }
    spec["top_panel"] = {
        "template": key,
        "source": "project_original_panel_pattern",
        "observed": observed,
        "shoulder_y": h * 0.96,
        "shoulder_half_width": dims["width"]["value"] * 0.44,
        "landmarks": shape.get("landmarks", {}) if observed else {},
        "warnings": []
        if observed
        else ["상의 외곽을 확인하지 못해 일반 티셔츠 패턴을 사용합니다."],
    }


def _triangulate(points):
    """오목한 목 파임을 보존하는 ear clipping. 경계 밖 삼각형을 만들지 않는다."""
    xy = np.asarray(points)[:, :2]
    # 신발끈 면적으로 순서를 결정한다.
    signed = sum(
        xy[i, 0] * xy[(i + 1) % len(xy), 1] - xy[(i + 1) % len(xy), 0] * xy[i, 1]
        for i in range(len(xy))
    )
    remaining = list(range(len(xy)))
    if signed < 0:
        remaining.reverse()
    faces = []

    def cross(a, b, c):
        return float((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))

    while len(remaining) > 3:
        for j, b in enumerate(remaining):
            a, c = remaining[j - 1], remaining[(j + 1) % len(remaining)]
            if cross(xy[a], xy[b], xy[c]) <= 1e-12:
                continue
            if any(
                all(
                    v >= -1e-12
                    for v in (
                        cross(xy[a], xy[b], xy[p]),
                        cross(xy[b], xy[c], xy[p]),
                        cross(xy[c], xy[a], xy[p]),
                    )
                )
                for p in remaining
                if p not in {a, b, c}
            ):
                continue
            faces.append([a, b, c])
            remaining.pop(j)
            break
        else:
            raise AppError("INVALID_PATTERN", "티셔츠 패널 경계를 연결하지 못했습니다.", 422)
    faces.append(remaining)
    return faces


def make_top(spec):
    dims = spec["dimensions"]
    h, w, depth, sleeve = [dims[k]["value"] for k in ("length", "width", "depth", "sleeve")]
    half, neck = w / 2, min(0.105, w * 0.19)
    shoulder = half * 0.9
    extent = shoulder + sleeve * 0.92
    # x / 앞면 높이 / 뒷면 높이. 목 구멍만 전후의 파임 깊이가 다르다.
    left = [
        [-half * 1.02, 0, 0],
        [-half, h * 0.40, h * 0.40],
        [-half * 0.97, h * 0.63, h * 0.63],
        [-extent + 0.02, h * 0.58, h * 0.58],
        [-extent, h * 0.81, h * 0.81],
        [-shoulder, h * 0.94, h * 0.94],
        [-neck, h, h],
    ]
    mouth = []
    for i in range(1, 8):
        theta = math.pi * i / 8
        x = -neck * math.cos(theta)
        drop = (
            0.10 * (1 - abs(x) / neck) if spec["neckline"] == "브이넥" else 0.065 * math.sin(theta)
        )
        mouth.append([x, h - drop, h - 0.018 * math.sin(theta)])
    points = left + mouth + [[-x, y, z] for x, y, z in reversed(left)]
    faces = _triangulate(points)
    edges = {}
    for i in range(len(points)):
        j = (i + 1) % len(points)
        a, b = points[i], points[j]
        opening = (
            (a[1] == 0 and b[1] == 0)
            or (abs(a[0]) > shoulder + 0.03 and abs(b[0]) > shoulder + 0.03)
            or (abs(a[0]) <= neck + 1e-9 and abs(b[0]) <= neck + 1e-9)
        )
        edges[tuple(sorted((i, j)))] = opening
    # 같은 경계 중점을 공유하여 T-junction 없이 패널을 세분한다.
    for _ in range(4):
        mids = {}

        def midpoint(a, b, mids=mids):
            key = tuple(sorted((a, b)))
            if key not in mids:
                mids[key] = len(points)
                points.append([(points[a][k] + points[b][k]) / 2 for k in range(3)])
            return mids[key]

        refined = []
        for a, b, c in faces:
            ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
            refined.extend([[a, ab, ca], [ab, b, bc], [ca, bc, c], [ab, bc, ca]])
        boundary = {}
        for (a, b), opening in edges.items():
            m = midpoint(a, b)
            boundary[tuple(sorted((a, m)))] = opening
            boundary[tuple(sorted((m, b)))] = opening
        faces, edges = refined, boundary
    positions, uvs, indices = [], [], []
    count = len(points)
    for face in (1, -1):
        for x, front_y, back_y in points:
            y = front_y if face == 1 else back_y
            sleeve_weight = min(1, max(0, (abs(x) - shoulder * 0.85) / (half * 0.3)))
            sleeve_weight *= max(0, min(1, (y / h - 0.52) / 0.18))
            sleeve_weight = sleeve_weight * sleeve_weight * (3 - 2 * sleeve_weight)
            torso_curve = math.sqrt(max(0.03, 1 - (x / (half * 1.1)) ** 4))
            sleeve_center = h * (0.78 - 0.10 * min(1, max(0, (abs(x) - shoulder) / sleeve)))
            sleeve_curve = math.sqrt(max(0.035, 1 - ((y - sleeve_center) / (h * 0.16)) ** 2))
            thickness = depth * (
                0.46 * torso_curve * (1 - sleeve_weight) + 0.31 * sleeve_curve * sleeve_weight
            )
            drape = (
                0.0035 * math.sin(x * 38 + face * 0.6) * math.sin(math.pi * max(0, min(1, y / h)))
            )
            # 4cm 폭의 목 주변 밴드는 같은 표면 안의 완만한 리브로 표현한다.
            neck_y = h - (0.065 if face == 1 else 0.018) * math.sqrt(max(0, 1 - (x / neck) ** 2))
            rib = 0.0018 * math.exp(-(((y - neck_y + 0.008) / 0.006) ** 2)) if abs(x) < neck else 0
            positions.extend([x, y, face * (thickness + drape + rib)])
            if spec.get("mode") == "B":
                image_u = max(0, min(1, 0.5 + face * x / (extent * 2)))
                uvs.extend(
                    [image_u * 0.496 + (0.002 if face == 1 else 0.502), max(0, min(1, 1 - y / h))]
                )
            else:
                uvs.extend([0.5 + x / (extent * 2.1), max(0, min(1, y / h))])
    for a, b, c in faces:
        indices.extend([a, b, c, count + a, count + c, count + b])
    # 어깨/몸판 옆선/소매 윗선·아랫선을 동일 정점에 연결한다. 개구부는 열린 채 둔다.
    for (a, b), opening in edges.items():
        if opening:
            continue
        # 앞면 삼각형 경계 방향과 반대로 이어 일관된 외향 winding을 만든다.
        directed = any((a, b) in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])) for f in faces)
        if directed:
            a, b = b, a
        indices.extend([a, b, count + a, b, count + b, count + a])
    return [_mesh("body", positions, indices, uvs)]
