"""K-Fashion '원천데이터'와 '라벨링데이터'를 한 폴더로 합치고, 파일 이름에 특징(스타일·카테고리·색상)을 붙인다.

원본은 그대로 두고 복사만 한다. 이미지와 라벨 JSON은 같은 이름(확장자만 다름)으로 저장되므로
학습 스크립트가 그대로 짝을 찾는다. 이름 맨 앞에는 항상 원래 ID를 둬서 원본과 다시 대조할 수 있다.

사용 예 (backend/ 폴더에서):
    python -m scripts.organize_kfashion --data-dir "C:/Temp/3Dwardrobe/2D/New_sample" --out-dir "C:/Temp/kfashion_merged"
    # 먼저 이름만 확인
    python -m scripts.organize_kfashion --data-dir ... --out-dir ... --dry-run

결과: <out-dir>/<스타일>/<ID>_<스타일>_<부위별 카테고리-색상>.jpg/.json + <out-dir>/index.csv (엑셀에서 열림)
예:   1016530_레트로_상의-탑-화이트_하의-청바지-스카이블루.jpg
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
from pathlib import Path

from app.ai.config import MASK_PAINT_ORDER
from app.ai.datasets.kfashion import KFashionSample, scan_dataset

SLOT_LABELS = {"top": "상의", "bottom": "하의", "outer": "아우터", "onepiece": "원피스"}
# 이름에 넣는 부위 순서 (겉 → 속이 아니라 위 → 아래로 읽히게)
NAME_SLOT_ORDER = ["outer", "top", "onepiece", "bottom"]
_UNSAFE_CHARS = re.compile(r'[\\/:*?"<>|\s]+')  # Windows 파일 이름에 못 쓰는 문자 + 공백
MAX_NAME_LEN = 150  # Windows 경로 길이(260자) 여유


def safe(text: str) -> str:
    return _UNSAFE_CHARS.sub("", str(text)).strip("._-") or "없음"


def describe(sample: KFashionSample) -> str:
    parts = []
    for slot in NAME_SLOT_ORDER:
        if slot not in sample.polygons:
            continue
        attrs = sample.attributes.get(slot, {})
        bits = [SLOT_LABELS[slot], attrs.get("카테고리"), attrs.get("색상")]
        parts.append("-".join(safe(b) for b in bits if b))
    return "_".join(parts)


def new_stem(sample: KFashionSample) -> str:
    style = safe(sample.styles[0]) if sample.styles else "스타일없음"
    stem = f"{sample.label_path.stem}_{style}_{describe(sample)}"
    return stem[:MAX_NAME_LEN].rstrip("_-")


def csv_row(sample: KFashionSample, rel_image: str) -> dict[str, str]:
    row = {"id": sample.label_path.stem, "file": rel_image, "style": "|".join(sample.styles)}
    for slot in MASK_PAINT_ORDER:
        attrs = sample.attributes.get(slot, {})
        row[f"{slot}_category"] = str(attrs.get("카테고리", ""))
        row[f"{slot}_color"] = str(attrs.get("색상", ""))
    return row


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-dir", type=Path, required=True)
    p.add_argument("--labels-dir", type=Path, default=None)
    p.add_argument("--out-dir", type=Path, required=True, help="원본과 다른 폴더여야 한다")
    p.add_argument("--dry-run", action="store_true", help="복사하지 않고 바뀔 이름 10개만 출력")
    args = p.parse_args()

    if args.out_dir.resolve().is_relative_to(args.data_dir.resolve()):
        raise SystemExit("--out-dir는 --data-dir 밖에 두세요 (다시 스캔할 때 중복으로 잡힘).")
    samples, skipped = scan_dataset(args.data_dir, args.labels_dir)
    print(f"정리할 샘플 {len(samples)}개, 건너뜀 {len(skipped)}개")
    rows = []
    for i, sample in enumerate(samples):
        style_dir = safe(sample.styles[0]) if sample.styles else "스타일없음"
        stem = new_stem(sample)
        image_dst = args.out_dir / style_dir / f"{stem}{sample.image_path.suffix.lower()}"
        if args.dry_run:
            if i < 10:
                print(f"  {sample.image_path.name} → {style_dir}/{image_dst.name}")
            continue
        image_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(sample.image_path, image_dst)
        shutil.copy2(sample.label_path, image_dst.with_suffix(".json"))
        rows.append(csv_row(sample, f"{style_dir}/{image_dst.name}"))
    if rows:
        with (args.out_dir / "index.csv").open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print(f"복사 완료 → {args.out_dir} (index.csv 포함)")


if __name__ == "__main__":
    main()
