import base64
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import func, select

from app.core.config import Settings
from app.main import create_app
from app.models import Asset, Garment, Report, User
from app.services import auth
from app.services.ocr_parser import parse_ocr


@pytest.fixture
def client():
    auth._attempts.clear()
    with TestClient(
        create_app(
            Settings(
                _env_file=None, database_url="sqlite:///:memory:", admin_review_key="test-admin-key"
            )
        )
    ) as client:
        yield client


def account(client, username):
    response = client.post(
        "/api/v1/auth/register", json={"username": username, "password": "correct-horse-battery"}
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


def payload():
    stream = BytesIO()
    Image.new("RGB", (120, 160), "red").save(stream, "PNG")
    return {
        "info": {"name": "내 티셔츠", "category": "top"},
        "analysis": {"front": {"garment_type": "unknown"}},
        "images": {
            "front": {
                "content_type": "image/png",
                "data": base64.b64encode(stream.getvalue()).decode(),
            }
        },
    }


def create(client, headers, body=None):
    return client.post(
        "/api/v1/garments",
        headers={**headers, "X-Upload-Rights": "confirmed", "X-Image-Storage-Consent": "confirmed"},
        json=body or payload(),
    )


def test_crud_ownership_assets_revision_and_cascade(client):
    alice, bob = account(client, "alice"), account(client, "bob")
    response = create(client, alice)
    assert response.status_code == 201, response.text
    item = response.json()
    uri = f"/api/v1/garments/{item['id']}"
    asset = f"/api/v1/assets/{item['assets']['front']['id']}"
    assert client.get("/api/v1/garments", headers=bob).json() == []
    for method, path, data in [
        ("get", uri, None),
        ("get", asset, None),
        ("delete", uri, None),
        ("patch", uri, {"info": item["info"], "revision": 1}),
    ]:
        result = getattr(client, method)(path, headers=bob, **({"json": data} if data else {}))
        assert result.status_code == 404
    assert client.get(asset).status_code == 401
    image = client.get(asset, headers=alice)
    assert image.status_code == 200
    assert image.headers["cache-control"] == "no-store"
    assert Image.open(BytesIO(image.content)).size == (120, 160)
    corrected = {
        **item["info"],
        "name": "수정한 옷",
        "measurements": [
            {"label": "가슴단면", "value": 50, "unit": "cm", "kind": "flat", "target": "garment"}
        ],
    }
    update = client.patch(uri, headers=alice, json={"info": corrected, "revision": 1})
    assert update.status_code == 200, update.text
    assert update.json()["revision"] == 2
    assert update.json()["analysis"] == item["analysis"]
    assert (
        client.patch(uri, headers=alice, json={"info": corrected, "revision": 1}).status_code == 409
    )
    assert client.get(uri, headers=alice).json()["info"]["name"] == "수정한 옷"
    assert client.delete(uri, headers=alice).status_code == 204
    assert client.get(asset, headers=alice).status_code == 404
    with client.app.state.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Asset)) == 0
        assert db.scalar(select(func.count()).select_from(Garment)) == 0


def test_file_validation_and_required_front(client):
    headers = account(client, "files")
    body = payload()
    assert client.post("/api/v1/garments", headers=headers, json=body).status_code == 400
    body["images"] = {}
    assert create(client, headers, body).status_code == 400
    body = payload()
    body["images"]["front"]["data"] = base64.b64encode(b"broken").decode()
    assert create(client, headers, body).status_code == 400
    body = payload()
    body["images"]["front"]["content_type"] = "image/jpeg"
    assert create(client, headers, body).status_code == 415
    body = payload()
    body["images"]["front"]["data"] = "!invalid!"
    assert create(client, headers, body).status_code == 400


def test_login_logout_delete_account_and_reports(client):
    headers = account(client, "owner")
    item = create(client, headers).json()
    report = client.post(
        "/api/v1/reports",
        headers=headers,
        json={"garment_id": item["id"], "reason": "원본 이미지의 권리 검토 요청"},
    ).json()
    assert client.get("/api/v1/admin/reports").status_code == 403
    assert (
        client.patch(
            f"/api/v1/admin/reports/{report['id']}",
            headers={"X-Admin-Review-Key": "test-admin-key"},
            json={"status": "reviewing"},
        ).status_code
        == 200
    )
    assert client.get("/api/v1/reports", headers=headers).json()[0]["status"] == "reviewing"
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/garments", headers=headers).status_code == 401
    credentials = {"username": "owner", "password": "correct-horse-battery"}
    login = client.post("/api/v1/auth/login", json=credentials)
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['token']}"}
    assert client.get("/api/v1/garments", headers=headers).json()[0]["id"] == item["id"]
    assert (
        client.request(
            "DELETE",
            "/api/v1/auth/account",
            headers=headers,
            json={**credentials, "password": "incorrect-password"},
        ).status_code
        == 401
    )
    assert (
        client.request(
            "DELETE", "/api/v1/auth/account", headers=headers, json=credentials
        ).status_code
        == 204
    )
    with client.app.state.session_factory() as db:
        for model in (User, Garment, Asset, Report):
            assert db.scalar(select(func.count()).select_from(model)) == 0


def test_analysis_requires_auth_consent_and_valid_image(client):
    assert client.post("/api/v1/garments/analyze", content=b"test").status_code == 401
    headers = account(client, "analysis")
    assert (
        client.post("/api/v1/garments/analyze", headers=headers, content=b"test").status_code == 400
    )
    result = client.post(
        "/api/v1/garments/ocr",
        headers={
            **headers,
            "Content-Type": "image/png",
            "X-Upload-Rights": "confirmed",
            "X-Image-Processing-Consent": "confirmed",
        },
        content=b"test",
    )
    assert result.status_code == 400


def test_ocr_does_not_invent_units_or_table_correspondence():
    result = parse_ocr(
        "S M L\n가슴단면 40 45 50 cm\n어깨너비 40\n실측 총장 70 cm\n신체 권장 허리둘레 80 cm",
        "size",
    )
    assert len(result["measurements"]) == 3
    first = result["measurements"][0]
    assert (
        first["unit"] == "unknown" and first["target"] == "unknown" and first["kind"] == "unknown"
    )
    assert result["measurements"][1]["kind"] == "length"
    assert result["measurements"][2]["target"] == "body"
    material = parse_ocr("면 65%\n폴리에스터 30%", "material")
    assert len(material["composition"]) == 2 and material["warnings"]
    assert parse_ocr("", "material")["composition"] == []


def test_missing_model_does_not_return_fake_analysis(client, monkeypatch):
    headers = account(client, "missing_model")
    monkeypatch.setattr(client.app.state.garment_ai, "status", lambda: {"classification": False})
    image = base64.b64decode(payload()["images"]["front"]["data"])
    result = client.post(
        "/api/v1/garments/analyze",
        content=image,
        headers={
            **headers,
            "Content-Type": "image/png",
            "X-Upload-Rights": "confirmed",
            "X-Image-Processing-Consent": "confirmed",
        },
    )
    assert result.status_code == 503
    assert result.json()["error"]["code"] == "MODEL_UNAVAILABLE"
    assert client.get("/api/v1/garments", headers=headers).json() == []
