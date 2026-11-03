"""인증된 사용자 본인의 취향·추천·피드백 API."""

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.api.v1.garments import database
from app.core.errors import AppError
from app.models import Asset, Recommendation, SavedMannequin, StylePreference
from app.schemas.recommendations import (
    PreferenceUpdate,
    RecommendationApply,
    RecommendationFeedback,
    RecommendationInput,
)
from app.services.auth import current_user
from app.services.fittings import owned_row
from app.services.generation import now
from app.services.recommendations import generate, live_items, preferences, read_recommendation

router = APIRouter()


@router.get("/style-preferences")
def get_preferences(request: Request):
    with database(request) as db:
        return preferences(db, current_user(request, db).id)


@router.put("/style-preferences")
def put_preferences(body: PreferenceUpdate, request: Request):
    with database(request) as db:
        user_id = current_user(request, db).id
        data = body.model_dump(exclude={"revision"})
        if body.revision == 0:
            db.add(StylePreference(user_id=user_id, data=data, updated_at=now()))
        else:
            changed = db.execute(
                update(StylePreference)
                .where(
                    StylePreference.user_id == user_id, StylePreference.revision == body.revision
                )
                .values(data=data, revision=StylePreference.revision + 1, updated_at=now())
            )
            if not changed.rowcount:
                raise AppError("CONFLICT", "취향이 변경되었습니다. 다시 불러와 주세요.", 409)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise AppError("CONFLICT", "취향이 변경되었습니다. 다시 불러와 주세요.", 409) from None
        return preferences(db, user_id)


@router.post("/recommendations", status_code=201)
def create_recommendations(body: RecommendationInput, request: Request):
    with database(request) as db:
        result = generate(db, current_user(request, db).id, body)
        db.commit()
        return result


@router.get("/recommendations")
def list_recommendations(
    request: Request,
    saved_only: bool = False,
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    with database(request) as db:
        query = select(Recommendation).where(Recommendation.user_id == current_user(request, db).id)
        if saved_only:
            query = query.where(Recommendation.saved_at.is_not(None))
        return [
            read_recommendation(db, row)
            for row in db.scalars(
                query.order_by(Recommendation.created_at.desc(), Recommendation.id)
                .offset(offset)
                .limit(limit)
            )
        ]


@router.get("/recommendations/{recommendation_id}")
def get_recommendation(recommendation_id: str, request: Request):
    with database(request) as db:
        return read_recommendation(
            db, owned_row(db, Recommendation, current_user(request, db).id, recommendation_id)
        )


@router.post("/recommendations/{recommendation_id}/feedback")
def feedback(recommendation_id: str, body: RecommendationFeedback, request: Request):
    with database(request) as db:
        row = owned_row(db, Recommendation, current_user(request, db).id, recommendation_id)
        row.feedback, row.feedback_at = body.feedback, now()
        db.commit()
        return read_recommendation(db, row)


@router.post("/recommendations/{recommendation_id}/save")
def save(recommendation_id: str, request: Request):
    with database(request) as db:
        row = owned_row(db, Recommendation, current_user(request, db).id, recommendation_id)
        if not read_recommendation(db, row)["available"]:
            raise AppError(
                "STALE_RECOMMENDATION", "사용할 수 없는 의류가 있습니다. 새로 추천해 주세요.", 409
            )
        row.saved_at = row.saved_at or now()
        db.commit()
        return read_recommendation(db, row)


@router.delete("/recommendations/{recommendation_id}", status_code=204)
def delete_recommendation(recommendation_id: str, request: Request):
    with database(request) as db:
        db.delete(owned_row(db, Recommendation, current_user(request, db).id, recommendation_id))
        db.commit()


@router.get("/recommendations/{recommendation_id}/preview/{part}")
def preview(recommendation_id: str, part: str, request: Request):
    with database(request) as db:
        row = owned_row(db, Recommendation, current_user(request, db).id, recommendation_id)
        items, _, _ = live_items(db, row)
        item = next((item for item in items if item["part"] == part), None)
        if not item:
            raise AppError("NOT_FOUND", "이미지를 표시할 수 없습니다.", 404)
        assets = list(
            db.scalars(
                select(Asset).where(
                    Asset.garment_id == item["id"], Asset.slot.in_(["cutout_front", "front"])
                )
            )
        )
        assets.sort(key=lambda asset: asset.slot != "cutout_front")
        if not assets:
            raise AppError("NOT_FOUND", "보관된 의류 이미지가 없습니다.", 404)
        return Response(content=assets[0].content, media_type=assets[0].mime)


@router.post("/recommendations/{recommendation_id}/apply")
def apply(recommendation_id: str, body: RecommendationApply, request: Request):
    with database(request) as db:
        user_id = current_user(request, db).id
        row = owned_row(db, Recommendation, user_id, recommendation_id)
        state = read_recommendation(db, row)
        if not state["fitting_available"]:
            raise AppError(
                "MODEL_UNAVAILABLE", "의류 권리와 3D 모델을 확인하고 새 추천을 실행해 주세요.", 409
            )
        mannequin_id = body.mannequin_id or row.mannequin_id
        mannequin = owned_row(db, SavedMannequin, user_id, mannequin_id) if mannequin_id else None
        _, pins, _ = live_items(db, row)
        return {
            "recommendation_id": row.id,
            "slots": row.slots,
            "pins": pins,
            "mannequin_id": mannequin_id,
            "mannequin": mannequin.profile if mannequin else None,
        }
