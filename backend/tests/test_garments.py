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
        "original_image_retention": "consented_storage",
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


def test_temporary_default_discards_all_images_and_keeps_policy(client):
    headers = account(client, "temporary")
    body = payload()
    body.pop("original_image_retention")
    body["source_type"] = "self_photographed"
    body["images"]["cutout_front"] = body["images"]["front"]
    response = create(client, headers, body)
    assert response.status_code == 201, response.text
    item = response.json()
    assert item["reconstruction_mode"] == "A"
    assert item["rights_status"] == "unverified"
    assert item["source_type"] == "self_photographed"
    assert item["original_image_retention"] == "temporary"
    assert item["assets"] == {}
    assert item["model_visibility"] == "private"
    assert item["generated_model_path"] is None
    assert item["rights_reviewed_at"] is None
    assert item["license_reference"] is None
    with client.app.state.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Asset)) == 0
    assert client.get(f"/api/v1/garments/{item['id']}", headers=headers).json() == item


@pytest.mark.parametrize(
    "field,value",
    [
        ("reconstruction_mode", "B"),
        ("rights_status", "approved"),
        ("model_visibility", "public"),
        ("generated_model_path", "/fake.glb"),
        ("rights_reviewed_at", "2026-11-03"),
        ("license_reference", "self-approved"),
    ],
)
def test_client_cannot_grant_rights_or_enable_b(client, field, value):
    headers = account(client, "forged")
    body = payload()
    body[field] = value
    assert create(client, headers, body).status_code == 400
    item = create(client, headers).json()
    assert (
        client.patch(
            f"/api/v1/garments/{item['id']}",
            headers=headers,
            json={"info": item["info"], "revision": 1, field: value},
        ).status_code
        == 400
    )


def test_review_reference_is_pending_not_approval_and_requires_ownership(client):
    alice, bob = account(client, "reviewer"), account(client, "outsider")
    item = create(client, alice).json()
    path = f"/api/v1/garments/{item['id']}/rights-review"
    body = {"license_reference": "권리자 이용허락 문서 DOC-123", "revision": 1}
    assert client.post(path, json=body).status_code == 401
    assert client.post(path, headers=bob, json=body).status_code == 404
    assert (
        client.post(path, headers=alice, json={**body, "license_reference": "   "}).status_code
        == 400
    )
    assert (
        client.post(path, headers=alice, json={**body, "rights_status": "approved"}).status_code
        == 400
    )
    assert client.post(path, headers=alice, json={**body, "revision": 2}).status_code == 409
    response = client.post(path, headers=alice, json=body)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["rights_status"] == "pending"
    assert result["reconstruction_mode"] == "A"
    assert result["rights_reviewed_at"] is None
    assert result["license_reference"] == body["license_reference"]
    assert result["revision"] == 2
    assert client.post(path, headers=alice, json={**body, "revision": 2}).status_code == 409
    updated = client.patch(
        f"/api/v1/garments/{item['id']}",
        headers=alice,
        json={"info": {**item["info"], "name": "수정한 옷"}, "revision": 2},
    ).json()
    assert updated["rights_status"] == "pending"
    assert updated["reconstruction_mode"] == "A"


def test_policy_migration_preserves_existing_consent_and_data(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect, text

    url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config("alembic.ini")
    command.upgrade(config, "75730b3d1871")
    engine = create_engine(url)
    with engine.begin() as db:
        db.execute(text("INSERT INTO users VALUES ('owner', 'owner', 'hashed')"))
        db.execute(
            text(
                "INSERT INTO garments "
                "(id,user_id,data,analysis,created_at,revision,model_3d_status) "
                "VALUES ('old','owner','{}','{}','2026-11-03',1,'not_implemented')"
            )
        )
        db.execute(
            text("INSERT INTO garment_assets VALUES ('asset','old','front',X'0102','image/png')")
        )
    command.upgrade(config, "head")
    with engine.connect() as db:
        row = db.execute(text("SELECT * FROM garments")).mappings().one()
        assert row["reconstruction_mode"] == "A"
        assert row["rights_status"] == "unverified"
        assert row["original_image_retention"] == "consented_storage"
        assert row["model_visibility"] == "private"
        assert row["rights_reviewed_at"] is None
        assert db.execute(text("SELECT content FROM garment_assets")).scalar() == b"\x01\x02"
    command.downgrade(config, "75730b3d1871")
    assert "rights_status" not in {
        column["name"] for column in inspect(engine).get_columns("garments")
    }
    command.upgrade(config, "head")
    engine.dispose()
