"""초기 가설 가중치의 설명 가능한 규칙 추천. 확률·패션 품질·실제 착용감 점수가 아니다."""

from itertools import combinations, product
from math import ceil, isfinite

VERSION = "stylefit-rules-1.0"
WEIGHTS = {
    "style": 0.20,
    "color": 0.18,
    "purpose": 0.16,
    "season": 0.12,
    "fit": 0.08,
    "size": 0.12,
    "feedback": 0.08,
    "mood": 0.04,
    "type": 0.02,
}
DIVERSITY_WEIGHT = 0.18
MAX_CANDIDATES = 12_000
STYLE_LABELS = {
    "minimal": "미니멀",
    "casual": "캐주얼",
    "street": "스트릿",
    "formal": "포멀",
    "business_casual": "비즈니스 캐주얼",
    "sporty": "스포티",
    "vintage": "빈티지",
    "other": "기타",
}
STYLE_TYPES = {
    "minimal": {"티셔츠", "니트", "셔츠", "슬랙스", "코트", "재킷"},
    "casual": {"티셔츠", "맨투맨", "후드티", "청바지", "반바지", "카디건"},
    "street": {"후드티", "맨투맨", "티셔츠", "청바지", "재킷", "패딩"},
    "formal": {"셔츠", "슬랙스", "스커트", "재킷", "코트"},
    "business_casual": {"셔츠", "니트", "슬랙스", "카디건", "재킷"},
    "sporty": {"티셔츠", "맨투맨", "후드티", "반바지", "패딩"},
    "vintage": {"셔츠", "카디건", "청바지", "스커트", "재킷"},
    "other": set(),
}
PURPOSE_TYPES = {
    "daily": STYLE_TYPES["casual"],
    "work": STYLE_TYPES["business_casual"],
    "occasion": STYLE_TYPES["formal"],
    "exercise": STYLE_TYPES["sporty"],
    "travel": STYLE_TYPES["casual"] | {"패딩", "재킷"},
}
SEASON_TYPES = {
    "spring": {"셔츠", "티셔츠", "니트", "카디건", "청바지", "슬랙스", "스커트", "재킷"},
    "summer": {"티셔츠", "셔츠", "반바지", "스커트", "슬랙스"},
    "autumn": {"셔츠", "니트", "맨투맨", "후드티", "카디건", "청바지", "슬랙스", "재킷", "코트"},
    "winter": {"니트", "맨투맨", "후드티", "카디건", "청바지", "슬랙스", "코트", "패딩"},
}
COLOR_ALIASES = {
    "black": ("검정", "검은", "블랙", "black"),
    "white": ("흰색", "화이트", "흰", "white", "아이보리", "ivory"),
    "gray": ("회색", "그레이", "gray", "grey", "차콜"),
    "beige": ("베이지", "beige", "크림", "cream"),
    "brown": ("갈색", "브라운", "brown"),
    "blue": ("파랑", "파란", "블루", "blue", "청색", "남색", "네이비", "navy"),
    "red": ("빨강", "빨간", "레드", "red"),
    "green": ("초록", "그린", "green", "카키", "khaki"),
    "yellow": ("노랑", "노란", "옐로", "yellow"),
    "pink": ("분홍", "핑크", "pink"),
    "purple": ("보라", "퍼플", "purple"),
    "orange": ("주황", "오렌지", "orange"),
}
NEUTRALS = {"black", "white", "gray", "beige", "brown"}
FIT_ALIASES = {
    "slim": ("슬림", "slim", "fitted"),
    "regular": ("레귤러", "regular"),
    "oversized": ("오버", "oversized", "oversize", "relaxed", "루즈"),
}


def colors(value):
    text = (value or "").lower()
    return {
        key for key, aliases in COLOR_ALIASES.items() if any(alias in text for alias in aliases)
    }


def color_set(values):
    return set().union(*(colors(value) for value in values)) if values else set()


def signature(slots):
    return tuple(slots.get(part) or "" for part in ("top", "bottom", "outer"))


