"""높이별 사진 외곽과 밑위 분기를 따르는 직접 제작 바지 표면. 천 시뮬레이션은 아니다."""

import math

import numpy as np

from app.core.errors import AppError
from app.services.pants_silhouette import valid_shape


def configure_pants(spec, info, shape=None):
    h = spec["dimensions"]["length"]["value"]
    wide = spec["fit"] in {"wide", "와이드", "와이드핏", "loose", "루즈핏", "오버핏", "oversized"}
    observed = valid_shape(shape)
    source = "photo_silhouette_estimate" if observed else "estimated"
    if observed:
        outline = [
            [t, outer * h * shape["aspect_ratio"], inner * h * shape["aspect_ratio"]]
            for t, outer, inner in shape["rows"]
        ]
        rise = shape["rise_ratio"]
    else:
        rise = 0.29 if h > 0.7 else 0.42
        waist, hip = spec["dimensions"]["width"]["value"], 0.51
        thigh, hem = (0.29, 0.28) if wide else (0.235, 0.17)
        anchors = [
            [0, waist / 2, 0],
            [0.12, hip / 2, 0],
            [rise, hip / 2, 0],
            [rise + 0.08, thigh + 0.012, 0.012],
            [0.65, hem + 0.023, 0.023],
            [1, hem + 0.028, 0.028],
        ]
        outline = [
            [
                float(t),
                float(np.interp(t, [a[0] for a in anchors], [a[1] for a in anchors])),
                float(np.interp(t, [a[0] for a in anchors], [a[2] for a in anchors])),
            ]
            for t in np.linspace(0, 1, 49)
        ]

    def sample(t, column):
        return float(np.interp(t, [row[0] for row in outline], [row[column] for row in outline]))

    values = {
        "waist_width": 2 * sample(0.03, 1),
        "hip_width": 2 * sample(min(0.20, rise * 0.75), 1),
        "rise": rise * h,
        "thigh_width": sample(min(0.9, rise + 0.10), 1) - sample(min(0.9, rise + 0.10), 2),
        "hem_width": sample(0.97, 1) - sample(0.97, 2),
    }
    sources = dict.fromkeys(values, source)
    aliases = {
        "허리단면": "waist_width",
        "허리너비": "waist_width",
        "엉덩이단면": "hip_width",
        "골반너비": "hip_width",
        "밑위": "rise",
        "앞밑위": "rise",
        "허벅지단면": "thigh_width",
        "밑단": "hem_width",
        "밑단너비": "hem_width",
        "밑단단면": "hem_width",
    }
    selected = (info.get("size") or "").strip().casefold()
    for measurement in sorted(
        info.get("measurements", []), key=lambda row: row.get("source") != "user_entered"
    ):
        key = aliases.get(measurement.get("label", "").replace(" ", ""))
        if (
            not key
            or sources[key] in {"user_entered", "ocr"}
            or measurement.get("target") != "garment"
        ):
            continue
        if measurement.get("size") and measurement["size"].strip().casefold() != selected:
            continue
        if measurement.get("kind") != ("length" if key == "rise" else "flat"):
            continue
        factor = {"cm": 0.01, "mm": 0.001, "inch": 0.0254}.get(measurement.get("unit"))
        value = measurement.get("value")
        if not factor or value is None:
            continue
        value *= factor
        low, high = {
            "waist_width": (0.2, 0.8),
            "hip_width": (0.25, 1.1),
            "rise": (0.12, min(0.65, h * 0.6)),
            "thigh_width": (0.1, 0.6),
            "hem_width": (0.08, 0.6),
        }[key]
        if not math.isfinite(value) or not low <= value <= high:
            raise AppError(
                "INVALID_DIMENSIONS", "바지 치수의 단위·단면·선택 사이즈를 확인해 주세요.", 422
            )
        values[key], sources[key] = value, measurement.get("source", "user_entered")
    old_waist, old_hip = 2 * sample(0.03, 1), 2 * sample(min(0.20, rise * 0.75), 1)
    old_thigh = sample(min(0.9, rise + 0.1), 1) - sample(min(0.9, rise + 0.1), 2)
    old_hem = sample(0.97, 1) - sample(0.97, 2)
    # 명시적 실측만 사진 추정 비율에 우선한다. 중간 높이의 외곽 변화는 그대로 보존한다.
    new_rise = values["rise"] / h
    adjusted = []
    for t, outer, inner in outline:
        if t <= rise:
            scale = float(
                np.interp(
                    t,
                    [0, min(0.20, rise * 0.75), rise],
                    [
                        values["waist_width"] / old_waist,
                        values["hip_width"] / old_hip,
                        values["hip_width"] / old_hip,
                    ],
                )
            )
            adjusted.append([t / rise * new_rise, outer * scale, 0.0])
        else:
            scale = float(
                np.interp(
                    t,
                    [rise, min(0.95, rise + 0.10), 1],
                    [
                        values["hip_width"] / old_hip,
                        values["thigh_width"] / old_thigh,
                        values["hem_width"] / old_hem,
                    ],
                )
            )
            adjusted.append(
                [new_rise + (t - rise) / (1 - rise) * (1 - new_rise), outer * scale, inner * scale]
            )
    spec["pants"] = {
        "outline": adjusted,
        "rise_ratio": new_rise,
        "observed": observed,
        "method": shape["method"] if observed else "generic_pants_profile",
        "warnings": shape.get("warnings", [])
        if observed
        else ["사진 외곽이 없습니다. 사진을 다시 분석하면 형태에 반영할 수 있습니다."],
        "fit_inference": "wide"
        if values["hem_width"] >= values["thigh_width"] * 0.8
        else "tapered",
        "back_geometry": "estimated",
    }
    for key, value in values.items():
        spec["dimensions"][key] = {"value": value, "source": sources[key]}
    spec["dimensions"]["width"] = {"value": values["waist_width"], "source": sources["waist_width"]}
    spec["dimensions"]["depth"] = {
        "value": min(0.27, max(0.13, values["hip_width"] * 0.40)),
        "source": "estimated",
    }


