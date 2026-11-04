"""직접 제작한 일반 의류 파라미터 메시와 자체 포함 glTF 2.0 GLB.

A는 사진 외곽 수치와 자체 패턴만 사용한다. B는 권한 검증된 티셔츠·바지의
앞뒤 사진을 제한적으로 투영한다. 봉제/천 시뮬레이션 모델이 아니다.
"""

import json
import math
import struct
from datetime import UTC, datetime

from app.core.errors import AppError
from app.services.mesh_quality import inspect_meshes
from app.services.pants_materials import generic_check, legacy_check
from app.services.pants_materials import materials as pants_materials
from app.services.pants_mesh import configure_pants, make_pants
from app.services.pants_silhouette import PANTS, valid_shape
from app.services.pattern_top import configure_top, make_top
from app.services.top_silhouette import TOPS, valid_top

VERSION = "stylefit-template-1.0"
PANTS_VERSION = "stylefit-pants-2.2"
TEMPLATES = {
    "티셔츠": ("top", 0.68),
    "셔츠": ("top", 0.73),
    "니트": ("top", 0.66),
    "재킷": ("outer", 0.72),
    "코트": ("outer", 1.05),
    "청바지": ("bottom", 1.02),
    "슬랙스": ("bottom", 1.02),
    "반바지": ("bottom", 0.48),
    "스커트": ("bottom", 0.60),
}
COLORS = {
    "검정": "#242428",
    "검정색": "#242428",
    "black": "#242428",
    "흰색": "#ecebe6",
    "white": "#ecebe6",
    "회색": "#88888b",
    "gray": "#88888b",
    "빨강": "#b93840",
    "red": "#b93840",
    "파랑": "#356baa",
    "blue": "#356baa",
    "남색": "#283b60",
    "navy": "#283b60",
    "초록": "#437257",
    "green": "#437257",
    "베이지": "#c5ae8c",
    "beige": "#c5ae8c",
    "갈색": "#805c44",
    "brown": "#805c44",
    "분홍": "#d5a1b0",
    "pink": "#d5a1b0",
    "노랑": "#d3b34a",
    "yellow": "#d3b34a",
    "보라": "#8872a4",
    "purple": "#8872a4",
    "주황": "#cd8441",
    "orange": "#cd8441",
}


