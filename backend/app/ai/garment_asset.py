"""의류 누끼 → 3D 메시 에셋 (MVP 수준).

방식: 누끼 마스크 안쪽을 '부풀린' 앞면·뒷면 메시를 만들고 누끼 이미지를 텍스처로 입힌다.
경계에서 두께 0, 안쪽으로 갈수록 두꺼워지며(거리변환의 제곱근 프로파일) 앞뒤가 경계에서 이어진 닫힌 메시다.
사진 한 장에서 실제 옷 형태(소매 입체감, 주름, 뒷면 무늬)를 복원하는 것은 아니며,
3D 뷰어에서 옷장 아이템을 입체 카드처럼 보여 주는 용도다. 드레이핑·아바타 착장은 M+6 범위.

출력: .glb (Three.js / R3F 권장 형식, CONVENTIONS 3절), .obj+.mtl+.png (확인용)
"""

from __future__ import annotations

import json
import math
import struct
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

ALPHA_THRESHOLD = 127
DEFAULT_GRID_MAX = 160  # 긴 변 기준 격자 수. 높을수록 매끈하지만 정점 수가 제곱으로 는다.
DEFAULT_DEPTH_RATIO = 0.12  # 가장 두꺼운 곳의 앞면 높이 = 옷 너비 × 이 비율
DEFAULT_BACK_RATIO = 0.8  # 뒷면은 앞면보다 조금 납작하게 (등판이 평평한 옷이 많아서)
DEFAULT_SMOOTH_ITERS = 8  # 라플라시안 스무딩 횟수. 0이면 격자 그대로 (계단·주름이 보임)
MASK_BLUR_RATIO = 0.006  # 윤곽 다듬기 블러 = 긴 변 × 비율. 세그멘테이션의 톱니 모양 가장자리를 펴 준다
HEIGHT_BLUR_RATIO = 0.03  # 두께 지도 블러 = 긴 변 × 비율. 거리변환의 가운데 능선(접힌 자국)을 없앤다


@dataclass
class GarmentMesh:
    """좌표 단위: height_m을 주면 미터, 아니면 높이 1로 정규화."""

    positions: np.ndarray  # (V, 3) float32, Y가 위
    normals: np.ndarray  # (V, 3) float32
    uvs: np.ndarray  # (V, 2) float32, 이미지 좌표계 (0,0)=왼쪽 위
    faces: np.ndarray  # (F, 3) uint32, 반시계 = 바깥
    texture_rgba: np.ndarray  # (H, W, 4) uint8


