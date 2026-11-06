"""내려받은 K-Fashion 데이터가 학습에 쓸 수 있는 상태인지 확인한다.

사용 예 (backend/ 폴더에서):
    python -m scripts.check_kfashion --data-dir "D:/aihub/K-Fashion_sample" --preview 5

K-Fashion(dataSetSn=51)과 LabelMe 형식(dataSetSn=71940 등)을 모두 읽는다.
출력: (이미지, 라벨) 쌍 수, 부위별 개수, 건너뛴 이유, 의류로 연결 안 된 라벨 이름. --preview N이면 마스크 미리보기 N장을 저장.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from app.ai.datasets.kfashion import load_label_map, load_sample_mask, scan_dataset
from scripts.run_garment_pipeline import overlay, save_png


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-dir", type=Path, required=True)
    p.add_argument("--labels-dir", type=Path, default=None)
    p.add_argument("--label-map", type=Path, default=None, help="LabelMe 라벨 이름 → slot JSON")
    p.add_argument("--preview", type=int, default=0)
    p.add_argument("--preview-dir", type=Path, default=Path("out/kfashion_preview"))
    args = p.parse_args()

    samples, skipped = scan_dataset(args.data_dir, args.labels_dir, load_label_map(args.label_map))
    slots = Counter(slot for s in samples for slot in s.polygons)
    categories = Counter(
        f"{slot}:{attrs.get('카테고리')}"
        for s in samples
        for slot, attrs in s.attributes.items()
        if attrs.get("카테고리")
    )
    print(f"사용 가능 샘플: {len(samples)}  /  건너뜀: {len(skipped)}")
    print("부위별 샘플 수:", dict(slots))
    print("카테고리 상위 10:", categories.most_common(10))
    ignored = Counter(name for s in samples for name in s.ignored_labels)
    if ignored:
        print("의류로 안 쓴 라벨 (필요하면 --label-map으로 연결):", dict(ignored.most_common(20)))
    reasons = Counter(r.split(": ", 1)[1].split(" (")[0] for r in skipped)
    if reasons:
        print("건너뛴 이유:", dict(reasons))
        print("  예:", skipped[0])

    if args.preview:
        args.preview_dir.mkdir(parents=True, exist_ok=True)
        for sample in samples[: args.preview]:
            image, mask = load_sample_mask(sample)
            save_png(args.preview_dir / f"{sample.image_path.stem}.jpg", overlay(image, mask))
        print(f"미리보기 저장: {args.preview_dir}")


if __name__ == "__main__":
    main()
