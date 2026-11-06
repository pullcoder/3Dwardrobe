"""세그멘테이션 마스크 → 부위별 누끼(RGBA) + OpenCV 경계 보정. torch 없이 동작한다."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

# 전체 이미지 대비 이 비율보다 작은 부위는 오검출로 보고 버린다.
MIN_SLOT_AREA_RATIO = 0.01
# 경계 보정: 작은 구멍·잡티 제거용 커널과, 가장자리를 부드럽게 하는 페더 폭(px)
MORPH_KERNEL_PX = 5
FEATHER_PX = 3


@dataclass
class SlotCutout:
    """부위 하나의 누끼 결과."""

    slot: str
    mask: np.ndarray  # (H, W) uint8 0/255, 원본 크기
    rgba: np.ndarray  # (h, w, 4) uint8, bbox로 자른 누끼
    bbox: tuple[int, int, int, int]  # x, y, w, h (원본 좌표)
    area_ratio: float


def refine_mask(binary: np.ndarray) -> np.ndarray:
    """0/1 마스크 → 잡티·구멍을 정리한 0/255 마스크. 가장 큰 덩어리와 그에 붙은 큰 조각만 남긴다."""
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (MORPH_KERNEL_PX, MORPH_KERNEL_PX))
    mask = (binary > 0).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if count <= 1:
        return mask
    areas = stats[1:, cv2.CC_STAT_AREA]
    # 바지 양쪽 다리처럼 떨어진 조각이 있어 '가장 큰 것만'이 아니라 '가장 큰 것의 10% 이상'을 남긴다.
    keep = [i + 1 for i, a in enumerate(areas) if a >= 0.1 * areas.max()]
    mask = np.isin(labels, keep).astype(np.uint8) * 255
    # 내부 구멍(단추 반사 등) 채우기
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    filled = np.zeros_like(mask)
    cv2.drawContours(filled, contours, -1, 255, thickness=cv2.FILLED)
    return filled


def make_cutout(image_rgb: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    """마스크(0/255)로 RGBA 누끼를 만들고 bbox로 자른다. 가장자리는 페더 처리."""
    alpha = cv2.GaussianBlur(mask, (0, 0), sigmaX=FEATHER_PX / 2) if FEATHER_PX else mask
    alpha = np.minimum(alpha, cv2.dilate(mask, np.ones((3, 3), np.uint8)))
    rgba = np.dstack([image_rgb, alpha])
    x, y, w, h = cv2.boundingRect(mask)
    return rgba[y : y + h, x : x + w].copy(), (x, y, w, h)


def extract_cutouts(image_rgb: np.ndarray, class_mask: np.ndarray, classes: list[str]) -> list[SlotCutout]:
    """클래스 마스크 → 부위별 누끼 목록 (작은 오검출 제외)."""
    total = class_mask.size
    results: list[SlotCutout] = []
    for class_id, slot in enumerate(classes):
        if class_id == 0:
            continue
        raw = class_mask == class_id
        if raw.sum() / total < MIN_SLOT_AREA_RATIO:
            continue
        mask = refine_mask(raw)
        area_ratio = float((mask > 0).sum() / total)
        if area_ratio < MIN_SLOT_AREA_RATIO:
            continue
        rgba, bbox = make_cutout(image_rgb, mask)
        results.append(SlotCutout(slot, mask, rgba, bbox, area_ratio))
    return results
