"""의류 부위 세그멘테이션 모델 (학습·추론). 누끼·경계 보정은 cutout.py.

모델: torchvision DeepLabV3-MobileNetV3-Large (BSD-3, CPU에서도 1장 1초 안팎)를
K-Fashion 폴리곤으로 미세조정해 배경/상의/하의/아우터/원피스 5클래스를 나눈다.
RMBG/SAM 같은 범용 배경 제거는 '사람+옷 전체'를 떼어 낼 뿐 부위를 나누지 못해서,
옷장 등록용 부위별 누끼는 이 모델로 하고 RMBG/SAM은 경계 보정 단계에 선택적으로 붙인다.

AI 모듈은 Celery 워커에서만 부른다. ClothSegmenter는 워커 시작 시 1회 만든다.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import torch
from torch import nn
from torchvision.models import MobileNet_V3_Large_Weights
from torchvision.models.segmentation import deeplabv3_mobilenet_v3_large

from app.ai.config import SEG_CLASSES, default_cloth_seg_checkpoint
from app.ai.datasets.seg_dataset import letterbox, to_tensor

DEFAULT_IMAGE_SIZE = 512


def build_model(num_classes: int = len(SEG_CLASSES), pretrained_backbone: bool = True) -> nn.Module:
    """세그멘테이션 모델을 만든다. pretrained_backbone=True면 ImageNet 백본 가중치를 내려받는다."""
    weights_backbone = MobileNet_V3_Large_Weights.IMAGENET1K_V1 if pretrained_backbone else None
    return deeplabv3_mobilenet_v3_large(
        weights=None, weights_backbone=weights_backbone, num_classes=num_classes, aux_loss=False
    )


def save_checkpoint(model: nn.Module, path: Path, image_size: int, metrics: dict[str, float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "classes": SEG_CLASSES,
            "image_size": image_size,
            "arch": "deeplabv3_mobilenet_v3_large",
            "metrics": metrics,
        },
        path,
    )


class ClothSegmenter:
    """학습된 체크포인트로 의류 부위 마스크를 예측한다."""

    def __init__(self, checkpoint: Path | None = None, device: str | None = None) -> None:
        checkpoint = checkpoint or default_cloth_seg_checkpoint()
        if not checkpoint.exists():
            raise FileNotFoundError(
                f"체크포인트가 없습니다: {checkpoint}\n"
                "scripts/train_cloth_seg.py 로 먼저 학습하거나 AI_WEIGHTS_DIR을 확인하세요."
            )
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        state = torch.load(checkpoint, map_location=self.device, weights_only=False)
        self.classes: list[str] = state["classes"]
        self.image_size: int = state.get("image_size", DEFAULT_IMAGE_SIZE)
        self.model = build_model(len(self.classes), pretrained_backbone=False)
        self.model.load_state_dict(state["state_dict"])
        self.model.to(self.device).eval()

    @torch.inference_mode()
    def predict(self, image_rgb: np.ndarray) -> np.ndarray:
        """(H, W, 3) RGB → (H, W) 클래스 마스크."""
        h, w = image_rgb.shape[:2]
        x = to_tensor(letterbox(image_rgb, self.image_size, cv2.INTER_LINEAR)).unsqueeze(0)
        logits = self.model(x.to(self.device))["out"][0]
        pred = logits.argmax(0).byte().cpu().numpy()
        return unletterbox(pred, h, w)


def unletterbox(square: np.ndarray, height: int, width: int) -> np.ndarray:
    """letterbox()의 역변환: 패딩을 잘라내고 원래 크기로 되돌린다."""
    size = square.shape[0]
    scale = size / max(height, width)
    new_h, new_w = max(1, round(height * scale)), max(1, round(width * scale))
    top, left = (size - new_h) // 2, (size - new_w) // 2
    crop = square[top : top + new_h, left : left + new_w]
    return cv2.resize(crop, (width, height), interpolation=cv2.INTER_NEAREST)
