"""AI Hub 의류 데이터 라벨 읽기 + 의류 마스크 생성.

- 'K-Fashion 이미지'(dataSetSn=51): 부위별 '폴리곤좌표' 형식
- '의류 가상착용 3D 이미지(업사이클링)'(dataSetSn=71940): LabelMe 형식(shapes/label/points)

데이터는 AI Hub 로그인·승인 후 사용자가 직접 내려받는다 (크롤링 금지, AGENTS.md 규칙 4).
분할 압축(*.zip.part*)은 `cat a.zip.part* > a.zip` 으로 합친 뒤 풀어서 한 폴더에 둔다.

라벨 JSON(부위별 '렉트좌표'·'폴리곤좌표'·'라벨링')은 샘플/원본, 버전마다 키 이름과 중첩이 조금씩
달라서, 키 위치를 고정하지 않고 재귀로 찾는다. 폴리곤은 {"X좌표1": .., "Y좌표1": .., "X좌표2": ..}
형태를 기본으로, [[x, y], ...] / [x1, y1, x2, y2, ...] 형태도 받는다.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.ai.config import KFASHION_PART_TO_SLOT, LABELME_LABEL_TO_SLOT, MASK_PAINT_ORDER, SLOT_TO_CLASS_ID

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
POLYGON_KEY = "폴리곤좌표"
LABEL_KEY = "라벨링"
STYLE_KEY = "스타일"
IMAGE_FILENAME_KEYS = ("이미지 파일명", "파일이름", "파일 이름", "file_name", "imagePath")
MIN_POLYGON_POINTS = 3
_COORD_KEY_RE = re.compile(r"^([XxYy])\s*좌표\s*(\d+)$")


@dataclass
class KFashionSample:
    """이미지 1장 + 라벨 1개."""

    image_path: Path
    label_path: Path
    polygons: dict[str, list[np.ndarray]] = field(default_factory=dict)  # slot → (N, 2) float32 목록
    attributes: dict[str, dict[str, Any]] = field(default_factory=dict)  # slot → 카테고리·색상 등
    styles: list[str] = field(default_factory=list)
    ignored_labels: set[str] = field(default_factory=set)  # LabelMe에서 slot으로 못 바꾼 라벨 이름


def load_json(path: Path) -> dict[str, Any]:
    """AI Hub JSON은 UTF-8(BOM 포함)과 CP949가 섞여 있어 순서대로 시도한다."""
    for encoding in ("utf-8-sig", "cp949"):
        try:
            return json.loads(path.read_text(encoding=encoding))
        except UnicodeDecodeError:
            continue
    raise ValueError(f"인코딩을 알 수 없는 JSON: {path}")


def find_key(node: Any, key: str) -> Any | None:
    """중첩 dict/list에서 처음 나오는 key의 값을 찾는다."""
    if isinstance(node, dict):
        if key in node:
            return node[key]
        children = node.values()
    elif isinstance(node, list):
        children = node
    else:
        return None
    for child in children:
        found = find_key(child, key)
        if found is not None:
            return found
    return None


def _points_from_coord_dict(entry: dict[str, Any]) -> np.ndarray | None:
    xs: dict[int, float] = {}
    ys: dict[int, float] = {}
    for key, value in entry.items():
        match = _COORD_KEY_RE.match(str(key).strip())
        if not match or value in (None, ""):
            continue
        axis, idx = match.group(1).upper(), int(match.group(2))
        (xs if axis == "X" else ys)[idx] = float(value)
    indices = sorted(set(xs) & set(ys))
    if len(indices) < MIN_POLYGON_POINTS:
        return None
    return np.array([[xs[i], ys[i]] for i in indices], dtype=np.float32)


def parse_polygon(entry: Any) -> np.ndarray | None:
    """폴리곤 1개를 (N, 2) 배열로. 점이 3개 미만이면 None."""
    if isinstance(entry, dict):
        return _points_from_coord_dict(entry)
    if isinstance(entry, list) and entry:
        if all(isinstance(p, (list, tuple)) and len(p) >= 2 for p in entry):
            points = np.array([[float(p[0]), float(p[1])] for p in entry], dtype=np.float32)
        elif all(isinstance(v, (int, float)) for v in entry) and len(entry) % 2 == 0:
            points = np.array(entry, dtype=np.float32).reshape(-1, 2)
        else:
            return None
        return points if len(points) >= MIN_POLYGON_POINTS else None
    return None


def parse_polygons(label: dict[str, Any]) -> dict[str, list[np.ndarray]]:
    """'폴리곤좌표' → {slot: [폴리곤, ...]}. 빈 부위({})는 건너뛴다."""
    section = find_key(label, POLYGON_KEY) or {}
    result: dict[str, list[np.ndarray]] = {}
    for part, slot in KFASHION_PART_TO_SLOT.items():
        entries = section.get(part) or []
        if isinstance(entries, dict):
            entries = [entries]
        polygons = [p for p in (parse_polygon(e) for e in entries) if p is not None]
        if polygons:
            result[slot] = polygons
    return result


def normalize_label(name: str) -> str:
    return " ".join(str(name).strip().lower().replace("-", " ").split())


def parse_labelme_polygons(
    label: dict[str, Any], label_map: dict[str, str] | None = None
) -> tuple[dict[str, list[np.ndarray]], set[str]]:
    """LabelMe 'shapes' → ({slot: [폴리곤]}, 모르는 라벨 이름들). polygon/rectangle만 쓴다."""
    mapping = {normalize_label(k): v for k, v in (label_map or LABELME_LABEL_TO_SLOT).items()}
    result: dict[str, list[np.ndarray]] = {}
    unknown: set[str] = set()
    for shape in label.get("shapes") or []:
        name = str(shape.get("label", ""))
        slot = mapping.get(normalize_label(name))
        if slot is None:
            unknown.add(name)
            continue
        points = parse_polygon(shape.get("points") or [])
        if shape.get("shape_type") == "rectangle" and points is None:
            pts = shape.get("points") or []
            if len(pts) == 2:
                (x1, y1), (x2, y2) = pts
                points = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.float32)
        if points is not None:
            result.setdefault(slot, []).append(points)
    return result, unknown


def parse_attributes(label: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """'라벨링' → 부위별 속성(카테고리·색상·소재…)과 스타일 목록. VLM 태깅 정답으로 쓸 수 있다."""
    section = find_key(label, LABEL_KEY) or {}
    attributes: dict[str, dict[str, Any]] = {}
    for part, slot in KFASHION_PART_TO_SLOT.items():
        entries = section.get(part) or []
        first = entries[0] if isinstance(entries, list) and entries else entries
        if isinstance(first, dict) and first:
            attributes[slot] = first
    styles: list[str] = []
    for entry in section.get(STYLE_KEY) or []:
        if isinstance(entry, dict):
            styles.extend(str(v) for v in entry.values() if v)
    return attributes, styles


def image_filename_from_label(label: dict[str, Any]) -> str | None:
    for key in IMAGE_FILENAME_KEYS:
        value = find_key(label, key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def rasterize_mask(polygons: dict[str, list[np.ndarray]], height: int, width: int) -> np.ndarray:
    """slot별 폴리곤 → (H, W) uint8 클래스 마스크 (0=배경)."""
    mask = np.zeros((height, width), dtype=np.uint8)
    for slot in MASK_PAINT_ORDER:
        for polygon in polygons.get(slot, []):
            pts = np.round(polygon).astype(np.int32).reshape(-1, 1, 2)
            cv2.fillPoly(mask, [pts], color=SLOT_TO_CLASS_ID[slot])
    return mask


def _index_images(data_dir: Path) -> dict[str, Path]:
    """파일 이름(소문자) → 경로, 확장자 없는 이름 → 경로 둘 다 등록."""
    index: dict[str, Path] = {}
    for path in data_dir.rglob("*"):
        if path.suffix.lower() in IMAGE_EXTENSIONS and path.is_file():
            index.setdefault(path.name.lower(), path)
            index.setdefault(path.stem.lower(), path)
    return index


def scan_dataset(
    data_dir: Path, labels_dir: Path | None = None, label_map: dict[str, str] | None = None
) -> tuple[list[KFashionSample], list[str]]:
    """폴더를 훑어 (이미지, 라벨) 쌍을 만든다.

    이미지와 JSON이 같은 폴더든 '원천데이터/라벨링데이터'로 나뉘어 있든 상관없이,
    JSON의 이미지 파일명(없으면 JSON 파일 이름)으로 이미지를 찾는다.
    K-Fashion 형식이 아니면 LabelMe 형식으로 읽는다 (label_map: 라벨 이름 → slot).
    반환: (폴리곤이 하나라도 있는 샘플 목록, 건너뛴 이유 목록)
    """
    labels_dir = labels_dir or data_dir
    images = _index_images(data_dir)
    samples: list[KFashionSample] = []
    skipped: list[str] = []
    for label_path in sorted(labels_dir.rglob("*.json")):
        try:
            label = load_json(label_path)
        except (ValueError, json.JSONDecodeError) as exc:
            skipped.append(f"{label_path.name}: JSON 읽기 실패 ({exc})")
            continue
        name = image_filename_from_label(label) or label_path.stem
        image_path = images.get(Path(name).name.lower()) or images.get(Path(name).stem.lower())
        image_path = image_path or images.get(label_path.stem.lower())
        if image_path is None:
            skipped.append(f"{label_path.name}: 이미지 없음 ({name})")
            continue
        polygons, unknown = parse_polygons(label), set()
        if not polygons and "shapes" in label:
            polygons, unknown = parse_labelme_polygons(label, label_map)
        if not polygons:
            extra = f" (모르는 라벨: {', '.join(sorted(unknown))})" if unknown else ""
            skipped.append(f"{label_path.name}: 폴리곤 없음{extra}")
            continue
        attributes, styles = parse_attributes(label)
        samples.append(KFashionSample(image_path, label_path, polygons, attributes, styles, unknown))
    return samples, skipped


def load_label_map(path: Path | None) -> dict[str, str] | None:
    """--label-map JSON ({"라벨 이름": "top|bottom|outer|onepiece"}) 읽기."""
    if path is None:
        return None
    mapping = load_json(path)
    bad = {k: v for k, v in mapping.items() if v not in SLOT_TO_CLASS_ID or v == "background"}
    if bad:
        raise ValueError(f"slot은 top/bottom/outer/onepiece 중 하나여야 합니다: {bad}")
    return mapping


def read_image_rgb(path: Path) -> np.ndarray:
    """한글 경로에서도 읽히게 imdecode를 쓴다 (cv2.imread는 Windows 한글 경로 실패)."""
    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"이미지를 읽을 수 없음: {path}")
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def load_sample_mask(sample: KFashionSample) -> tuple[np.ndarray, np.ndarray]:
    """샘플 → (RGB 이미지, 클래스 마스크)."""
    image = read_image_rgb(sample.image_path)
    mask = rasterize_mask(sample.polygons, image.shape[0], image.shape[1])
    return image, mask