def bleed_texture(rgba: np.ndarray) -> np.ndarray:
    """투명 영역을 가장 가까운 옷 색으로 채운다. 경계 UV가 배경색을 집어 테두리가 생기는 것을 막는다."""
    fg = rgba[..., 3] > ALPHA_THRESHOLD
    if not fg.any() or fg.all():
        return rgba.copy()
    _, labels = cv2.distanceTransformWithLabels((~fg).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    ys, xs = np.nonzero(fg)  # 전경 픽셀 = 거리 0 픽셀 = 라벨 소스
    lookup = np.zeros((labels.max() + 1, 3), dtype=np.uint8)
    lookup[labels[ys, xs]] = rgba[ys, xs, :3]
    out = rgba.copy()
    out[..., :3] = lookup[labels]
    out[fg, :3] = rgba[fg, :3]
    return out


def _grid(mask: np.ndarray, grid_max: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    h, w = mask.shape
    step = max(1, math.ceil(max(h, w) / grid_max))
    gx = np.arange(0, w, step)
    gy = np.arange(0, h, step)
    inside = mask[np.ix_(gy, gx)]
    return gx, gy, inside


def _valid_cells(inside: np.ndarray) -> np.ndarray:
    return inside[:-1, :-1] & inside[:-1, 1:] & inside[1:, :-1] & inside[1:, 1:]


def _boundary_edges(faces: np.ndarray) -> np.ndarray:
    """한 면에만 속한 방향 있는 모서리 (a→b) 목록 = 윤곽선."""
    directed = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    keys = np.sort(directed, axis=1)
    _, inverse, counts = np.unique(keys, axis=0, return_inverse=True, return_counts=True)
    return directed[counts[inverse.ravel()] == 1]


def _stitch_faces(edges: np.ndarray, offset: int) -> np.ndarray:
    """앞면 윤곽 모서리 a→b와 뒷면 a'→b'를 잇는 띠. 두 면 모두 두께 0인 경계라 면적은 0이지만
    위상적으로 앞뒤가 이어져 닫힌(watertight) 메시가 된다."""
    a, b = edges[:, 0], edges[:, 1]
    return np.concatenate([np.stack([b, a, a + offset], 1), np.stack([b, a + offset, b + offset], 1)])


def _smooth_mask(alpha: np.ndarray) -> np.ndarray:
    """알파를 살짝 블러한 뒤 다시 이진화해 윤곽선을 매끈하게 만든다."""
    sigma = max(1.0, MASK_BLUR_RATIO * max(alpha.shape))
    return cv2.GaussianBlur(alpha, (0, 0), sigma) > ALPHA_THRESHOLD


def _height_map(mask: np.ndarray, depth_px: float) -> np.ndarray:
    """경계 0 → 안쪽으로 둥글게 솟는 두께 지도 (픽셀 단위)."""
    dist = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 5)
    dist = cv2.GaussianBlur(dist, (0, 0), max(1.0, HEIGHT_BLUR_RATIO * max(mask.shape)))
    dist = dist * mask
    return depth_px * np.sqrt(np.clip(dist / max(float(dist.max()), 1e-6), 0.0, 1.0))


def _snap_to_contour(points: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """격자에 걸린 윤곽 정점(x, y 픽셀)을 실제 윤곽선 위 가장 가까운 점으로 옮긴다 → 계단 제거."""
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    contour = np.concatenate([c.reshape(-1, 2) for c in contours]).astype(np.float32)
    snapped = np.empty_like(points)
    chunk = 512  # (정점 × 윤곽점) 거리 행렬이 너무 커지지 않게 나눠서
    for i in range(0, len(points), chunk):
        block = points[i : i + chunk]
        d2 = ((block[:, None, :] - contour[None, :, :]) ** 2).sum(-1)
        snapped[i : i + chunk] = contour[d2.argmin(1)]
    return snapped


def _laplacian_smooth(values: np.ndarray, edges: np.ndarray, fixed: np.ndarray, iters: int) -> np.ndarray:
    """이웃 평균 쪽으로 반씩 당기기를 반복. fixed 정점(윤곽)은 움직이지 않는다."""
    out = values.astype(np.float64).copy()
    a, b = edges[:, 0], edges[:, 1]
    degree = np.bincount(np.concatenate([a, b]), minlength=len(out)).astype(np.float64)
    degree = np.maximum(degree, 1.0).reshape(-1, *([1] * (out.ndim - 1)))
    for _ in range(iters):
        acc = np.zeros_like(out)
        np.add.at(acc, a, out[b])
        np.add.at(acc, b, out[a])
        moved = out + 0.5 * (acc / degree - out)
        out = np.where(fixed.reshape(-1, *([1] * (out.ndim - 1))), out, moved)
    return out


def _compute_normals(positions: np.ndarray, faces: np.ndarray) -> np.ndarray:
    tri = positions[faces]
    face_n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    normals = np.zeros_like(positions)
    for k in range(3):
        np.add.at(normals, faces[:, k], face_n)
    length = np.linalg.norm(normals, axis=1, keepdims=True)
    return (normals / np.maximum(length, 1e-12)).astype(np.float32)


def _quad_faces(idx: np.ndarray, cells: np.ndarray, flip: bool) -> np.ndarray:
    """격자 셀 → 삼각형 2개씩. 이미지 y가 아래로 커지므로 월드(Y 위)에서 반시계가 되게 묶는다."""
    ci, cj = np.nonzero(cells)
    v00, v01 = idx[ci, cj], idx[ci, cj + 1]
    v10, v11 = idx[ci + 1, cj], idx[ci + 1, cj + 1]
    tris = np.concatenate([np.stack([v10, v11, v01], 1), np.stack([v10, v01, v00], 1)])
    return tris[:, ::-1] if flip else tris


def build_garment_mesh(
    rgba: np.ndarray,
    grid_max: int = DEFAULT_GRID_MAX,
    depth_ratio: float = DEFAULT_DEPTH_RATIO,
    back_ratio: float = DEFAULT_BACK_RATIO,
    height_m: float | None = None,
    smooth_iters: int = DEFAULT_SMOOTH_ITERS,
) -> GarmentMesh:
    """RGBA 누끼 → 부풀린 닫힌 메시. 마스크가 너무 작으면 ValueError.

    품질 단계: 윤곽 블러 → 격자 메시 → 윤곽 정점을 실제 윤곽선으로 이동(계단 제거)
    → 안쪽 정점 위치·두께 라플라시안 스무딩(격자 무늬·능선 제거).
    """
    mask = _smooth_mask(rgba[..., 3])
    gx, gy, inside = _grid(mask, grid_max)
    cells = _valid_cells(inside)
    if not cells.any():
        raise ValueError("누끼 영역이 너무 작아 메시를 만들 수 없습니다.")
    used = np.zeros(inside.shape, dtype=bool)
    for di, dj in ((0, 0), (0, 1), (1, 0), (1, 1)):
        used[di : di + cells.shape[0], dj : dj + cells.shape[1]] |= cells
    n_used = int(used.sum())
    vert_idx = np.full(inside.shape, -1, dtype=np.int64)
    vert_idx[used] = np.arange(n_used)
    front = _quad_faces(vert_idx, cells, flip=False)
    outline = _boundary_edges(front)
    on_outline = np.zeros(n_used, dtype=bool)
    on_outline[outline.ravel()] = True
    edges = np.unique(np.sort(np.concatenate([front[:, [0, 1]], front[:, [1, 2]], front[:, [2, 0]]]), axis=1), axis=0)

    # 정점 위치 (픽셀 좌표): 윤곽은 실제 윤곽선으로, 안쪽은 스무딩으로 고르게
    jj, ii = np.meshgrid(gx, gy)
    px = np.stack([jj[used], ii[used]], 1).astype(np.float32)
    px[on_outline] = _snap_to_contour(px[on_outline], mask)
    px = _laplacian_smooth(px, edges, on_outline, smooth_iters).astype(np.float32)

    depth_px = depth_ratio * (gx[-1] - gx[0] + 1)
    heights = _height_map(mask, depth_px)
    xi = np.clip(np.round(px[:, 0]).astype(int), 0, mask.shape[1] - 1)
    yi = np.clip(np.round(px[:, 1]).astype(int), 0, mask.shape[0] - 1)
    z = heights[yi, xi]
    z[on_outline] = 0.0  # 윤곽에서 앞뒤가 만나도록
    z = _laplacian_smooth(z, edges, on_outline, smooth_iters)

    h, w = mask.shape
    scale = (height_m or 1.0) / h
    xy = np.stack([(px[:, 0] - w / 2.0) * scale, (h / 2.0 - px[:, 1]) * scale], 1)
    positions = np.concatenate(
        [
            np.column_stack([xy, z * scale]),
            np.column_stack([xy, -back_ratio * z * scale]),
        ]
    ).astype(np.float32)
    uv = np.stack([(px[:, 0] + 0.5) / w, (px[:, 1] + 0.5) / h], 1)
    uvs = np.concatenate([uv, uv]).astype(np.float32)
    back = _quad_faces(vert_idx + n_used, cells, flip=True)
    faces = np.concatenate([front, back, _stitch_faces(outline, n_used)]).astype(np.uint32)
    return GarmentMesh(positions, _compute_normals(positions, faces), uvs, faces, bleed_texture(rgba))


def _encode_png(rgba: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))
    if not ok:
        raise ValueError("PNG 인코딩 실패")
    return buf.tobytes()


def write_obj(mesh: GarmentMesh, obj_path: Path) -> None:
    """OBJ + MTL + 텍스처 PNG. OBJ의 UV 원점은 왼쪽 아래라 v를 뒤집는다."""
    obj_path.parent.mkdir(parents=True, exist_ok=True)
    tex_name = obj_path.with_suffix(".png").name
    mtl_name = obj_path.with_suffix(".mtl").name
    obj_path.with_suffix(".png").write_bytes(_encode_png(mesh.texture_rgba))
    obj_path.with_suffix(".mtl").write_text(
        f"newmtl garment\nKa 1 1 1\nKd 1 1 1\nKs 0 0 0\nmap_Kd {tex_name}\n", encoding="utf-8"
    )
    lines = [f"mtllib {mtl_name}", "usemtl garment"]
    lines += [f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in mesh.positions]
    lines += [f"vt {u:.6f} {1.0 - v:.6f}" for u, v in mesh.uvs]
    lines += [f"vn {x:.6f} {y:.6f} {z:.6f}" for x, y, z in mesh.normals]
    lines += [f"f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}" for a, b, c in (mesh.faces + 1)]
    obj_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _pad4(data: bytes, pad: bytes = b"\x00") -> bytes:
    return data + pad * ((4 - len(data) % 4) % 4)


def write_glb(mesh: GarmentMesh, glb_path: Path) -> None:
    """텍스처를 내장한 단일 .glb (glTF 2.0). 외부 라이브러리 없이 직접 쓴다."""
    chunks = [
        mesh.positions.astype("<f4").tobytes(),
        mesh.normals.astype("<f4").tobytes(),
        mesh.uvs.astype("<f4").tobytes(),
        mesh.faces.astype("<u4").tobytes(),
        _encode_png(mesh.texture_rgba),
    ]
    views, blob = [], b""
    for i, data in enumerate(chunks):
        view = {"buffer": 0, "byteOffset": len(blob), "byteLength": len(data)}
        if i < 3:
            view["target"] = 34962  # ARRAY_BUFFER
        elif i == 3:
            view["target"] = 34963  # ELEMENT_ARRAY_BUFFER
        views.append(view)
        blob += _pad4(data)
    n_vert = len(mesh.positions)
    gltf = {
        "asset": {"version": "2.0", "generator": "closet-verse garment_asset"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "garment"}],
        "meshes": [
            {
                "primitives": [
                    {
                        "attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2},
                        "indices": 3,
                        "material": 0,
                    }
                ]
            }
        ],
        "materials": [
            {
                "name": "garment",
                "pbrMetallicRoughness": {
                    "baseColorTexture": {"index": 0},
                    "metallicFactor": 0.0,
                    "roughnessFactor": 0.9,
                },
            }
        ],
        "textures": [{"source": 0, "sampler": 0}],
        "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 33071, "wrapT": 33071}],
        "images": [{"bufferView": 4, "mimeType": "image/png"}],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5126,
                "count": n_vert,
                "type": "VEC3",
                "min": mesh.positions.min(0).tolist(),
                "max": mesh.positions.max(0).tolist(),
            },
            {"bufferView": 1, "componentType": 5126, "count": n_vert, "type": "VEC3"},
            {"bufferView": 2, "componentType": 5126, "count": n_vert, "type": "VEC2"},
            {"bufferView": 3, "componentType": 5125, "count": int(mesh.faces.size), "type": "SCALAR"},
        ],
        "bufferViews": views,
        "buffers": [{"byteLength": len(blob)}],
    }
    json_bytes = _pad4(json.dumps(gltf, separators=(",", ":")).encode("utf-8"), b" ")
    total = 12 + 8 + len(json_bytes) + 8 + len(blob)
    glb_path.parent.mkdir(parents=True, exist_ok=True)
    with glb_path.open("wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))  # 'glTF'
        f.write(struct.pack("<II", len(json_bytes), 0x4E4F534A))  # 'JSON'
        f.write(json_bytes)
        f.write(struct.pack("<II", len(blob), 0x004E4942))  # 'BIN\0'
        f.write(blob)
