"""K-Fashion 경량(샘플) 데이터로 의류 세그멘테이션 모델을 학습한다.

사용 예 (backend/ 폴더에서):
    python -m scripts.train_cloth_seg --data-dir "D:/aihub/K-Fashion_sample" --epochs 30

--data-dir: AI Hub에서 내려받아 압축을 푼 폴더. 이미지와 라벨 JSON이 하위 폴더 어디에 있든 찾는다.
            라벨이 따로 있으면 --labels-dir로 지정.
결과: 체크포인트(.pth)와 학습 기록(.json)이 AI_WEIGHTS_DIR/cloth_seg/ 에 저장된다 (git 제외).
"""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader

from app.ai.config import SEG_CLASSES, default_cloth_seg_checkpoint
from app.ai.datasets.kfashion import load_label_map, scan_dataset
from app.ai.datasets.seg_dataset import KFashionSegDataset
from app.ai.segmentation import DEFAULT_IMAGE_SIZE, build_model, save_checkpoint


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument(
        "--data-dir", type=Path, required=True, help="내려받은 AI Hub 데이터 폴더 (K-Fashion 또는 LabelMe 형식)"
    )
    p.add_argument("--labels-dir", type=Path, default=None, help="라벨 JSON 폴더 (기본: --data-dir)")
    p.add_argument("--label-map", type=Path, default=None, help="LabelMe 라벨 이름 → slot JSON (dataSetSn=71940 등)")
    p.add_argument("--out", type=Path, default=None, help="체크포인트 경로 (기본: AI_WEIGHTS_DIR/cloth_seg/…)")
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--image-size", type=int, default=DEFAULT_IMAGE_SIZE)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--val-ratio", type=float, default=0.15)
    p.add_argument("--max-samples", type=int, default=0, help="0이면 전부. 빠른 확인용으로 일부만 쓸 때")
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--no-pretrained", action="store_true", help="ImageNet 백본을 내려받지 않음 (오프라인 테스트용)")
    p.add_argument("--device", default=None, help="cuda | cpu (기본: 자동)")
    return p.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def confusion(pred: torch.Tensor, target: torch.Tensor, num_classes: int) -> torch.Tensor:
    idx = target.flatten() * num_classes + pred.flatten()
    return torch.bincount(idx, minlength=num_classes**2).reshape(num_classes, num_classes)


def iou_from_confusion(cm: torch.Tensor) -> dict[str, float]:
    """클래스별 IoU. 검증셋에 한 번도 안 나온 클래스는 제외(NaN)하고 mIoU를 낸다."""
    cm = cm.double()
    inter = cm.diag()
    union = cm.sum(0) + cm.sum(1) - inter
    ious = {name: (inter[i] / union[i]).item() if union[i] > 0 else float("nan") for i, name in enumerate(SEG_CLASSES)}
    valid = [v for v in ious.values() if not np.isnan(v)]
    ious["mIoU"] = float(np.mean(valid)) if valid else 0.0
    return ious


def run_epoch(model: nn.Module, loader: DataLoader, device: torch.device, optimizer=None) -> tuple[float, dict]:
    """optimizer가 있으면 학습, 없으면 검증."""
    is_train = optimizer is not None
    model.train(is_train)
    criterion = nn.CrossEntropyLoss()
    cm = torch.zeros(len(SEG_CLASSES), len(SEG_CLASSES), dtype=torch.long)
    total_loss, total_n = 0.0, 0
    with torch.set_grad_enabled(is_train):
        for images, masks in loader:
            images, masks = images.to(device), masks.to(device)
            logits = model(images)["out"]
            loss = criterion(logits, masks)
            if is_train:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            total_loss += loss.item() * images.size(0)
            total_n += images.size(0)
            cm += confusion(logits.argmax(1).cpu(), masks.cpu(), len(SEG_CLASSES))
    return total_loss / max(total_n, 1), iou_from_confusion(cm)


BN_RECALIBRATION_BATCHES = 50


