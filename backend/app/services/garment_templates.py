"""프로젝트에서 직접 작성한 패널 템플릿. 외부 의류 자산을 포함하지 않는다."""

TEMPLATE_CATALOG = {
    "tshirt_regular": {"kind": "티셔츠", "status": "panel", "ease": 1.0},
    "tshirt_oversized": {"kind": "티셔츠", "status": "panel", "ease": 1.12},
    "pants_wide": {"kind": "슬랙스", "status": "profile", "ease": 1.0},
    "pants_slim": {"kind": "청바지", "status": "profile", "ease": 1.0},
    "shirt": {"kind": "셔츠", "status": "legacy_approximation"},
    "hoodie": {"kind": "후드티", "status": "unavailable"},
    "jacket": {"kind": "재킷", "status": "legacy_approximation"},
}


def top_template(spec):
    oversized = spec["fit"] in {"loose", "루즈핏", "오버핏", "oversized", "와이드핏"}
    key = "tshirt_oversized" if oversized else "tshirt_regular"
    return key, TEMPLATE_CATALOG[key]
