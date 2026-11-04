"""공통 누끼 입력 비교. 기본 입력은 합성 검증물이며 실제 사진 품질 비교가 아니다."""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.garment_mesh import build_glb, resolve_spec, validate_glb  # noqa: E402
from app.services.generation_engines import engine_catalog, hardware  # noqa: E402
from app.services.pants_silhouette import analyze_pants  # noqa: E402
from app.services.top_silhouette import analyze_top  # noqa: E402


def fixture(path, pants):
    image = Image.new("RGBA", (512, 640))
    draw = ImageDraw.Draw(image)
    points = (
        [(140, 70), (370, 70), (410, 580), (280, 580), (255, 270), (235, 580), (105, 580)]
        if pants
        else [
            (180, 80),
            (220, 100),
            (290, 100),
            (330, 80),
            (440, 180),
            (375, 255),
            (350, 215),
            (350, 550),
            (160, 550),
            (160, 215),
            (135, 255),
            (70, 180),
        ]
    )
    draw.polygon(points, fill=(60, 100, 160, 255))
    image.save(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tshirt", type=Path)
    parser.add_argument("--pants", type=Path)
    args = parser.parse_args()
    directory = Path(__file__).resolve().parents[1] / "storage/engine-comparison"
    directory.mkdir(parents=True, exist_ok=True)
    report = {"environment": hardware(), "models_executed": ["template"], "results": []}
    for name, source, kind, category, analyze in (
        ("tshirt", args.tshirt, "티셔츠", "top", analyze_top),
        ("wide-pants", args.pants, "슬랙스", "bottom", analyze_pants),
    ):
        synthetic = source is None
        if synthetic:
            source = directory / f"{name}-synthetic.png"
            fixture(source, category == "bottom")
        content = source.read_bytes()
        shape = analyze(content)
        spec = resolve_spec(
            {"garment_type": kind, "category": category, "fit": "와이드", "color": "파랑"},
            {"silhouette": shape},
        )
        started = time.perf_counter()
        glb, metadata = build_glb(spec)
        validate_glb(glb)
        elapsed = time.perf_counter() - started
        path = directory / f"{name}-template.glb"
        path.write_bytes(glb)
        shared = {
            "sample": name,
            "input_kind": "synthetic_fixture" if synthetic else "user_cutout",
            "input_sha256": hashlib.sha256(content).hexdigest(),
        }
        report["results"].append(
            {
                **shared,
                "engine": "template",
                "status": "completed",
                "glb": path.name,
                "bytes": len(glb),
                "seconds": elapsed,
                "gpu_memory_bytes": None,
                "gpu_used": False,
                "mesh": metadata.get("mesh_quality"),
                "texture": metadata.get("texture_policy"),
                "silhouette_accuracy": "not_measured",
                "shape_accuracy": "not_measured",
                "mannequin": "existing_visual_contract_only",
            }
        )
        for entry in engine_catalog()[1:]:
            report["results"].append(
                {
                    **shared,
                    "engine": entry["id"],
                    "status": "not_run",
                    "reasons": entry["reasons"],
                    "glb": None,
                    "bytes": None,
                    "seconds": None,
                    "gpu_memory_bytes": None,
                    "silhouette_accuracy": None,
                    "shape_accuracy": None,
                    "texture": None,
                    "mesh": None,
                    "mannequin": "not_tested",
                }
            )
    (directory / "results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
