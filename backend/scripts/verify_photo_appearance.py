"""직접 그린 검증용 앞뒤 표식으로 실제 GLB 산출물을 준비한다. 실사진 품질 주장이 아니다."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_photo_appearance import marked_photo, photo_spec  # noqa: E402

from app.services.garment_mesh import build_glb, validate_glb  # noqa: E402


def main():
    target = ROOT / "storage/photo-appearance"
    target.mkdir(parents=True, exist_ok=True)
    results = []
    for name, kind in (("tshirt", "top"), ("pants", "bottom")):
        content, metadata = build_glb(photo_spec(kind))
        validate_glb(content)
        (target / f"{name}.glb").write_bytes(content)
        for back in (False, True):
            (target / f"{name}-{'back' if back else 'front'}.png").write_bytes(
                marked_photo(kind, back)
            )
        results.append(
            {
                "file": f"{name}.glb",
                "bytes": len(content),
                "input": "synthetic_color_markers",
                "metadata": metadata,
            }
        )
    (target / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps([{k: item[k] for k in ("file", "bytes", "input")} for item in results]))


if __name__ == "__main__":
    main()