def measured(info, label, kind):
    """의류 실측·의미·단위가 명확한 수치만 비교한다. OCR보다 수동 수치가 우선이다."""
    rows = sorted(info.get("measurements", []), key=lambda row: row.get("source") != "user_entered")
    # 여러 사이즈의 동일 항목이 있으면 선택 사이즈와 정확히 맞는 행만 쓴다.
    selected = info.get("size", "").strip().upper()
    for row in rows:
        if row.get("target") != "garment" or row.get("kind") != kind:
            continue
        if row.get("size") and row["size"].strip().upper() != selected:
            continue
        if row.get("label", "").replace(" ", "") not in label:
            continue
        value = row.get("value")
        unit = row.get("unit")
        if (
            not isinstance(value, (int, float))
            or not isfinite(value)
            or value <= 0
            or unit not in {"cm", "mm", "inch"}
        ):
            continue
        return value * {"cm": 1, "mm": 0.1, "inch": 2.54}[unit]
    return None


def size_evidence(info, body, preferred_fit):
    notes, values = [], []
    body_values = body.get("values", {}) if body else {}
    fields = [
        ("chest", {"가슴단면", "chest"}, "가슴둘레"),
        ("waist", {"허리단면", "waist"}, "허리둘레"),
        ("hip", {"엉덩이단면", "hip"}, "엉덩이둘레"),
    ]
    target = {"slim": (2, 8), "regular": (6, 16), "oversized": (14, 32), "any": (2, 30)}[
        preferred_fit
    ]
    for key, labels, label in fields:
        body_value = body_values.get(key)
        flat = measured(info, labels, "flat")
        if flat is None or body_value is None:
            continue
        difference = flat * 2 - body_value
        source = (
            "사진 기반 추정값" if body.get("origins", {}).get(key) == "estimated" else "제공한 수치"
        )
        notes.append(
            f"{label}: 의류 단면×2와 {source}의 차이는 {difference:+.1f}cm입니다. "
            "단면 기반 근사이며 착용감을 보장하지 않습니다."
        )
        values.append(
            1.0 if target[0] <= difference <= target[1] else 0.2 if difference < 0 else 0.45
        )
    return sum(values) / len(values) if values else 0.5, notes


def item_context(info, prefs, body):
    kind = info.get("garment_type", "unknown")
    known_kind = kind not in {"", "unknown", "기타"}
    styles = [s for s in prefs["styles"] if STYLE_TYPES[s]]
    style = max((float(kind in STYLE_TYPES[s]) for s in styles), default=0.5) if known_kind else 0.5
    purpose = (
        float(kind in PURPOSE_TYPES[prefs["purpose"]])
        if prefs["purpose"] != "any" and known_kind
        else 0.5
    )
    season = (
        float(kind in SEASON_TYPES[prefs["season"]])
        if prefs["season"] != "any" and known_kind
        else 0.5
    )
    fit_value = info.get("fit", "").lower()
    actual_fit = next(
        (
            key
            for key, aliases in FIT_ALIASES.items()
            if any(alias in fit_value for alias in aliases)
        ),
        None,
    )
    fit = float(actual_fit == prefs["fit"]) if actual_fit and prefs["fit"] != "any" else 0.5
    size, notes = size_evidence(info, body, prefs["fit"])
    palette = colors(info.get("color")) | colors(info.get("secondary_color"))
    mood = 0.5
    if prefs["mood"] == "calm" and palette:
        mood = float(palette <= NEUTRALS)
    elif prefs["mood"] == "neat" and known_kind:
        mood = float(kind in STYLE_TYPES["formal"])
    elif prefs["mood"] == "active" and known_kind:
        mood = float(kind in STYLE_TYPES["sporty"])
    elif prefs["mood"] == "expressive":
        pattern = info.get("pattern", "unknown")
        if pattern not in {"unknown", ""}:
            mood = float(pattern not in {"무지", "solid"})
    type_score = (
        float(kind in prefs["preferred_types"]) if prefs["preferred_types"] and known_kind else 0.5
    )
    return (
        {
            "style": style,
            "purpose": purpose,
            "season": season,
            "fit": fit,
            "size": size,
            "mood": mood,
            "type": type_score,
        },
        notes,
        palette,
    )


def harmony(palettes, preferred):
    known = [palette for palette in palettes if palette]
    if not known:
        return 0.5
    pairs = []
    for a, b in combinations(known, 2):
        pairs.append(0.95 if (a | b) <= NEUTRALS or a & b else 0.85 if (a | b) & NEUTRALS else 0.55)
    base = sum(pairs) / len(pairs) if pairs else 0.5
    return (
        0.7 * base + 0.3 * sum(bool(p & preferred) for p in known) / len(known)
        if preferred
        else base
    )


