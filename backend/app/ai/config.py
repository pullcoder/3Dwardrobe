"""AI 모듈 공통 설정 (경로·클래스 정의).

FastAPI 설정 모듈(app/core/config.py)이 생기면 그쪽으로 옮긴다. 지금은 학습 스크립트가
백엔드 앱 없이도 돌아가야 해서 환경변수만 읽는다.
"""

from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]

# 가중치 폴더 이름(backend/models/weights → backend/weights)은 아직 미결정이라
# 경로를 한 곳(AI_WEIGHTS_DIR)에서만 읽는다. 이름이 바뀌면 .env 값만 고치면 된다.
DEFAULT_WEIGHTS_DIR = BACKEND_DIR / "models" / "weights"


def weights_dir() -> Path:
    """모델 가중치 루트 폴더. 상대경로면 backend/ 기준으로 해석한다."""
    raw = os.getenv("AI_WEIGHTS_DIR")
    if not raw:
        return DEFAULT_WEIGHTS_DIR
    path = Path(raw)
    return path if path.is_absolute() else BACKEND_DIR / path


def default_cloth_seg_checkpoint() -> Path:
    """의류 세그멘테이션 체크포인트 기본 위치."""
    return weights_dir() / "cloth_seg" / "kfashion_deeplabv3_mbv3.pth"


# 세그멘테이션 클래스. 인덱스 0은 배경.
# K-Fashion 라벨의 부위 이름 → 코드의 slot 이름 (docs/CONVENTIONS.md 도메인 용어).
KFASHION_PART_TO_SLOT: dict[str, str] = {
    "상의": "top",
    "하의": "bottom",
    "아우터": "outer",
    "원피스": "onepiece",
}
# LabelMe 형식 라벨(shapes/label/points) → slot. AI Hub '의류 가상착용 3D 이미지(업사이클링)'(dataSetSn=71940)가
# 이 형식이다. 페이지 샘플에서 확인된 이름은 "upper body", "dress"뿐이라 나머지는 흔한 이름을 추정해 넣었다.
# 실제 데이터의 라벨 이름은 scripts/check_kfashion.py 가 '모르는 라벨'로 보여 주니 보고 고치거나 --label-map으로 덮어쓴다.
LABELME_LABEL_TO_SLOT: dict[str, str] = {
    "upper body": "top",
    "upper_body": "top",
    "top": "top",
    "상의": "top",
    "lower body": "bottom",
    "lower_body": "bottom",
    "bottom": "bottom",
    "pants": "bottom",
    "skirt": "bottom",
    "하의": "bottom",
    "outer": "outer",
    "outerwear": "outer",
    "아우터": "outer",
    "dress": "onepiece",
    "onepiece": "onepiece",
    "one piece": "onepiece",
    "원피스": "onepiece",
}
SEG_CLASSES: list[str] = ["background", "top", "bottom", "outer", "onepiece"]
SLOT_TO_CLASS_ID: dict[str, int] = {name: idx for idx, name in enumerate(SEG_CLASSES)}

# 마스크를 그리는 순서. 겹치는 부분은 나중에 그린 부위가 이긴다.
# 아우터가 상의·원피스 위에 걸쳐 입혀지므로 마지막에 그린다.
MASK_PAINT_ORDER: list[str] = ["bottom", "top", "onepiece", "outer"]
