"""K-Fashion 형식을 흉내 낸 가짜 샘플 (실제 AI Hub 데이터는 저장소에 넣지 않는다)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

IMG_W, IMG_H = 200, 300
TOP_BOX = (50, 40, 150, 150)  # x1, y1, x2, y2
BOTTOM_BOX = (60, 150, 140, 280)


def box_polygon(x1: int, y1: int, x2: int, y2: int) -> dict[str, float]:
    pts = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
    entry: dict[str, float] = {}
    for i, (x, y) in enumerate(pts, start=1):
        entry[f"X좌표{i}"] = float(x)
        entry[f"Y좌표{i}"] = float(y)
    return entry


def shifted(box: tuple[int, int, int, int], dx: int, dy: int) -> tuple[int, int, int, int]:
    return box[0] + dx, box[1] + dy, box[2] + dx, box[3] + dy


def make_label(file_name: str, dx: int = 0, dy: int = 0) -> dict:
    return {
        "이미지 정보": {"이미지 식별자": 1, "이미지 파일명": file_name, "이미지 너비": IMG_W, "이미지 높이": IMG_H},
        "데이터셋 정보": {
            "데이터셋 상세설명": {
                "렉트좌표": {"아우터": [{}], "하의": [{}], "원피스": [{}], "상의": [{}]},
                "폴리곤좌표": {
                    "아우터": [{}],
                    "하의": [box_polygon(*shifted(BOTTOM_BOX, dx, dy))],
                    "원피스": [{}],
                    "상의": [box_polygon(*shifted(TOP_BOX, dx, dy))],
                },
                "라벨링": {
                    "스타일": [{"스타일": "스트리트"}],
                    "아우터": [{}],
                    "하의": [{"카테고리": "청바지", "색상": "블루"}],
                    "원피스": [{}],
                    "상의": [{"카테고리": "티셔츠", "색상": "레드"}],
                },
            }
        },
    }


def make_image(dx: int = 0, dy: int = 0, seed: int = 0) -> np.ndarray:
    """배경 잡음·옷 색·위치를 조금씩 바꿔 BatchNorm 통계가 한쪽으로 쏠리지 않게 한다."""
    rng = np.random.default_rng(seed)
    image = rng.integers(150, 256, size=(IMG_H, IMG_W, 3), dtype=np.uint8)
    top, bottom = shifted(TOP_BOX, dx, dy), shifted(BOTTOM_BOX, dx, dy)
    top_color = tuple(int(v) for v in rng.integers(0, 120, 3)) if seed else (40, 40, 200)
    bottom_color = tuple(int(v) for v in rng.integers(0, 120, 3)) if seed else (180, 90, 30)
    cv2.rectangle(image, bottom[:2], bottom[2:], bottom_color, -1)
    cv2.rectangle(image, top[:2], top[2:], top_color, -1)
    return image


def write_fake_dataset(root: Path, count: int) -> Path:
    """원천데이터/라벨링데이터로 나뉜 AI Hub 스타일 폴더를 만든다."""
    for i in range(count):
        name = f"{1000 + i}.jpg"
        img_dir = root / "원천데이터" / "스트리트"
        lbl_dir = root / "라벨링데이터" / "스트리트"
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)
        dx, dy = (i * 7) % 21 - 10, (i * 5) % 11 - 5
        cv2.imwrite(str(img_dir / name), make_image(dx, dy, seed=i))
        label = make_label(name, dx, dy)
        (lbl_dir / f"{1000 + i}.json").write_text(json.dumps(label, ensure_ascii=False), encoding="utf-8")
    return root


@pytest.fixture
def fake_dataset(tmp_path: Path) -> Path:
    return write_fake_dataset(tmp_path / "kfashion", count=4)
