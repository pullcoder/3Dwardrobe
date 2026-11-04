"""자체 포함 삼각형 GLB를 재로딩한다. 개구부·충돌·실루엣 적합성은 미검증으로 둔다."""

import json
import math
import struct
from io import BytesIO

from PIL import Image

from app.services.mesh_quality import inspect_meshes


def inspect_glb(content):
    if len(content) < 28 or len(content) > 32 * 1024 * 1024:
        raise ValueError("invalid GLB size")
    magic, version, size = struct.unpack_from("<4sII", content)
    if (magic, version, size) != (b"glTF", 2, len(content)):
        raise ValueError("invalid GLB header")
    length, kind = struct.unpack_from("<I4s", content, 12)
    if kind != b"JSON" or length % 4 or 28 + length > size:
        raise ValueError("invalid JSON chunk")
    doc = json.loads(content[20 : 20 + length])
    bin_size, kind = struct.unpack_from("<I4s", content, 20 + length)
    binary = content[28 + length :]
    if kind != b"BIN\0" or bin_size != len(binary):
        raise ValueError("invalid binary chunk")
    if len(doc.get("buffers", [])) != 1 or doc["buffers"][0].get("byteLength", 0) > bin_size:
        raise ValueError("invalid buffers")
    if any("uri" in x for x in doc.get("buffers", []) + doc.get("images", [])):
        raise ValueError("external resources forbidden")
    if doc.get("extensionsRequired"):
        raise ValueError("unreviewed required extension")

    def reference(key, index):
        if not isinstance(index, int) or not 0 <= index < len(doc.get(key, [])):
            raise ValueError("invalid GLB reference")
        return doc[key][index]

    def values(index, width, allowed):
        accessor = reference("accessors", index)
        if "sparse" in accessor or accessor["componentType"] not in allowed:
            raise ValueError("unsupported accessor")
        types = {1: "SCALAR", 2: "VEC2", 3: "VEC3", 4: "VEC4"}
        if accessor["type"] != types[width] or not 0 < accessor["count"] <= 1_000_000:
            raise ValueError("invalid accessor shape")
        view = reference("bufferViews", accessor["bufferView"])
        if view.get("buffer", 0) != 0:
            raise ValueError("invalid buffer reference")
        code, byte_count = {5121: ("B", 1), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}[
            accessor["componentType"]
        ]
        stride = view.get("byteStride", width * byte_count)
        offset = accessor.get("byteOffset", 0)
        start = view.get("byteOffset", 0)
        end = start + view["byteLength"]
        if (
            stride < width * byte_count
            or min(start, offset) < 0
            or end > len(binary)
            or offset + (accessor["count"] - 1) * stride + width * byte_count > view["byteLength"]
        ):
            raise ValueError("accessor out of bounds")
        out = []
        for i in range(accessor["count"]):
            out.extend(struct.unpack_from(f"<{width}{code}", binary, start + offset + i * stride))
        if not all(math.isfinite(x) for x in out):
            raise ValueError("nonfinite accessor")
        return out

    meshes, uv_count, vertices, triangles = [], 0, 0, 0
    for mesh in doc.get("meshes", []):
        for primitive in mesh["primitives"]:
            if primitive.get("mode", 4) != 4:
                raise ValueError("triangles required")
            positions = values(primitive["attributes"]["POSITION"], 3, {5126})
            ids = values(primitive["indices"], 1, {5121, 5123, 5125})
            count = len(positions) // 3
            if not ids or len(ids) % 3 or max(ids) >= count:
                raise ValueError("invalid faces")
            if "NORMAL" in primitive["attributes"]:
                normals = values(primitive["attributes"]["NORMAL"], 3, {5126})
                if len(normals) != len(positions):
                    raise ValueError("invalid normals")
            if "TEXCOORD_0" in primitive["attributes"]:
                uv = values(primitive["attributes"]["TEXCOORD_0"], 2, {5126})
                if len(uv) != count * 2:
                    raise ValueError("invalid UV count")
                uv_count += 1
            if "material" in primitive and not 0 <= primitive["material"] < len(
                doc.get("materials", [])
            ):
                raise ValueError("invalid material")
            meshes.append({"positions": positions, "indices": ids})
            vertices += count
            triangles += len(ids) // 3
            if vertices > 300_000 or triangles > 500_000:
                raise ValueError("mesh budget exceeded")
    if not meshes or not doc.get("nodes") or not doc.get("scenes"):
        raise ValueError("empty scene")
    for image in doc.get("images", []):
        if image.get("mimeType") not in {"image/png", "image/jpeg"}:
            raise ValueError("unreviewed embedded image")
        view = reference("bufferViews", image["bufferView"])
        if (
            view.get("byteOffset", 0) < 0
            or view.get("byteOffset", 0) + view["byteLength"] > bin_size
        ):
            raise ValueError("invalid embedded image bounds")
        start = view.get("byteOffset", 0)
        with Image.open(BytesIO(binary[start : start + view["byteLength"]])) as picture:
            if picture.width * picture.height > 20_000_000:
                raise ValueError("texture budget exceeded")
            picture.verify()
    for texture in doc.get("textures", []):
        reference("images", texture["source"])
        if "sampler" in texture:
            reference("samplers", texture["sampler"])
    for material in doc.get("materials", []):
        pbr = material.get("pbrMetallicRoughness", {})
        for texture in (
            pbr.get("baseColorTexture"),
            pbr.get("metallicRoughnessTexture"),
            material.get("normalTexture"),
            material.get("occlusionTexture"),
            material.get("emissiveTexture"),
        ):
            if texture:
                reference("textures", texture["index"])
    quality = inspect_meshes(meshes)
    if quality["degenerate_triangles"] or quality["nonmanifold_edges"]:
        raise ValueError("abnormal mesh topology")
    return {
        "vertex_count": vertices,
        "triangle_count": triangles,
        "bytes": size,
        "uv_primitives": uv_count,
        "materials": len(doc.get("materials", [])),
        "images": len(doc.get("images", [])),
        "topology": quality,
        "glb_reloaded": True,
        "silhouette_accuracy": "unverified",
        "openings": "unverified",
        "thickness": "unverified",
        "body_collisions": "unverified",
        "wearable": False,
    }
