"""합성 의류/라벨과 기존 공식 체형 테스트 사진으로 실제 CPU 추론을 검사한다."""

import json
import sys
import time
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.garment_ai import GarmentAI  # noqa: E402


def fixtures():
    target = ROOT.parent / "frontend/e2e/fixtures/garments"
    target.mkdir(parents=True, exist_ok=True)
    shirt = Image.new("RGB", (600, 700), "#f1efec")
    draw = ImageDraw.Draw(shirt)
    draw.polygon(
        [
            (200, 100),
            (130, 140),
            (60, 260),
            (160, 310),
            (200, 260),
            (200, 600),
            (400, 600),
            (400, 260),
            (440, 310),
            (540, 260),
            (470, 140),
            (400, 100),
            (350, 130),
            (250, 130),
        ],
        fill="#203c98",
    )
    draw.arc((250, 75, 350, 160), 0, 180, fill="#182a63", width=12)
    shirt.save(target / "shirt.png")
    font = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 38)
    for kind, lines in {
        "size": ["SIZE M", "실측 총장 70 cm", "가슴단면 50 cm", "허리둘레 80 cm"],
        "material": ["소재 및 혼용률", "면 65%", "폴리에스터 35%"],
    }.items():
        label = Image.new("RGB", (1000, 380), "white")
        draw = ImageDraw.Draw(label)
        for i, line in enumerate(lines):
            draw.text((40, 30 + i * 75), line, fill="black", font=font)
        label.save(target / f"{kind}.png")
    return target


if __name__ == "__main__":
    target = fixtures()
    if "--fixtures-only" in sys.argv:
        print("Synthetic garment fixtures prepared.")
        sys.exit(0)
    engine = GarmentAI()
    started = time.perf_counter()
    image = Image.open(target / "shirt.png").convert("RGB")
    result = {"classification": engine.classify(image)}
    segmented = engine.segment(image.copy())
    import base64

    png = base64.b64decode(segmented.pop("png"))
    (target / "cutout.png").write_bytes(png)
    alpha = Image.open(BytesIO(png)).getchannel("A")
    assert alpha.getextrema() == (0, 255)
    result["segmentation"] = segmented
    for kind in ("size", "material"):
        result[kind] = engine.ocr((target / f"{kind}.png").read_bytes(), kind)
    assert result["size"]["measurements"], result["size"]
    assert result["material"]["composition"], result["material"]
    # 사진은 기존 단계에서 준비한 공식 고정 테스트 에셋만 사용한다.
    photo = ROOT.parent / "frontend/e2e/fixtures/full-body.jpg"
    if photo.is_file():
        real = Image.open(photo).convert("RGB")
        w, h = real.size
        result["existing_photo_crop_classification"] = engine.classify(
            real.crop((int(w * 0.2), int(h * 0.18), int(w * 0.8), int(h * 0.52)))
        )
    result["elapsed_seconds"] = round(time.perf_counter() - started, 2)
    (target / "verification.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=True, indent=2))