@torch.no_grad()
def recalibrate_batchnorm(model: nn.Module, loader: DataLoader, device: torch.device) -> None:
    """BatchNorm 이동평균을 현재 가중치 기준으로 다시 잰다.

    경량 데이터는 학습 step 수가 적어 이동평균(momentum 0.1)이 가중치 변화를 못 따라가고,
    그러면 eval 모드에서 전부 배경으로 찍히는 문제가 생긴다 (가짜 데이터 실험에서 확인).
    """
    for module in model.modules():
        if isinstance(module, nn.modules.batchnorm._BatchNorm):
            module.reset_running_stats()
            module.momentum = None  # 누적 평균
    model.train()
    for i, (images, _) in enumerate(loader):
        if i >= BN_RECALIBRATION_BATCHES:
            break
        model(images.to(device))
    for module in model.modules():
        if isinstance(module, nn.modules.batchnorm._BatchNorm):
            module.momentum = 0.1


def split_samples(samples: list, val_ratio: float, seed: int) -> tuple[list, list]:
    shuffled = samples[:]
    random.Random(seed).shuffle(shuffled)
    n_val = max(1, int(len(shuffled) * val_ratio)) if len(shuffled) > 1 else 0
    return shuffled[n_val:], shuffled[:n_val]


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    samples, skipped = scan_dataset(args.data_dir, args.labels_dir, load_label_map(args.label_map))
    print(f"샘플 {len(samples)}개 사용, {len(skipped)}개 건너뜀")
    for reason in skipped[:10]:
        print("  건너뜀:", reason)
    if not samples:
        raise SystemExit("학습할 샘플이 없습니다. --data-dir 경로와 압축 해제를 확인하세요.")
    if args.max_samples:
        samples = samples[: args.max_samples]
    train_s, val_s = split_samples(samples, args.val_ratio, args.seed)
    print(f"학습 {len(train_s)} / 검증 {len(val_s)}")

    device = torch.device(args.device or ("cuda" if torch.cuda.is_available() else "cpu"))
    loader_kw = {"batch_size": args.batch_size, "num_workers": args.workers}
    train_dl = DataLoader(
        KFashionSegDataset(train_s, args.image_size, augment=True),
        shuffle=True,
        drop_last=len(train_s) > args.batch_size,
        **loader_kw,
    )
    # BN 재측정용: 증강 없이, 배치 1개짜리 마지막 묶음은 버림 (ASPP 풀링 BN이 배치 1에서 실패)
    calib_dl = DataLoader(
        KFashionSegDataset(train_s, args.image_size, augment=False),
        shuffle=True,
        drop_last=len(train_s) > args.batch_size,
        **loader_kw,
    )
    val_dl = DataLoader(KFashionSegDataset(val_s, args.image_size, augment=False), **loader_kw) if val_s else None

    model = build_model(pretrained_backbone=not args.no_pretrained).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    out = args.out or default_cloth_seg_checkpoint()
    best, history = -1.0, []

    for epoch in range(1, args.epochs + 1):
        start = time.time()
        train_loss, _ = run_epoch(model, train_dl, device, optimizer)
        scheduler.step()
        recalibrate_batchnorm(model, calib_dl, device)
        val_loss, ious = run_epoch(model, val_dl, device) if val_dl else (train_loss, {"mIoU": 0.0})
        history.append({"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss, **ious})
        print(
            f"[{epoch}/{args.epochs}] train {train_loss:.4f} | val {val_loss:.4f} | mIoU {ious['mIoU']:.3f} | {time.time() - start:.0f}s"
        )
        if ious["mIoU"] >= best:
            best = ious["mIoU"]
            save_checkpoint(model, out, args.image_size, {k: v for k, v in ious.items() if not np.isnan(v)})
    out.with_suffix(".json").write_text(
        json.dumps(history, ensure_ascii=False, indent=2, default=float), encoding="utf-8"
    )
    print(f"최고 mIoU {best:.3f} → {out}")


if __name__ == "__main__":
    main()
