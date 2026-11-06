import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torchvision")

import numpy as np

from app.ai.datasets.kfashion import scan_dataset
from app.ai.datasets.seg_dataset import KFashionSegDataset
from app.ai.segmentation import ClothSegmenter, build_model, save_checkpoint, unletterbox


def test_unletterbox_restores_shape():
    square = np.zeros((64, 64), dtype=np.uint8)
    assert unletterbox(square, 300, 200).shape == (300, 200)


def test_dataset_and_checkpoint_roundtrip(fake_dataset, tmp_path):
    samples, _ = scan_dataset(fake_dataset)
    ds = KFashionSegDataset(samples, image_size=64, augment=True)
    x, y = ds[0]
    assert x.shape == (3, 64, 64) and y.shape == (64, 64)
    model = build_model(pretrained_backbone=False)
    ckpt = tmp_path / "seg.pth"
    save_checkpoint(model, ckpt, image_size=64, metrics={})
    pred = ClothSegmenter(ckpt, device="cpu").predict(np.zeros((90, 60, 3), dtype=np.uint8))
    assert pred.shape == (90, 60)
