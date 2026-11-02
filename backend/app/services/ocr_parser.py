"""OCR 원문을 보존하고 명시된 행만 파싱한다. 표의 열·단위는 추측하지 않는다."""

import re

MATERIALS = (
    r"면|폴리에스터|나일론|울|모|스판덱스|레이온|아크릴|린넨|캐시미어|"
    r"cotton|polyester|nylon|wool|spandex|elastane|rayon|acrylic|linen|cashmere"
)
MEASURES = (
    r"총장|어깨너비|가슴단면|허리단면|엉덩이단면|소매길이|소매 길이|밑위|허벅지단면|"
    r"밑단|가슴둘레|허리둘레|엉덩이둘레|length|shoulder|chest|waist|hip|sleeve|inseam"
)


def parse_ocr(text: str, kind: str):
    composition = []
    measurements = []
    warnings = []
    if kind == "material":
        for match in re.finditer(
            rf"({MATERIALS})\s*[:：]?\s*(\d{{1,3}}(?:\.\d+)?)?\s*(%)?", text, re.I
        ):
            percent = float(match[2]) if match[2] and match[3] else None
            if percent is not None and percent > 100:
                continue
            composition.append({"name": match[1], "percent": percent, "source": "ocr"})
        known = [c["percent"] for c in composition if c["percent"] is not None]
        if known and (len(known) != len(composition) or abs(sum(known) - 100) > 0.1):
            warnings.append(
                "혼용률 합계가 100%인지 원본 라벨에서 확인해 주세요. "
                "겉감·안감이 섞였을 수 있습니다."
            )
    else:
        for line in text.splitlines():
            label = re.search(MEASURES, line, re.I)
            if not label:
                continue
            # 여러 수치가 있는 표의 행은 사이즈 열 대응이 불명확하므로 자동 대응하지 않는다.
            numbers = re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?", line)
            if len(numbers) != 1:
                warnings.append(
                    "여러 사이즈 열 또는 불명확한 수치 행은 원문을 보고 직접 입력해 주세요."
                )
                continue
            unit_match = re.search(r"\b(cm|mm|inch|inches)\b|인치|센티미터|밀리미터", line, re.I)
            unit = "unknown"
            if unit_match:
                token = unit_match[0].lower()
                unit = {"cm": "cm", "mm": "mm", "센티미터": "cm", "밀리미터": "mm"}.get(
                    token, "inch"
                )
            name = label[0]
            meaning = (
                "flat"
                if "단면" in line
                else "circumference"
                if "둘레" in line
                else "length"
                if re.search("총장|길이|length|inseam", line, re.I)
                else "unknown"
            )
            target = (
                "body"
                if re.search("신체|권장|body|recommended", line, re.I)
                else "garment"
                if re.search("의류|실측|garment", line, re.I)
                else "unknown"
            )
            size_match = re.search(r"\b(XXS|XS|S|M|L|XL|XXL|2XL|3XL)\b", line, re.I)
            measurements.append(
                {
                    "label": name,
                    "size": size_match[0] if size_match else None,
                    "value": float(numbers[0]),
                    "unit": unit,
                    "kind": meaning,
                    "target": target,
                    "source": "ocr",
                }
            )
    if not text.strip():
        warnings.append("읽을 수 있는 글자가 없습니다. 사진을 교체해 주세요.")
    return {
        "sizes": list(
            dict.fromkeys(re.findall(r"\b(?:XXS|XS|S|M|L|XL|XXL|2XL|3XL)\b", text, re.I))
        ),
        "composition": composition,
        "measurements": measurements,
        "warnings": list(dict.fromkeys(warnings)),
    }
