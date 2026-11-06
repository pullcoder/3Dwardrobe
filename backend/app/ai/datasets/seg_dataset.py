"""K-Fashion 샘플 → PyTorch 학습용 Dataset."""

from __future__ import annotations

import random

import cv2
import numpy as np
import torch
from torch.utils.data import Dataset

from app.ai.datasets.kfashion import KFashionSample, load_sample_mask

# torchvision 사전학습 백본(ImageNet) 정규화 값
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
BRIGHTNESS_JITTER = 0.2
SCALE_JITTER = (0.8, 1.0)


def to_tensor(image_rgb: np.ndarray) -> torch.Tensor:
    """(H, W, 3) uint8 → (3, H, W) 정규화 float 텐서."""
    x = image_rgb.astype(np.float32) / 255.0
    x = (x - IMAGENET_MEAN) / IMAGENET_STD
    return torch.from_numpy(x.transpose(2, 0, 1).copy())


def letterbox(image: np.ndarray, size: int, interpolation: int, pad_value: int = 0) -> np.ndarray:
    """비율을 지키며 size×size 정사각형에 맞추고 남는 곳은 채운다 (전신 사진은 세로로 길다)."""
    h, w = image.shape[:2]
    scale = size / max(h, w)
    new_h, new_w = max(1, round(h * scale)), max(1, round(w * scale))
    resized = cv2.resize(image, (new_w, new_h), interpolation=interpolation)
    canvas_shape = (size, size) + image.shape[2:]
    canvas = np.full(canvas_shape, pad_value, dtype=image.dtype)
    top, left = (size - new_h) // 2, (size - new_w) // 2
    canvas[top : top + new_h, left : left + new_w] = resized
    return canvas


class KFashionSegDataset(Dataset):
    """이미지와 마스크를 같은 방식으로 리사이즈·증강해서 돌려준다."""

    def __init__(self, samples: list[KFashionSample], image_size: int, augment: bool) -> None:
        self.samples = samples
        self.image_size = image_size
        self.augment = augment

    def __len__(self) -> int:
        return len(self.samples)

    def _augment(self, image: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        if random.random() < 0.5:
            image, mask = image[:, ::-1], mask[:, ::-1]
        # 무작위 크롭: 옷이 화면에서 차지하는 크기가 사진마다 달라서 스케일 변화를 준다.
        h, w = mask.shape
        scale = random.uniform(*SCALE_JITTER)
        ch, cw = int(h * scale), int(w * scale)
        top, left = random.randint(0, h - ch), random.randint(0, w - cw)
        image = image[top : top + ch, left : left + cw]
        mask = mask[top : top + ch, left : left + cw]
        factor = 1.0 + random.uniform(-BRIGHTNESS_JITTER, BRIGHTNESS_JITTER)
        image = np.clip(image.astype(np.float32) * factor, 0, 255).astype(np.uint8)
        return np.ascontiguousarray(image), np.ascontiguousarray(mask)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        image, mask = load_sample_mask(self.samples[index])
        if self.augment:
            image, mask = self._augment(image, mask)
        image = letterbox(image, self.image_size, cv2.INTER_LINEAR)
        mask = letterbox(mask, self.image_size, cv2.INTER_NEAREST)
        return to_tensor(image), torch.from_numpy(mask.astype(np.int64))
