import numpy as np

from app.ai.config import SLOT_TO_CLASS_ID
from app.ai.datasets.kfashion import load_sample_mask, parse_polygon, parse_polygons, scan_dataset
from tests.conftest import BOTTOM_BOX, TOP_BOX, make_label


def test_parse_polygon_formats():
    assert parse_polygon({"X좌표1": 0, "Y좌표1": 0, "X좌표2": 10, "Y좌표2": 0, "X좌표3": 10, "Y좌표3": 10}).shape == (
        3,
        2,
    )
    assert parse_polygon([[0, 0], [1, 0], [1, 1]]).shape == (3, 2)
    assert parse_polygon([0, 0, 1, 0, 1, 1]).shape == (3, 2)
    assert parse_polygon({}) is None
    assert parse_polygon({"X좌표1": 0, "Y좌표1": 0}) is None


def test_parse_polygons_skips_empty_parts():
    polygons = parse_polygons(make_label("a.jpg"))
    assert set(polygons) == {"top", "bottom"}


def test_scan_and_mask(fake_dataset):
    samples, skipped = scan_dataset(fake_dataset)
    assert len(samples) == 4 and not skipped
    assert samples[0].attributes["top"]["카테고리"] == "티셔츠"
    assert samples[0].styles == ["스트리트"]
    _, mask = load_sample_mask(samples[0])
    x1, y1, x2, y2 = TOP_BOX
    assert mask[(y1 + y2) // 2 - 20, (x1 + x2) // 2] == SLOT_TO_CLASS_ID["top"]
    bx1, by1, bx2, by2 = BOTTOM_BOX
    assert mask[(by1 + by2) // 2, (bx1 + bx2) // 2] == SLOT_TO_CLASS_ID["bottom"]
    assert mask[5, 5] == 0
    assert set(np.unique(mask)) == {0, 1, 2}


def test_labelme_format(tmp_path):
    import json

    import cv2

    cv2.imwrite(str(tmp_path / "p1.jpg"), np.zeros((100, 80, 3), dtype=np.uint8))
    label = {
        "version": "4.0.0",
        "imagePath": "p1.jpg",
        "imageHeight": 100,
        "imageWidth": 80,
        "shapes": [
            {"label": "upper body", "shape_type": "polygon", "points": [[10, 10], [70, 10], [70, 50], [10, 50]]},
            {"label": "Dress", "shape_type": "rectangle", "points": [[20, 55], [60, 95]]},
            {"label": "face", "shape_type": "polygon", "points": [[0, 0], [5, 0], [5, 5]]},
        ],
    }
    (tmp_path / "p1.json").write_text(json.dumps(label), encoding="utf-8")
    samples, skipped = scan_dataset(tmp_path)
    assert not skipped
    assert set(samples[0].polygons) == {"top", "onepiece"}
    assert samples[0].ignored_labels == {"face"}
    _, mask = load_sample_mask(samples[0])
    assert mask[30, 40] == SLOT_TO_CLASS_ID["top"] and mask[75, 40] == SLOT_TO_CLASS_ID["onepiece"]

    samples, skipped = scan_dataset(tmp_path, label_map={"face": "top"})
    assert set(samples[0].polygons) == {"top"}
