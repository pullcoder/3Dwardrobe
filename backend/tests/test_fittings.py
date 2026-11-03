import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_garments import account
from test_generation import garment, queue

from app.core.config import Settings
from app.main import create_app
from app.models import Fitting, Garment, GenerationJob, Outfit, SavedMannequin
from app.services import auth
from app.services.generation import run_once


@pytest.fixture
def client():
    auth._attempts.clear()
    with TestClient(
        create_app(Settings(_env_file=None, database_url="sqlite:///:memory:"))
    ) as instance:
        yield instance


def fitted_input(client, headers):
    slots = {}
    for kind, category in (("티셔츠", "top"), ("청바지", "bottom"), ("재킷", "outer")):
        item = garment(client, headers, kind, category)
        assert queue(client, headers, item).status_code == 202
        assert run_once(client.app.state.session_factory)
        slots[category] = item["id"]
    return {
        "mannequin": {
            "mode": "manual",
            "values": {
                "height": 175,
                "shoulder": 42,
                "chest": 94,
                "waist": 78,
                "hip": 98,
                "arm": 56,
                "leg": 81,
            },
            "origins": {"height": "user_entered"},
        },
        "body_storage_consent": True,
        "slots": slots,
        "adjustments": {"outer": {"clearance": 0.025}, "top": {"chest": 1.04}},
    }


def test_snapshot_replace_remove_outfit_reload_and_immutable_mannequin(client):
    alice = account(client, "fitter")
    body = fitted_input(client, alice)
    result = client.post("/api/v1/fittings", headers=alice, json=body)
    assert result.status_code == 201, result.text
    fitting = result.json()
    assert all(slot["status"] == "available" for slot in fitting["slots"].values())
    assert fitting["mannequin"]["values"]["height"] == 175
    outfit = client.post(
        "/api/v1/outfits", headers=alice, json={"fitting_id": fitting["id"], "name": "세 겹 코디"}
    )
    assert outfit.status_code == 201, outfit.text
    outfit = outfit.json()
    uri = f"/api/v1/fittings/{fitting['id']}"
    body["mannequin"]["values"]["height"] = 180
    body["slots"]["top"] = None
    patched = client.patch(uri, headers=alice, json={**body, "revision": 1})
    assert patched.status_code == 200, patched.text
    patched = patched.json()
    assert patched["slots"]["top"] is None
    assert patched["slots"]["bottom"]["garment_id"] == fitting["slots"]["bottom"]["garment_id"]
    assert patched["mannequin_id"] != fitting["mannequin_id"]
    assert client.patch(uri, headers=alice, json={**body, "revision": 1}).status_code == 409
    reloaded = client.get(f"/api/v1/outfits/{outfit['id']}", headers=alice).json()
    assert reloaded["mannequin"]["values"]["height"] == 175
    assert reloaded["slots"]["top"]["garment_id"] == outfit["slots"]["top"]["garment_id"]
    assert reloaded["adjustments"]["outer"]["clearance"] == 0.025
    assert len(client.get("/api/v1/outfits", headers=alice).json()) == 1
    assert client.delete(f"/api/v1/outfits/{outfit['id']}", headers=alice).status_code == 204
    assert client.get(f"/api/v1/outfits/{outfit['id']}", headers=alice).status_code == 404
    assert client.delete(uri, headers=alice).status_code == 204
    with client.app.state.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(SavedMannequin)) == 0


def test_owner_category_consent_and_injection_boundaries(client):
    alice, bob = account(client, "owner_fit"), account(client, "other_fit")
    body = fitted_input(client, alice)
    assert client.post("/api/v1/fittings", json=body).status_code == 401
    assert client.post("/api/v1/fittings", headers=bob, json=body).status_code == 404
    assert (
        client.post(
            "/api/v1/fittings", headers=alice, json={**body, "body_storage_consent": False}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/fittings", headers=alice, json={**body, "user_id": "forged"}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/fittings", headers=alice, json={**body, "reconstruction_mode": "B"}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/fittings",
            headers=alice,
            json={**body, "mannequin": {**body["mannequin"], "photo": "forbidden"}},
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/fittings", headers=alice, json={**body, "adjustments": {"top": {"chest": 100}}}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/fittings",
            headers=alice,
            json={**body, "slots": {"top": body["slots"]["bottom"]}},
        ).status_code
        == 422
    )
    saved = client.post("/api/v1/fittings", headers=alice, json=body).json()
    outfit = client.post(
        "/api/v1/outfits", headers=alice, json={"fitting_id": saved["id"], "name": "비공개 코디"}
    ).json()
    for path in (f"/api/v1/fittings/{saved['id']}", f"/api/v1/outfits/{outfit['id']}"):
        assert client.get(path, headers=bob).status_code == 404
        assert client.delete(path, headers=bob).status_code == 404
    assert (
        client.patch(
            f"/api/v1/fittings/{saved['id']}", headers=bob, json={**body, "revision": 1}
        ).status_code
        == 404
    )
    assert client.get("/api/v1/outfits", headers=bob).json() == []
    assert (
        client.post(
            "/api/v1/outfits", headers=bob, json={"fitting_id": saved["id"], "name": "타인 코디"}
        ).status_code
        == 404
    )


