"""실제 비공개 옷장 기반 추천의 저장·권한·현재 상태 검증."""

from uuid import uuid4

from sqlalchemy import func, select

from app.core.errors import AppError
from app.models import Garment, Recommendation, SavedMannequin, StylePreference
from app.schemas.recommendations import StylePreferences
from app.services.fittings import owned_row, resource
from app.services.generation import now, selected_mode
from app.services.recommendation_rules import (
    STYLE_LABELS,
    STYLE_TYPES,
    VERSION,
    item_context,
    rank_combinations,
    signature,
)


def preferences(db, user_id):
    row = db.get(StylePreference, user_id)
    return {
        **(row.data if row else StylePreferences().model_dump()),
        "revision": row.revision if row else 0,
    }


def live_items(db, row):
    items, pins, warnings = [], {}, []
    for part, garment_id in row.slots.items():
        garment = db.get(Garment, garment_id)
        if (
            not garment
            or garment.user_id != row.user_id
            or selected_mode(garment) is None
            or garment.data.get("category") != part
        ):
            warnings.append("삭제·권리 변경으로 사용할 수 없는 의류가 있습니다.")
            continue
        if (
            row.details.get("garment_revisions", {}).get(garment_id, garment.revision)
            != garment.revision
        ):
            warnings.append("추천 이후 의류 정보가 변경되었습니다. 새 추천을 실행해 주세요.")
            continue
        model_id = None
        try:
            model_id = resource(db, row.user_id, garment_id)["model_asset_id"]
            if row.model_refs.get(part) and row.model_refs[part] != model_id:
                model_id = None
                warnings.append("추천 이후 3D 모델이 변경되었습니다. 새 추천을 실행해 주세요.")
        except AppError:
            pass
        if model_id:
            pins[part] = model_id
        items.append(
            {
                "id": garment.id,
                "part": part,
                "name": garment.data["name"],
                "info": garment.data,
                "revision": garment.revision,
                "reconstruction_mode": garment.reconstruction_mode,
                "model_ready": bool(model_id),
            }
        )
    return items, pins, list(dict.fromkeys(warnings))


def read_recommendation(db, row):
    items, pins, warnings = live_items(db, row)
    available = len(items) == len(row.slots)
    return {
        "id": row.id,
        "name": row.details["name"],
        "reasons": row.details["reasons"] if available else [],
        "notes": row.details["notes"] if available else [],
        "engine": row.details["engine"],
        "body_used": row.details["body_used"],
        "items": items,
        "slots": row.slots if available else {},
        "available": available,
        "fitting_available": available and len(pins) == len(row.slots),
        "warnings": warnings,
        "feedback": row.feedback,
        "saved_at": row.saved_at,
        "created_at": row.created_at,
        "mannequin_id": row.mannequin_id,
    }


def generate(db, user_id, body):
    if (
        db.scalar(
            select(func.count())
            .select_from(Recommendation)
            .where(Recommendation.user_id == user_id)
        )
        + body.count
        > 300
    ):
        raise AppError(
            "STORAGE_LIMIT", "추천 기록은 300개까지 보관합니다. 이전 기록을 삭제해 주세요.", 413
        )
    prefs = preferences(db, user_id)
    profile = body.body.model_dump() if body.body else None
    if body.mannequin_id:
        profile = owned_row(db, SavedMannequin, user_id, body.mannequin_id).profile
    items = []
    for garment in db.scalars(
        select(Garment).where(Garment.user_id == user_id).order_by(Garment.id)
    ):
        if selected_mode(garment) is None:
            continue
        context, notes, palette = item_context(garment.data, prefs, profile)
        items.append(
            {
                "id": garment.id,
                "category": garment.data["category"],
                "info": garment.data,
                "revision": garment.revision,
                "context": context,
                "notes": [f"{garment.data['name']}: {note}" for note in notes],
                "palette": palette,
            }
        )
    feedback = {}
    for previous in db.scalars(
        select(Recommendation)
        .where(Recommendation.user_id == user_id)
        .order_by(Recommendation.feedback_at, Recommendation.created_at, Recommendation.id)
    ):
        if previous.feedback_at:
            feedback[signature(previous.slots)] = previous.feedback
    ranked, stats = rank_combinations(items, prefs, profile, feedback, body.count)
    rows = []
    for index, candidate in enumerate(ranked):
        kinds = {item["info"].get("garment_type") for item in candidate["items"]}
        matched = [STYLE_LABELS[s] for s in prefs["styles"] if kinds & STYLE_TYPES[s]]
        names = [item["info"]["name"] for item in candidate["items"]]
        reasons = [" + ".join(names) + " 조합입니다."]
        if matched:
            reasons.append(f"선택한 {', '.join(matched)} 취향의 초기 의류 종류 규칙에 해당합니다.")
        if prefs["preferred_colors"]:
            reasons.append("입력한 선호 색상과 등록된 의류 색상을 비교해 순위를 계산했습니다.")
        reasons.append(
            "등록 정보와 취향을 비교한 규칙 기반 제안이며, "
            "실제 착용감이나 패션 품질을 보장하지 않습니다."
        )
        row = Recommendation(
            id=str(uuid4()),
            user_id=user_id,
            slots=candidate["slots"],
            model_refs={},
            mannequin_id=body.mannequin_id,
            created_at=now(),
            details={
                "name": f"{matched[0] if matched else '옷장'} 코디 {index + 1}",
                "reasons": reasons,
                "notes": candidate["notes"],
                "engine": VERSION,
                "body_used": bool(profile),
                "internal_score": candidate["score"],
                "components": candidate["components"],
                "garment_revisions": {item["id"]: item["revision"] for item in candidate["items"]},
            },
        )
        _, pins, _ = live_items(db, row)
        row.model_refs = pins
        db.add(row)
        rows.append(row)
    db.flush()
    return {
        "items": [read_recommendation(db, row) for row in rows],
        "stats": stats,
        "message": "가능한 실제 조합만 제공했습니다."
        if len(rows) < body.count
        else "규칙 기반 추천을 완료했습니다.",
    }
