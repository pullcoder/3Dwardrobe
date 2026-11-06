"""옷 사진 → 부위별 누끼(PNG) → 3D 메시(.glb/.obj).

사용 예 (backend/ 폴더에서):
    # 학습한 모델로 (폴더를 주면 안의 이미지를 전부 처리)
    python -m scripts.run_garment_pipeline --image samples/look01.jpg --out-dir out/

    # 모델 없이 K-Fashion 정답 폴리곤으로 누끼·3D 변환만 확인
    python -m scripts.run_garment_pipeline --image a.jpg --label a.json --out-dir out/

결과: out/<이미지이름>/{slot}_cutout.png, {slot}.glb, {slot}.obj(+.mtl/.png), overlay.jpg, result.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from app.ai.config import SEG_CLASSES
from app.ai.cutout import extract_cutouts
from app.ai.datasets.kfashion import IMAGE_EXTENSIONS, load_json, parse_polygons, rasterize_mask, read_image_rgb
from app.ai.garment_asset import DEFAULT_DEPTH_RATIO, DEFAULT_GRID_MAX, build_garment_mesh, write_glb, write_obj

# 오버레이 색 (RGB): 배경, 상의, 하의, 아우터, 원피스
OVERLAY_COLORS = np.array([[0, 0, 0], [230, 80, 80], [80, 120, 230], [80, 200, 120], [220, 170, 60]], dtype=np.uint8)
OVERLAY_ALPHA = 0.45


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--image", type=Path, required=True, help="이미지 파일 또는 폴더")
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--checkpoint", type=Path, default=None, help="기본: AI_WEIGHTS_DIR/cloth_seg/…")
    p.add_argument("--label", type=Path, default=None, help="K-Fashion 라벨 JSON (주면 모델 대신 정답 폴리곤 사용)")
    p.add_argument("--height-m", type=float, default=None, help="옷 실제 길이(m). 없으면 높이 1로 정규화")
    p.add_argument("--grid-max", type=int, default=DEFAULT_GRID_MAX)
    p.add_argument("--depth-ratio", type=float, default=DEFAULT_DEPTH_RATIO)
    p.add_argument("--no-obj", action="store_true", help=".glb만 저장")
    p.add_argument("--device", default=None)
    return p.parse_args()


def list_images(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(p for p in path.rglob("*") if p.suffix.lower() in IMAGE_EXTENSIONS)


def save_png(path: Path, rgba_or_rgb: np.ndarray) -> None:
    """한글 경로에서도 저장되게 imencode + tofile."""
    code = cv2.COLOR_RGBA2BGRA if rgba_or_rgb.shape[2] == 4 else cv2.COLOR_RGB2BGR
    ok, buf = cv2.imencode(path.suffix, cv2.cvtColor(rgba_or_rgb, code))
    if not ok:
        raise ValueError(f"저장 실패: {path}")
    buf.tofile(str(path))


def overlay(image_rgb: np.ndarray, class_mask: np.ndarray) -> np.ndarray:
    color = OVERLAY_COLORS[np.clip(class_mask, 0, len(OVERLAY_COLORS) - 1)]
    blended = image_rgb.astype(np.float32) * (1 - OVERLAY_ALPHA) + color * OVERLAY_ALPHA
    return np.where(class_mask[..., None] > 0, blended, image_rgb).astype(np.uint8)


def process_image(image_path: Path, class_mask_fn, args: argparse.Namespace) -> dict:
    image = read_image_rgb(image_path)
    class_mask = class_mask_fn(image)
    out_dir = args.out_dir / image_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    save_png(out_dir / "overlay.jpg", overlay(image, class_mask))
    items = []
    for cut in extract_cutouts(image, class_mask, SEG_CLASSES):
        save_png(out_dir / f"{cut.slot}_cutout.png", cut.rgba)
        mesh = build_garment_mesh(cut.rgba, args.grid_max, args.depth_ratio, height_m=args.height_m)
        write_glb(mesh, out_dir / f"{cut.slot}.glb")
        if not args.no_obj:
            write_obj(mesh, out_dir / f"{cut.slot}.obj")
        items.append(
            {
                "slot": cut.slot,
                "bbox": list(cut.bbox),
                "area_ratio": round(cut.area_ratio, 4),
                "cutout": f"{cut.slot}_cutout.png",
                "mesh": f"{cut.slot}.glb",
                "vertices": len(mesh.positions),
                "faces": len(mesh.faces),
            }
        )
    result = {"image": image_path.name, "items": items}
    (out_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def make_mask_fn(args: argparse.Namespace):
    if args.label:
        polygons = parse_polygons(load_json(args.label))
        return lambda image: rasterize_mask(polygons, image.shape[0], image.shape[1])
    from app.ai.segmentation import ClothSegmenter

    segmenter = ClothSegmenter(args.checkpoint, args.device)
    return segmenter.predict


def main() -> None:
    args = parse_args()
    images = list_images(args.image)
    if not images:
        raise SystemExit(f"이미지가 없습니다: {args.image}")
    if args.label and len(images) > 1:
        raise SystemExit("--label은 이미지 1장과 함께만 쓸 수 있습니다.")
    mask_fn = make_mask_fn(args)
    for path in images:
        result = process_image(path, mask_fn, args)
        slots = ", ".join(i["slot"] for i in result["items"]) or "검출 없음"
        print(f"{path.name}: {slots}")


if __name__ == "__main__":
    main()