def resolve_spec(info, analysis, has_back=False):
    """정해진 의미·단위의 의류 치수만 채택하며 나머지는 추정으로 남긴다."""
    front = analysis.get("front", {}) if isinstance(analysis.get("front"), dict) else {}
    back = analysis.get("back", {}) if isinstance(analysis.get("back"), dict) else {}

    def feature(key, fallback="unknown"):
        source_key = "primary_color" if key == "color" else key
        manual = info.get(key)
        if manual and manual not in {"unknown", "미확인"}:
            if front.get(source_key) == manual:
                return manual, "analysis_front"
            if back.get(source_key) == manual:
                return manual, "analysis_back"
            return manual, "user_entered"
        value = front.get(source_key)
        if isinstance(value, str) and value and value != "unknown":
            return value, "analysis_front"
        value = back.get(source_key)
        if isinstance(value, str) and value and value != "unknown":
            return value, "analysis_back"
        return fallback, "estimated"

    garment_type, type_source = feature("garment_type")
    if garment_type not in TEMPLATES:
        raise AppError(
            "UNSUPPORTED_GARMENT", "지원하지 않는 의류 종류입니다. 종류를 확인해 주세요.", 422
        )
    category, length = TEMPLATES[garment_type]
    if info["category"] != category:
        raise AppError("CATEGORY_MISMATCH", "의류 종류와 카테고리를 일치시켜 주세요.", 422)
    dims = {
        "length": {"value": length, "source": "estimated"},
        "width": {"value": 0.52 if category != "bottom" else 0.36, "source": "estimated"},
        "depth": {"value": 0.24 if category != "bottom" else 0.23, "source": "estimated"},
        "sleeve": {"value": 0.22 if garment_type == "티셔츠" else 0.57, "source": "estimated"},
    }
    aliases = {
        "총장": "length",
        "실측 총장": "length",
        "옷길이": "length",
        "기장": "length",
        "가슴단면": "width",
        "가슴너비": "width",
        "허리단면": "width",
        "소매길이": "sleeve",
    }
    measurements = sorted(
        info.get("measurements", []), key=lambda m: m.get("source") != "user_entered"
    )
    for m in measurements:
        key = aliases.get(m.get("label"))
        factor = {"cm": 0.01, "mm": 0.001, "inch": 0.0254}.get(m.get("unit"))
        if not key or not factor or m.get("target") != "garment" or m.get("value") is None:
            continue
        if (
            m.get("size")
            and m["size"].strip().casefold() != (info.get("size") or "").strip().casefold()
        ):
            continue
        if m.get("kind") != ("flat" if key == "width" else "length"):
            continue
        if dims[key]["source"] != "estimated":
            continue
        value = m["value"] * factor
        low, high = {"length": (0.25, 1.6), "width": (0.20, 0.95), "sleeve": (0.08, 0.90)}[key]
        if not math.isfinite(value) or not low <= value <= high:
            raise AppError("INVALID_DIMENSIONS", "생성 가능한 의류 치수 범위를 확인해 주세요.", 422)
        dims[key] = {"value": value, "source": m.get("source", "user_entered")}
    sleeve, sleeve_source = feature("sleeve")
    if dims["sleeve"]["source"] == "estimated":
        if sleeve in {"반소매", "반팔", "short sleeves"}:
            dims["sleeve"] = {"value": 0.22, "source": sleeve_source}
        elif sleeve in {"긴소매", "긴팔", "long sleeves"}:
            dims["sleeve"] = {"value": 0.57, "source": sleeve_source}
    color, color_source = feature("color")
    hex_color = COLORS.get(color.lower(), "#9a91ae")
    if len(color) == 7 and color.startswith("#"):
        try:
            int(color[1:], 16)
            hex_color = color
        except ValueError:
            pass
    if color.lower() not in COLORS and hex_color == "#9a91ae":
        color_source = "estimated"
    neckline, _ = feature("neckline", "라운드넥")
    fit, _ = feature("fit", "regular")
    pattern, _ = feature("pattern")
    spec = {
        "garment_type": garment_type,
        "category": category,
        "type_source": type_source,
        "dimensions": dims,
        "color": hex_color,
        "color_source": color_source,
        "neckline": neckline
        if neckline in {"브이넥", "라운드넥", "카라", "터틀넥"}
        else "라운드넥",
        "sleeveless": sleeve in {"민소매", "sleeveless"},
        "fit": fit
        if fit
        in {
            "slim",
            "regular",
            "loose",
            "슬림핏",
            "루즈핏",
            "wide",
            "와이드",
            "와이드핏",
            "오버핏",
            "oversized",
        }
        else "regular",
        "pattern": "check"
        if pattern in {"체크", "체크무늬", "plaid", "check", "checked"}
        else "solid",
        "back_observed": bool(has_back or back),
        "analysis_views": [
            view for view in ("front", "back") if isinstance(analysis.get(view), dict)
        ],
    }
    if garment_type in PANTS:
        configure_pants(
            spec,
            info,
            analysis.get("silhouette") if valid_shape(analysis.get("silhouette")) else None,
        )
    if garment_type in TOPS and not spec["sleeveless"]:
        configure_top(
            spec, analysis.get("silhouette") if valid_top(analysis.get("silhouette")) else None
        )
    fabric = (info.get("material") or "").lower()
    spec["material_profile"] = {
        "roughness": 0.96
        if any(x in fabric for x in ("면", "cotton", "울", "wool", "denim"))
        else 0.88,
        "source": "visual_preset_from_declared_material"
        if fabric not in {"", "미확인", "unknown"}
        else "generic_estimate",
    }
    return spec


