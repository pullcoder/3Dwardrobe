"""합성 의류 정보로 재현 가능한 GLB 검증 산출물을 만든다. 사진을 수집하지 않는다."""

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.garment_mesh import build_glb, resolve_spec, validate_glb  # noqa: E402


def main():
    output = Path(__file__).resolve().parents[1] / "storage" / "phase4-validation"
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for name, kind, category in (
        ("tshirt", "티셔츠", "top"),
        ("pants", "청바지", "bottom"),
        ("jacket", "재킷", "outer"),
    ):
        spec = resolve_spec(
            {"garment_type": kind, "category": category, "color": "파랑", "neckline": "브이넥"}, {}
        )
        content, metadata = build_glb(spec)
        path = output / f"{name}.glb"
        path.write_bytes(content)
        validate_glb(path.read_bytes())
        results.append(
            {
                "file": path.name,
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
                "metadata": metadata,
            }
        )
    (output / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps([{k: r[k] for k in ("file", "bytes", "sha256")} for r in results]))


if __name__ == "__main__":
    main()
