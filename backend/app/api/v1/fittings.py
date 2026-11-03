"""인증된 비공개 피팅과 코디. 체형은 별도 동의로 최소 수치만 저장한다."""

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.api.v1.garments import database
from app.models import Fitting, Outfit
from app.schemas.fittings import FittingInput, FittingPatch, OutfitInput
from app.services.auth import current_user
from app.services.fittings import (
    owned_row,
    prune_mannequins,
    read_state,
    resource,
    save_fitting,
    save_outfit,
)

router = APIRouter()


@router.get("/fittings/resources/{garment_id}")
def get_resource(garment_id: str, request: Request):
    with database(request) as db:
        return resource(db, current_user(request, db).id, garment_id)


@router.post("/fittings", status_code=201)
def create_fitting(body: FittingInput, request: Request):
    with database(request) as db:
        row = save_fitting(db, current_user(request, db).id, body)
        db.commit()
        return read_state(db, row)


@router.get("/fittings/{fitting_id}")
def get_fitting(fitting_id: str, request: Request):
    with database(request) as db:
        return read_state(db, owned_row(db, Fitting, current_user(request, db).id, fitting_id))


@router.patch("/fittings/{fitting_id}")
def patch_fitting(fitting_id: str, body: FittingPatch, request: Request):
    with database(request) as db:
        user_id = current_user(request, db).id
        row = save_fitting(db, user_id, body, owned_row(db, Fitting, user_id, fitting_id))
        db.commit()
        return read_state(db, row)


@router.delete("/fittings/{fitting_id}", status_code=204)
def delete_fitting(fitting_id: str, request: Request):
    with database(request) as db:
        user_id = current_user(request, db).id
        db.delete(owned_row(db, Fitting, user_id, fitting_id))
        prune_mannequins(db, user_id)
        db.commit()


@router.post("/outfits", status_code=201)
def create_outfit(body: OutfitInput, request: Request):
    with database(request) as db:
        row = save_outfit(db, current_user(request, db).id, body)
        db.commit()
        return read_state(db, row)


@router.get("/outfits")
def list_outfits(request: Request):
    with database(request) as db:
        user_id = current_user(request, db).id
        return [
            read_state(db, row)
            for row in db.scalars(
                select(Outfit).where(Outfit.user_id == user_id).order_by(Outfit.created_at.desc())
            )
        ]


@router.get("/outfits/{outfit_id}")
def get_outfit(outfit_id: str, request: Request):
    with database(request) as db:
        return read_state(db, owned_row(db, Outfit, current_user(request, db).id, outfit_id))


@router.delete("/outfits/{outfit_id}", status_code=204)
def delete_outfit(outfit_id: str, request: Request):
    with database(request) as db:
        user_id = current_user(request, db).id
        db.delete(owned_row(db, Outfit, user_id, outfit_id))
        prune_mannequins(db, user_id)
        db.commit()