def make_meshes(spec):
    """개구부가 있는 몸판·소매·바지통을 독립적인 삼각형 표면으로 제작한다."""
    if spec.get("top_panel"):
        return make_top(spec)
    if spec.get("pants"):
        return make_pants(spec)
    meshes = []
    n = 48

    def surface(name, rings, opening=False):
        positions, indices = [], []
        for ring in rings:
            for i in range(n + 1):
                theta = (
                    (math.pi / 2 + 0.14 + (2 * math.pi - 0.28) * i / n)
                    if opening
                    else 2 * math.pi * i / n
                )
                positions.extend(ring(theta))
        for j in range(len(rings) - 1):
            for i in range(n):
                a, b = j * (n + 1) + i, (j + 1) * (n + 1) + i
                indices.extend([a, b, a + 1, a + 1, b, b + 1])
        normals = [0.0] * len(positions)
        for i in range(0, len(indices), 3):
            ids = indices[i : i + 3]
            a, b, c = [positions[k * 3 : k * 3 + 3] for k in ids]
            u, v = [b[k] - a[k] for k in range(3)], [c[k] - a[k] for k in range(3)]
            normal = [
                u[1] * v[2] - u[2] * v[1],
                u[2] * v[0] - u[0] * v[2],
                u[0] * v[1] - u[1] * v[0],
            ]
            for index in ids:
                for k in range(3):
                    normals[index * 3 + k] += normal[k]
        for i in range(0, len(normals), 3):
            size = math.sqrt(sum(v * v for v in normals[i : i + 3]))
            if size < 1e-10:
                raise AppError("INVALID_MESH", "유효한 표면을 생성하지 못했습니다.", 422)
            normals[i : i + 3] = [v / size for v in normals[i : i + 3]]
        meshes.append(
            {"name": name, "positions": positions, "normals": normals, "indices": indices}
        )

    def ring(y, rx, rz, x=0):
        return lambda theta: [x + rx * math.cos(theta), y, rz * math.sin(theta)]

    dims = spec["dimensions"]
    h, w, d = [dims[key]["value"] for key in ("length", "width", "depth")]
    kind = spec["garment_type"]
    if spec["category"] == "bottom":
        if kind == "스커트":
            surface(
                "skirt",
                [
                    ring(0, w * 0.80, d * 0.85),
                    ring(h * 0.5, w * 0.62, d * 0.65),
                    ring(h, w * 0.5, d * 0.5),
                ],
            )
        else:
            surface(
                "waist",
                [
                    ring(h * 0.73, w * 0.48, d * 0.47),
                    ring(h * 0.90, w * 0.52, d * 0.52),
                    ring(h, w * 0.5, d * 0.5),
                ],
            )
            for sign, side in ((-1, "left"), (1, "right")):
                surface(
                    f"leg_{side}",
                    [
                        ring(y, rx, rz, sign * w * 0.25)
                        for y, rx, rz in (
                            (0, w * 0.18, d * 0.34),
                            (h * 0.4, w * 0.21, d * 0.41),
                            (h * 0.78, w * 0.26, d * 0.49),
                        )
                    ],
                )
    else:
        hem = 0.47 if spec["fit"] in {"slim", "슬림핏"} else 0.54
        if kind == "코트":
            hem = 0.65
        neck_width = min(w * 0.19, 0.10)

        def neck(theta):
            front_depth = 0.10 if spec["neckline"] == "브이넥" else 0.035
            front = max(0, math.sin(theta))
            return [
                neck_width * math.cos(theta),
                h - front_depth * front**3,
                d * 0.30 * math.sin(theta),
            ]

        surface(
            "body",
            [
                ring(0, w * hem, d * 0.48),
                ring(h * 0.40, w * 0.49, d * 0.50),
                ring(h * 0.78, w * 0.50, d * 0.50),
                ring(h * 0.94, w * 0.44, d * 0.42),
                neck,
            ],
            opening=spec["category"] == "outer",
        )
        if spec["neckline"] == "터틀넥":
            surface(
                "collar",
                [ring(h - 0.02, neck_width, d * 0.30), ring(h + 0.08, neck_width, d * 0.30)],
            )
        if not spec["sleeveless"]:
            length = dims["sleeve"]["value"]
            for sign, side in ((-1, "left"), (1, "right")):

                def sleeve_ring(t, sign=sign):
                    radius = 0.105 * (1 - 0.35 * t)
                    cx, cy = sign * (w * 0.43 + length * 0.52 * t), h * 0.82 - length * 0.85 * t
                    return lambda theta: [
                        cx + radius * 0.85 * math.cos(theta),
                        cy + sign * radius * 0.52 * math.cos(theta),
                        radius * math.sin(theta),
                    ]

                surface(f"sleeve_{side}", [sleeve_ring(t) for t in (1, 0.5, 0)])
    # 매우 긴 소매에서도 모델 하단을 y=0에 맞춘다.
    y_min = min(m["positions"][i] for m in meshes for i in range(1, len(m["positions"]), 3))
    for mesh in meshes:
        for i in range(1, len(mesh["positions"]), 3):
            mesh["positions"][i] -= y_min
    return meshes