def rank_combinations(items, prefs, body, feedback, count):
    """입력은 이미 소유권/권리를 검사한 옷장이다. 외부 이미지·고정 코디를 만들지 않는다."""
    avoided, preferred = color_set(prefs["avoided_colors"]), color_set(prefs["preferred_colors"])
    raw_avoid = {v.lower() for v in prefs["avoided_colors"]}
    eligible = [
        item
        for item in items
        if not (item["palette"] & avoided)
        and not any(
            v
            in (
                item["info"].get("color", "") + " " + (item["info"].get("secondary_color") or "")
            ).lower()
            for v in raw_avoid
        )
    ]
    groups = {
        part: sorted([i for i in eligible if i["category"] == part], key=lambda i: i["id"])
        for part in ("top", "bottom", "outer")
    }
    if not groups["top"] or not groups["bottom"]:
        return [], {"combinations": 0, "evaluated": 0, "eligible": len(eligible)}
    combinations_list = list(product(groups["top"], groups["bottom"], [None, *groups["outer"]]))
    stride = max(1, ceil(len(combinations_list) / MAX_CANDIDATES))
    candidates = []
    for combination in combinations_list[::stride]:
        chosen = [item for item in combination if item]
        slots = {item["category"]: item["id"] for item in chosen}
        key = signature(slots)
        if feedback.get(key) == "exclude":
            continue
        components = {
            name: sum(item["context"][name] for item in chosen) / len(chosen)
            for name in ("style", "purpose", "season", "fit", "size", "mood", "type")
        }
        components["color"] = harmony([i["palette"] for i in chosen], preferred)
        response = feedback.get(key)
        # 동일 조합 및 공통 의류의 실제 명시 피드백만 사용한다.
        likes, dislikes = 0, 0
        chosen_ids = set(key) - {""}
        for previous, value in feedback.items():
            overlap = len(chosen_ids & (set(previous) - {""})) / len(chosen_ids)
            likes += overlap if value == "like" else 0
            dislikes += overlap if value == "dislike" else 0
        components["feedback"] = max(
            0,
            min(
                1,
                0.5
                + 0.25 * (likes - dislikes)
                + (0.25 if response == "like" else -0.25 if response == "dislike" else 0),
            ),
        )
        notes = [note for item in chosen for note in item["notes"]]
        outer = combination[2]
        if outer:
            top_chest = measured(combination[0]["info"], {"가슴단면", "chest"}, "flat")
            outer_chest = measured(outer["info"], {"가슴단면", "chest"}, "flat")
            if top_chest is not None and outer_chest is not None:
                notes.append(
                    f"겉옷과 상의 가슴 단면 차이는 {outer_chest - top_chest:+.1f}cm입니다. "
                    "원단·두께·물성 정보가 없어 레이어 착용감을 보장하지 않습니다."
                )
                if outer_chest < top_chest:
                    components["size"] *= 0.5
        # 명시된 길이 비율만 참고한다. 체형 미적 판단은 하지 않는다.
        top_length = measured(combination[0]["info"], {"총장", "length"}, "length")
        bottom_length = measured(combination[1]["info"], {"총장", "length"}, "length")
        if top_length is not None and bottom_length is not None:
            notes.append(
                f"상의/하의 의류 총장은 {top_length:g}/{bottom_length:g}cm입니다. "
                "선호 길이는 별도 확인이 필요합니다."
            )
        score = sum(WEIGHTS[name] * value for name, value in components.items())
        candidates.append(
            {
                "slots": slots,
                "items": chosen,
                "components": components,
                "score": score,
                "notes": notes,
            }
        )
    selected = []
    while candidates and len(selected) < count:

        def adjusted(candidate):
            ids = set(candidate["slots"].values())
            similarity = max(
                (
                    len(ids & set(s["slots"].values())) / len(ids | set(s["slots"].values()))
                    for s in selected
                ),
                default=0,
            )
            same_pair = any(
                candidate["slots"].get("top") == s["slots"].get("top")
                and candidate["slots"].get("bottom") == s["slots"].get("bottom")
                for s in selected
            )
            return candidate["score"] - DIVERSITY_WEIGHT * similarity - 0.12 * same_pair

        best = max(candidates, key=adjusted)
        candidates.remove(best)
        selected.append(best)
    return selected, {
        "combinations": len(combinations_list),
        "evaluated": len(combinations_list[::stride]),
        "eligible": len(eligible),
    }