@pytest.mark.parametrize(
    "reason", ["garment_deleted", "model_deleted", "rights_withdrawn", "regenerated"]
)
def test_missing_or_invalid_models_are_reported_without_breaking_outfits(client, reason):
    headers = account(client, "missing_fit")
    body = fitted_input(client, headers)
    saved = client.post("/api/v1/fittings", headers=headers, json=body).json()
    outfit = client.post(
        "/api/v1/outfits", headers=headers, json={"fitting_id": saved["id"], "name": "보관 코디"}
    ).json()
    uri = f"/api/v1/garments/{body['slots']['top']}"
    if reason == "garment_deleted":
        assert client.delete(uri, headers=headers).status_code == 204
    elif reason == "rights_withdrawn":
        assert client.post(f"{uri}/rights-withdraw", headers=headers, json={}).status_code == 204
    elif reason == "model_deleted":
        assert client.delete(f"{uri}/model", headers=headers).status_code == 204
    else:
        assert client.post(f"{uri}/generate-3d", headers=headers, json={}).status_code == 202
        assert run_once(client.app.state.session_factory)
    response = client.get(f"/api/v1/outfits/{outfit['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["slots"]["top"]["status"] == "unavailable"
    assert response.json()["slots"]["bottom"]["status"] == "available"
    assert response.json()["warnings"]
    assert (
        client.post(
            "/api/v1/outfits",
            headers=headers,
            json={"fitting_id": saved["id"], "name": "다시 저장"},
        ).status_code
        == 409
    )


def test_approved_b_uses_same_contract_but_revocation_cannot_fall_back_to_a(client):
    headers = account(client, "b_contract")
    body = fitted_input(client, headers)
    garment_id = body["slots"]["top"]
    with client.app.state.session_factory() as db:
        row = db.get(Garment, garment_id)
        row.reconstruction_mode = "B"
        row.photo_rights_status = row.detailed_rights_status = row.output_rights_status = "verified"
        job = db.get(GenerationJob, row.generation_job_id)
        job.result_metadata = {**job.result_metadata, "mode": "B"}
        db.commit()
    resource = client.get(f"/api/v1/fittings/resources/{garment_id}", headers=headers)
    assert resource.status_code == 200
    assert resource.json()["reconstruction_mode"] == "B"
    assert client.post("/api/v1/fittings", headers=headers, json=body).status_code == 201
    with client.app.state.session_factory() as db:
        db.get(Garment, garment_id).detailed_rights_status = "unverified"
        db.commit()
    assert (
        client.get(f"/api/v1/fittings/resources/{garment_id}", headers=headers).status_code == 404
    )
    assert client.get(f"/api/v1/garments/{garment_id}/model", headers=headers).status_code == 404


def test_account_deletion_cascades_private_body_fitting_and_outfits(client):
    headers = account(client, "delete_fit")
    body = fitted_input(client, headers)
    saved = client.post("/api/v1/fittings", headers=headers, json=body).json()
    assert (
        client.post(
            "/api/v1/outfits",
            headers=headers,
            json={"fitting_id": saved["id"], "name": "삭제 코디"},
        ).status_code
        == 201
    )
    deleted = client.request(
        "DELETE",
        "/api/v1/auth/account",
        headers=headers,
        json={"username": "delete_fit", "password": "correct-horse-battery"},
    )
    assert deleted.status_code == 204
    with client.app.state.session_factory() as db:
        for model in (SavedMannequin, Fitting, Outfit):
            assert db.scalar(select(func.count()).select_from(model)) == 0