def build_glb(spec, progress=None):
    if progress:
        progress("mesh")
    meshes = make_meshes(spec)
    quality = inspect_meshes(meshes) if spec.get("top_panel") or spec.get("pants") else None
    if quality and any(
        quality[k]
        for k in ("degenerate_triangles", "nonmanifold_edges", "inconsistent_winding_edges")
    ):
        raise AppError("INVALID_MESH", "메시 연결·면 방향 검사를 통과하지 못했습니다.", 422)
    if progress:
        progress("exporting")
    blob, views, accessors, gltf_meshes = bytearray(), [], [], []

    def accessor(values, code, component, size, target):
        offset = len(blob)
        blob.extend(struct.pack(f"<{len(values)}{code}", *values))
        length = len(blob) - offset
        blob.extend(b"\0" * (-len(blob) % 4))
        views.append({"buffer": 0, "byteOffset": offset, "byteLength": length, "target": target})
        entry = {
            "bufferView": len(views) - 1,
            "componentType": component,
            "count": len(values) // size,
            "type": {1: "SCALAR", 2: "VEC2", 3: "VEC3"}[size],
        }
        if size == 3:
            entry.update(
                min=[min(values[k::3]) for k in range(3)], max=[max(values[k::3]) for k in range(3)]
            )
        accessors.append(entry)
        return len(accessors) - 1

    for mesh in meshes:
        position = accessor(mesh["positions"], "f", 5126, 3, 34962)
        normal = accessor(mesh["normals"], "f", 5126, 3, 34962)
        indices = accessor(mesh["indices"], "H", 5123, 1, 34963)
        uv = accessor(mesh["uvs"], "f", 5126, 2, 34962) if mesh.get("uvs") else None
        gltf_meshes.append(
            {
                "name": mesh["name"],
                "primitives": [
                    {
                        "attributes": {"POSITION": position, "NORMAL": normal},
                        "indices": indices,
                        "material": 0,
                        "mode": 4,
                    }
                ],
            }
        )
        if uv is not None:
            gltf_meshes[-1]["primitives"][0]["attributes"]["TEXCOORD_0"] = uv
    minimum = [min(min(m["positions"][i::3]) for m in meshes) for i in range(3)]
    maximum = [max(max(m["positions"][i::3]) for m in meshes) for i in range(3)]
    metadata = {
        "engine": "template",
        "generation_kind": "procedural",
        "category": spec["category"],
        "garment_type": spec["garment_type"],
        "unit": "meter",
        "coordinate_system": "y_up_z_front",
        "handedness": "right",
        "bounds": {"min": minimum, "max": maximum},
        "pivot": [0, 0, 0],
        "attachment_anchor": [0, maximum[1] * (0.78 if spec["category"] == "top" else 1), 0],
        "mannequin_anchor": {"top": "chest", "bottom": "waist", "outer": "shoulder"}[
            spec["category"]
        ],
        "layer": {"top": 1, "bottom": 1, "outer": 2}[spec["category"]],
        "dimensions": spec["dimensions"],
        "mode": spec.get("mode", "A"),
        "version": "stylefit-panel-3.0"
        if spec.get("top_panel")
        else PANTS_VERSION
        if spec.get("pants")
        else VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "color": spec["color"],
        "color_source": spec["color_source"],
        "analysis_views": spec["analysis_views"],
        "back_geometry": "estimated",
        "back_observed": spec["back_observed"],
        "mesh_names": [m["name"] for m in meshes],
        "material_names": ["generic_fabric"],
        "triangle_count": sum(len(m["indices"]) // 3 for m in meshes),
        "physical_simulation": False,
        "fitting_contract": "stylefit.panel.v3"
        if spec.get("top_panel")
        else "stylefit.pants.v2"
        if spec.get("pants")
        else "stylefit.parts.v1",
        "template_asset_source": "project_original_procedural",
        "warnings": [
            "깊이·후면·봉제 구조는 추정입니다.",
            "사진 텍스처·로고·고유 그래픽은 재현하지 않습니다.",
            "단순 메시 변형이며 원단 움직임·정밀 피팅을 재현하지 않습니다.",
        ],
    }
    if spec.get("top_panel"):
        metadata["top_panel"] = spec["top_panel"]
        metadata["shape_source"] = (
            "photo_silhouette_estimate" if spec["top_panel"]["observed"] else "estimated"
        )
        metadata["warnings"] = [
            "앞뒤 패널을 연결한 직접 제작 템플릿의 근사입니다. AI 고정밀 복원이 아닙니다.",
            "깊이·후면·주름·목 구조는 추정입니다.",
            *spec["top_panel"]["warnings"],
        ]
    elif not spec.get("pants"):
        metadata["warnings"].append(
            "구형 절차적 근사 템플릿입니다. 연결 패널 템플릿은 아직 티셔츠만 지원합니다."
        )
    metadata["mesh_quality"] = quality
    metadata["material_profile"] = spec.get(
        "material_profile", {"roughness": 0.88, "source": "generic_estimate"}
    )
    texture, texture_policy = (
        pants_materials(spec)
        if spec.get("pants")
        or (spec.get("top_panel") and (spec["pattern"] == "check" or spec.get("mode") == "B"))
        else (None, "solid_color")
    )
    metadata["texture_policy"] = texture_policy
    if spec.get("mode") == "B":
        metadata["version"] = "stylefit-photo-projection-1.0"
        metadata["photo_appearance"] = {
            "front": "verified_photo",
            "back": "verified_photo" if spec.get("_back_png") else "estimated",
            "geometry": "template_with_observed_silhouette",
            "uv_origin": "top_left",
            "background_edge_bleed": True,
        }
        metadata["back_appearance"] = (
            "verified_photo" if spec.get("_back_png") else "generic_estimated"
        )
        metadata["reconstruction_fidelity"] = (
            "front_back_projection_approximation"
            if spec.get("_back_png")
            else "single_view_projection_approximation"
        )
        metadata["warnings"] = [
            "사진의 색·무늬를 템플릿 표면에 투영했습니다. AI 고정밀 복원이 아닙니다.",
            "후면 사진을 반영했지만 깊이·옆면·봉제 구조는 추정입니다."
            if spec.get("_back_png")
            else "후면 사진이 없어 뒷면은 일반 원단으로 추정합니다.",
        ]
    if spec.get("pants"):
        metadata["pants"] = spec["pants"]
        metadata["surface_detail"] = "flattened_cloth_section_drape_folded_edges"
        metadata["detail_source"] = "procedural_estimate"
        metadata["shape_source"] = (
            "photo_silhouette_estimate" if spec["pants"]["observed"] else "estimated"
        )
        metadata.setdefault("back_appearance", "generic_estimated")
        metadata.setdefault(
            "reconstruction_fidelity",
            (
                "single_view_projection_approximation"
                if spec.get("mode") == "B"
                else "generic_silhouette_approximation"
            ),
        )
        metadata["warnings"] = ([*metadata["warnings"]] if spec.get("mode") == "B" else []) + [
            "사진 외곽은 투영 비율의 추정입니다. 깊이·후면·봉제 구조는 추정입니다.",
            "고무줄 주름은 일반적인 절차적 표현이며 실제 주름 복원이 아닙니다.",
            "B 사진 투영은 고정밀 입체 복원이 아니며 옆면·깊이·가려진 부위는 추정입니다."
            if spec.get("mode") == "B"
            else "체크는 자체 생성한 일반 패턴이며 원본 픽셀·로고·고유 그래픽을 복제하지 않습니다.",
            *spec["pants"]["warnings"],
        ]

    def linear(channel):
        c = int(channel, 16) / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    color = [1, 1, 1, 1] if texture else [linear(spec["color"][i : i + 2]) for i in (1, 3, 5)] + [1]
    image_view = None
    if texture:
        image_view = len(views)
        views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(texture)})
        blob.extend(texture)
        blob.extend(b"\0" * (-len(blob) % 4))
    document = {
        "asset": {"version": "2.0", "generator": metadata["version"]},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [
            {
                "name": "garment_root",
                "children": list(range(1, len(meshes) + 1)),
                "extras": metadata,
            }
        ]
        + [{"name": m["name"], "mesh": i} for i, m in enumerate(meshes)],
        "meshes": gltf_meshes,
        "materials": [
            {
                "name": "generic_fabric",
                "doubleSided": True,
                "pbrMetallicRoughness": {
                    "baseColorFactor": color,
                    "metallicFactor": 0,
                    "roughnessFactor": spec.get("material_profile", {}).get("roughness", 0.88),
                },
            }
        ],
        "buffers": [{"byteLength": len(blob)}],
        "bufferViews": views,
        "accessors": accessors,
    }
    if image_view is not None:
        document["images"] = [{"bufferView": image_view, "mimeType": "image/png"}]
        document["samplers"] = [
            {"wrapS": 33071, "wrapT": 33071, "magFilter": 9729, "minFilter": 9987}
        ]
        document["textures"] = [{"source": 0, "sampler": 0}]
        document["materials"][0]["pbrMetallicRoughness"]["baseColorTexture"] = {"index": 0}
    json_bytes = json.dumps(
        document, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode()
    json_bytes += b" " * (-len(json_bytes) % 4)
    result = (
        struct.pack("<4sII", b"glTF", 2, 28 + len(json_bytes) + len(blob))
        + struct.pack("<I4s", len(json_bytes), b"JSON")
        + json_bytes
        + struct.pack("<I4s", len(blob), b"BIN\0")
        + blob
    )
    if progress:
        progress("validating")
    validate_glb(result)
    return result, metadata


def validate_glb(content):
    """생성 파일을 재파싱해 유한 좌표·인덱스·3차원 범위·재질 연결을 검증한다."""
    magic, version, length = struct.unpack_from("<4sII", content)
    if magic != b"glTF" or version != 2 or length != len(content):
        raise ValueError("invalid GLB header")
    json_length, kind = struct.unpack_from("<I4s", content, 12)
    if kind != b"JSON" or json_length % 4:
        raise ValueError("invalid JSON chunk")
    doc = json.loads(content[20 : 20 + json_length])
    if not all(doc.get(key) for key in ("meshes", "nodes", "materials", "scenes")):
        raise ValueError("empty GLB scene")
    binary_length, kind = struct.unpack_from("<I4s", content, 20 + json_length)
    binary = content[28 + json_length :]
    if (
        kind != b"BIN\0"
        or binary_length != len(binary)
        or doc["buffers"][0]["byteLength"] != len(binary)
    ):
        raise ValueError("invalid binary chunk")
    if "images" in doc or "textures" in doc:
        meta = doc["nodes"][0].get("extras", {})
        if len(doc.get("images", [])) != 1 or len(doc.get("textures", [])) != 1:
            raise ValueError("unexpected texture")
        picture = doc["images"][0]
        if "uri" in picture or picture.get("mimeType") != "image/png":
            raise ValueError("embedded PNG required")
        view = doc["bufferViews"][picture["bufferView"]]
        png = binary[view["byteOffset"] : view["byteOffset"] + view["byteLength"]]
        if meta.get("mode") == "A":
            if meta.get("texture_policy") != "procedural_generic_check" or png != (
                legacy_check if meta.get("version") == "stylefit-pants-2.0" else generic_check
            )(meta["color"]):
                raise ValueError("A source texture forbidden")
        elif meta.get("mode") != "B" or meta.get("texture_policy") != "verified_front_projection":
            raise ValueError("texture policy missing")
    for mesh in doc["meshes"]:
        primitive = mesh["primitives"][0]
        p = doc["accessors"][primitive["attributes"]["POSITION"]]
        bounds = [p["max"][i] - p["min"][i] for i in range(3)]
        if min(bounds) <= 0.005 or max(bounds) > 3:
            raise ValueError("invalid 3D bounds")
        if primitive["material"] >= len(doc["materials"]):
            raise ValueError("missing material")
        for key, code in (("POSITION", "f"), ("NORMAL", "f")):
            a = doc["accessors"][primitive["attributes"][key]]
            view = doc["bufferViews"][a["bufferView"]]
            values = struct.unpack_from(f"<{a['count'] * 3}{code}", binary, view["byteOffset"])
            if not all(math.isfinite(v) for v in values):
                raise ValueError("non-finite vertex")
        if "TEXCOORD_0" in primitive["attributes"]:
            a = doc["accessors"][primitive["attributes"]["TEXCOORD_0"]]
            if a["type"] != "VEC2" or a["count"] != p["count"]:
                raise ValueError("invalid UV layout")
            view = doc["bufferViews"][a["bufferView"]]
            values = struct.unpack_from(f"<{a['count'] * 2}f", binary, view["byteOffset"])
            if not all(math.isfinite(v) and -0.0001 <= v <= 1.0001 for v in values):
                raise ValueError("invalid UV coordinates")
        a = doc["accessors"][primitive["indices"]]
        view = doc["bufferViews"][a["bufferView"]]
        ids = struct.unpack_from(f"<{a['count']}H", binary, view["byteOffset"])
        if not ids or len(ids) % 3 or max(ids) >= p["count"]:
            raise ValueError("invalid triangles")
    return doc
