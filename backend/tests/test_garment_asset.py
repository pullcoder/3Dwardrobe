import struct
from collections import Counter

import cv2
import numpy as np

from app.ai.config import SEG_CLASSES
from app.ai.cutout import extract_cutouts
from app.ai.garment_asset import build_garment_mesh, write_glb, write_obj


def ellipse_rgba(h: int = 240, w: int = 160) -> np.ndarray:
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[..., :3] = (200, 30, 30)
    alpha = np.zeros((h, w), dtype=np.uint8)
    cv2.ellipse(alpha, (w // 2, h // 2), (w // 2 - 10, h // 2 - 10), 0, 0, 360, 255, -1)
    rgba[..., 3] = alpha
    return rgba


def test_extract_cutouts_drops_noise():
    image = np.full((100, 100, 3), 255, dtype=np.uint8)
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[20:80, 20:80] = 1  # top
    mask[0, 0] = 2  # 1픽셀 잡음 → 버려져야 함
    cuts = extract_cutouts(image, mask, SEG_CLASSES)
    assert [c.slot for c in cuts] == ["top"]
    assert cuts[0].rgba.shape[2] == 4
    assert 0.3 < cuts[0].area_ratio < 0.4


def test_mesh_is_closed_and_inflated():
    mesh = build_garment_mesh(ellipse_rgba(), grid_max=48)
    edges = Counter()
    for a, b, c in mesh.faces.tolist():
        for e in ((a, b), (b, c), (c, a)):
            edges[tuple(sorted(e))] += 1
    assert set(edges.values()) == {2}  # 모든 모서리가 정확히 두 면에 공유 = 닫힌 메시
    assert mesh.positions[:, 2].max() > 0 > mesh.positions[:, 2].min()
    height = mesh.positions[:, 1].max() - mesh.positions[:, 1].min()
    assert 0.8 < height <= 1.0
    assert mesh.uvs.min() >= 0 and mesh.uvs.max() <= 1


def test_front_faces_point_forward():
    mesh = build_garment_mesh(ellipse_rgba(), grid_max=32)
    tri = mesh.positions[mesh.faces]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    center_z = tri[:, :, 2].mean(1)
    assert (n[center_z > 0.01, 2] > 0).mean() > 0.95
    assert (n[center_z < -0.01, 2] < 0).mean() > 0.95


def test_write_glb_and_obj(tmp_path):
    mesh = build_garment_mesh(ellipse_rgba(), grid_max=32, height_m=0.7)
    glb = tmp_path / "top.glb"
    write_glb(mesh, glb)
    data = glb.read_bytes()
    magic, version, length = struct.unpack("<III", data[:12])
    assert magic == 0x46546C67 and version == 2 and length == len(data)
    write_obj(mesh, tmp_path / "top.obj")
    assert (tmp_path / "top.mtl").exists() and (tmp_path / "top.png").exists()
