"""A는 자체 생성 체크만, 제한된 B는 검증된 앞면의 투영 근사만 사용한다."""

from functools import lru_cache
from io import BytesIO

import numpy as np
from PIL import Image, ImageDraw, ImageOps


def legacy_check(color):
    base = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))
    light = tuple(min(255, int(v * 0.58 + 100)) for v in base)
    dark = tuple(max(12, int(v * 0.30)) for v in base)
    image = Image.new("RGB", (384, 640), light)
    draw = ImageDraw.Draw(image)
    for x in range(0, 384, 24):
        draw.rectangle((x, 0, x + 6, 640), fill=base)
        draw.line((x + 11, 0, x + 11, 640), fill=dark, width=1)
    for y in range(0, 640, 24):
        draw.rectangle((0, y, 384, y + 6), fill=base)
        draw.line((0, y + 11, 384, y + 11), fill=dark, width=1)
    # 원본과 독립적인 일반 허리밴드·박음선 표현. 주름 자체는 메시에도 반영한다.
    draw.rectangle((0, 0, 384, 22), fill=base)
    for x in range(0, 384, 7):
        draw.line((x, 1, x + 1, 20), fill=dark, width=1)
    draw.line((0, 21, 384, 21), fill=dark, width=2)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


@lru_cache(maxsize=8)
def generic_check(color):
    """직접 설계한 미세 체크·실 짜임. 입력 사진/로고/체크 주기를 읽지 않는다."""
    base = np.array([int(color[i : i + 2], 16) for i in (1, 3, 5)], dtype=float)
    y, x = np.mgrid[:1536, :1024]
    # 서로 다른 폭의 일반 격자와 작은 실 교차를 결합한다.
    stripe = ((x % 18 < 2) | (y % 18 < 2)).astype(float)
    secondary = ((x % 54 < 1) | (y % 54 < 1)).astype(float)
    weave = ((x + y) % 2 * 2 - 1) * 1.8
    threads = np.sin(x * 2.1) * np.cos(y * 1.7) * 0.8
    pixels = base[None, None, :] * (1 - stripe[:, :, None] * 0.30)
    pixels = pixels * (1 - secondary[:, :, None] * 0.12)
    pixels += (weave + threads)[:, :, None]
    # 허리밴드는 동일한 일반 원단의 주름과 두 줄 박음선으로 표현한다.
    pixels[:54] *= (0.9 + 0.08 * np.cos(x[:54] * 0.60))[:, :, None]
    for row in (12, 45, 1510, 1514):
        pixels[row : row + 1, ::4] *= 0.7
    image = Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8))
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def materials(spec):
    mode = spec.get("mode", "A")
    if mode == "B":
        if not spec.get("_front_png") or not spec.get("_verified_projection"):
            raise ValueError("verified source required")
        with Image.open(BytesIO(spec["_front_png"])) as source:
            front = ImageOps.exif_transpose(source).convert("RGBA")
        if spec.get("_front_size"):
            front = front.resize(tuple(spec["_front_size"]), Image.Resampling.LANCZOS)
        bbox = spec.get("_front_bbox")
        if bbox:
            front = front.crop(tuple(bbox))
        front.thumbnail((768, 1024))
        background = Image.new("RGBA", front.size, "white")
        background.alpha_composite(front)
        front = background.convert("RGB").resize((768, 1280), Image.Resampling.LANCZOS)
        with Image.open(BytesIO(generic_check(spec["color"]))) as fallback:
            back = (
                fallback.convert("RGB").resize((768, 1280), Image.Resampling.LANCZOS)
                if spec.get("pattern") == "check"
                else Image.new("RGB", (768, 1280), spec["color"])
            )
        atlas = Image.new("RGB", (1536, 1280))
        atlas.paste(front, (0, 0))
        atlas.paste(back, (768, 0))
        output = BytesIO()
        atlas.save(output, format="PNG")
        return output.getvalue(), "verified_front_projection"
    if spec.get("pattern") == "check":
        return generic_check(spec["color"]), "procedural_generic_check"
    return None, "solid_color"