def _mesh(name, positions, indices, uvs):
    points = np.asarray(positions, dtype=float).reshape(-1, 3)
    faces = np.asarray(indices, dtype=int).reshape(-1, 3)
    normals = np.zeros_like(points)
    vectors = np.cross(
        points[faces[:, 1]] - points[faces[:, 0]], points[faces[:, 2]] - points[faces[:, 0]]
    )
    for i in range(3):
        np.add.at(normals, faces[:, i], vectors)
    lengths = np.linalg.norm(normals, axis=1)
    if np.any(lengths < 1e-12):
        raise AppError("INVALID_MESH", "바지 표면 연결을 생성하지 못했습니다.", 422)
    normals /= lengths[:, None]
    return {
        "name": name,
        "positions": positions,
        "indices": indices,
        "normals": normals.ravel().tolist(),
        "uvs": uvs,
    }


def make_pants(spec):
    h = spec["dimensions"]["length"]["value"]
    half_depth = spec["dimensions"]["depth"]["value"] / 2
    outline = spec["pants"]["outline"]
    rise = spec["pants"]["rise_ratio"]
    full_width = max(row[1] for row in outline) * 2
    meshes = []

    def bounds(t):
        ts = [row[0] for row in outline]
        outer = float(np.interp(t, ts, [row[1] for row in outline]))
        inner = 0 if t <= rise else float(np.interp(t, ts, [row[2] for row in outline]))
        if t > rise:
            # 배경 분리 오차로 내측 경계가 0인 행도 두 바지통이 중복 봉제되지 않게 분리한다.
            inner = max(inner, min(0.0015, (t - rise) * 0.08))
        return outer, inner

    def panels(name, ts, signs):
        positions, indices, uvs = [], [], []
        for sign in signs:
            for face in (1, -1):
                start = len(positions) // 3
                for t in ts:
                    outer, inner = bounds(t)
                    for j in range(49):
                        u = j / 48
                        x = sign * (inner + (outer - inner) * u)
                        leg_curve = math.sqrt(max(0, 1 - (2 * u - 1) ** 4))
                        pelvis_curve = math.sqrt(max(0, 1 - (x / max(outer, 1e-5)) ** 4))
                        blend = max(0, min(1, (t - rise * 0.82) / (rise * 0.18)))
                        blend = blend * blend * (3 - 2 * blend)
                        curve = (1 - blend) * pelvis_curve + blend * leg_curve
                        # 깊이는 단일 사진에서 관찰할 수 없어 별도 추정값으로 둔다.
                        depth = (
                            half_depth * (0.68 + 0.32 * math.sin(math.pi / 2 * min(1, t / rise)))
                            if t < rise
                            else min(half_depth, (outer - inner) * 0.46)
                        )
                        # 원본 픽셀을 복제하지 않는 일반적인 세로 드레이프와 밴드 주름.
                        gather = 0.003 * math.sin(u * math.pi * 24) * math.exp(-t / 0.035)
                        phase = u * math.pi * 6 + 0.65 * math.sin(t * 5) + face * 0.3
                        drape = 0.007 * math.cos(phase) + 0.0025 * math.sin(phase * 1.8)
                        drape *= math.sin(math.pi * u) ** 2 * min(1, t / 0.09)
                        drape *= 0.65 + 0.35 * math.sin(math.pi * t / 2)
                        # 윗/아랫 패널 경계는 같은 함수로 계산해 틈을 만들지 않는다.
                        seam = 0.0016 * math.exp(-(((t - 0.035) / 0.004) ** 2))
                        seam += 0.0012 * math.exp(-(((t - 0.987) / 0.005) ** 2))
                        z = face * (max(0.0002, depth + gather + drape + seam) * curve)
                        positions.extend([x, h * (1 - t), z])
                        image_u = 0.5 + x / full_width
                        uvs.extend(
                            [image_u * 0.5 + (0 if face == 1 else 0.5), 1 - t]
                            if spec.get("mode") == "B"
                            else [image_u, 1 - t]
                        )
                    if spec.get("mode", "A") == "A":
                        # A의 자체 원단은 단순 정면 투영 대신 표면 호 길이에 배치한다.
                        # 옆면에서 체크가 크게 늘어나는 현상을 줄인다. B 투영 UV는 보존한다.
                        row_start = len(positions) // 3 - 49
                        arc = 0.0
                        for j in range(49):
                            if j:
                                a, b = (row_start + j - 1) * 3, (row_start + j) * 3
                                arc += math.hypot(
                                    positions[b] - positions[a], positions[b + 2] - positions[a + 2]
                                )
                            u = j / 48
                            edge = max(0, min(1, (u - 0.70) / 0.30))
                            edge = edge * edge * (3 - 2 * edge)
                            flat = (outer - inner) * u
                            # 앞면의 직선 체크는 유지하고 둥근 측면에서만 호 길이를 보간한다.
                            uvs[(row_start + j) * 2] = 0.5 + sign * (
                                inner + flat + (arc - flat) * edge
                            ) / (full_width + 4 * half_depth)
                for row in range(len(ts) - 1):
                    for j in range(48):
                        a = start + row * 49 + j
                        b = a + 49
                        tri = [a, b, a + 1, a + 1, b, b + 1]
                        if sign * face < 0:
                            tri = [tri[i] for i in (0, 2, 1, 3, 5, 4)]
                        indices.extend(tri)
                # 허리와 밑단의 열린 가장자리에 접어 넣은 얇은 안쪽 단을 만든다.
                boundary = 0 if name == "waist" else len(ts) - 1
                edge = start + boundary * 49
                lip = len(positions) // 3
                outer, inner = bounds(ts[boundary])
                center = 0 if name == "waist" else sign * (outer + inner) / 2
                target_t = ts[boundary] + (0.008 / h if name == "waist" else -0.008 / h)
                upper_row = min(len(ts) - 1, max(1, int(np.searchsorted(ts, target_t))))
                lower_row = upper_row - 1
                blend = (target_t - ts[lower_row]) / (ts[upper_row] - ts[lower_row])
                for j in range(49):
                    a, b = (start + lower_row * 49 + j) * 3, (start + upper_row * 49 + j) * 3
                    x, y, z = [
                        positions[a + k] * (1 - blend) + positions[b + k] * blend for k in range(3)
                    ]
                    positions.extend(
                        [
                            center + (x - center) * 0.99,
                            y,
                            z * 0.98,
                        ]
                    )
                    uvs.extend(uvs[(edge + j) * 2 : (edge + j) * 2 + 2])
                for j in range(48):
                    a, b = edge + j, lip + j
                    tri = [a, b, a + 1, a + 1, b, b + 1]
                    if sign * face * (1 if name == "waist" else -1) > 0:
                        tri = [tri[i] for i in (0, 2, 1, 3, 5, 4)]
                    indices.extend(tri)
        return _mesh(name, positions, indices, uvs)

    upper = sorted(
        set(
            [float(t) for t in np.linspace(0, rise, 33)]
            + [min(rise, 0.025), min(rise, 0.035), min(rise, 0.045)]
        )
    )
    meshes.append(panels("waist", upper, (-1, 1)))
    legs = [float(t) for t in np.linspace(rise, 1, 65)]
    meshes.append(panels("leg_left", legs, (-1,)))
    meshes.append(panels("leg_right", legs, (1,)))
    # 좌우·앞뒤·부위 경계의 같은 좌표를 공유하는 외측 법선을 평균한다.
    # 실제 봉제/물리용 정점 용접은 아니며 UV와 의미 부위 계약은 보존한다.
    groups = {}
    for mesh in meshes:
        for i in range(0, len(mesh["positions"]), 3):
            key = tuple(round(v, 6) for v in mesh["positions"][i : i + 3])
            groups.setdefault(key, []).append((mesh, i))
    for members in groups.values():
        if len(members) < 2:
            continue
        normal = np.sum([m["normals"][i : i + 3] for m, i in members], axis=0)
        length = np.linalg.norm(normal)
        if length > 1e-6:
            for mesh, i in members:
                mesh["normals"][i : i + 3] = (normal / length).tolist()
    return meshes
