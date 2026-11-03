import base64
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_garments import account, create, payload

from app.core.config import Settings
from app.main import create_app
from app.models import Asset, Garment, GenerationJob, RightsEvidence, RightsReview
from app.services import auth
from app.services.garment_mesh import TEMPLATES, build_glb, resolve_spec, validate_glb
from app.services.generation import run_once


@pytest.fixture
def client():
    auth._attempts.clear()
    with TestClient(
        create_app(
            Settings(
                _env_file=None, database_url="sqlite:///:memory:", admin_review_key="test-admin-key"
            )
        )
    ) as instance:
        yield instance


def garment(client, headers, kind="티셔츠", category="top"):
    body = payload()
    body["info"].update(garment_type=kind, category=category, color="파랑", neckline="브이넥")
    body["original_image_retention"] = "temporary"
    result = create(client, headers, body)
    assert result.status_code == 201, result.text
    return result.json()


def queue(client, headers, item):
    return client.post(f"/api/v1/garments/{item['id']}/generate-3d", headers=headers, json={})


def status(client, headers, item):
    return client.get(f"/api/v1/garments/{item['id']}/generation-status", headers=headers).json()


@pytest.mark.parametrize("kind", list(TEMPLATES))
def test_templates_generate_real_private_glb_and_reload(client, tmp_path, kind):
    alice, bob = account(client, "creator"), account(client, "viewer")
    item = garment(client, alice, kind, TEMPLATES[kind][0])
    queued = queue(client, alice, item)
    assert queued.status_code == 202, queued.text
    assert queued.json()["selected_mode"] == "A"
    assert queued.json()["generation_status"] == "queued"
    assert queue(client, alice, item).status_code == 409
    assert client.get(f"/api/v1/garments/{item['id']}/model", headers=alice).status_code == 404
    assert run_once(client.app.state.session_factory)
    complete = status(client, alice, item)
    assert complete["generation_status"] == "completed", complete
    assert complete["model_ready"]
    metadata = complete["model_metadata"]
    assert metadata["coordinate_system"] == "y_up_z_front"
    assert metadata["unit"] == "meter"
    assert metadata["triangle_count"] > 100
    assert metadata["back_geometry"] == "estimated"
    assert metadata["physical_simulation"] is False
    assert metadata["category"] == TEMPLATES[kind][0]
    uri = f"/api/v1/garments/{item['id']}/model"
    for path in (
        uri,
        uri.replace("/model", "/generation-status"),
        uri.replace("/model", "/rights-status"),
    ):
        assert client.get(path, headers=bob).status_code == 404
        assert client.get(path).status_code == 401
    assert client.delete(uri, headers=bob).status_code == 404
    assert queue(client, bob, item).status_code == 404
    response = client.get(uri, headers=alice)
    assert response.status_code == 200
    assert response.headers["content-type"] == "model/gltf-binary"
    assert response.headers["cache-control"] == "no-store"
    path = tmp_path / "garment.glb"
    path.write_bytes(response.content)
    doc = validate_glb(path.read_bytes())
    assert "textures" not in doc and "images" not in doc
    assert doc["nodes"][0]["extras"] == metadata
    assert len(doc["materials"]) == 1
    assert doc["materials"][0]["pbrMetallicRoughness"]["baseColorFactor"][:3] != [1, 1, 1]
    assert doc["buffers"][0].get("uri") is None
    assert client.delete(uri, headers=alice).status_code == 204
    assert client.get(uri, headers=alice).status_code == 404
    assert not status(client, alice, item)["model_ready"]
    with client.app.state.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Asset)) == 0
    assert queue(client, alice, item).status_code == 202
    assert run_once(client.app.state.session_factory)


def test_unconfirmed_photo_and_status_forgery_are_blocked(client):
    headers = account(client, "photo")
    item = garment(client, headers)
    with client.app.state.session_factory() as db:
        db.get(Garment, item["id"]).photo_rights_status = "unverified"
        db.commit()
    assert queue(client, headers, item).status_code == 403
    uri = f"/api/v1/garments/{item['id']}/photo-rights-confirmation"
    assert client.post(uri, headers=headers, json={}).status_code == 400
    confirmed = {**headers, "X-Upload-Rights": "confirmed"}
    assert (
        client.post(uri, headers=confirmed, json={"photo_rights_status": "verified"}).status_code
        == 400
    )
    result = client.post(uri, headers=confirmed, json={})
    assert result.json()["photo_rights_status"] == "confirmed"
    assert result.json()["selected_mode"] == "A"
    assert queue(client, headers, item).status_code == 202


def evidence_and_review(client, headers, item, detailed="verified"):
    data = base64.b64decode(payload()["images"]["front"]["data"])
    evidence_uri = f"/api/v1/garments/{item['id']}/rights-evidence"
    evidence = client.post(
        evidence_uri,
        headers={**headers, "Content-Type": "image/png", "X-Evidence-Storage-Consent": "confirmed"},
        content=data,
    )
    assert evidence.status_code == 201, evidence.text
    evidence_id = evidence.json()["id"]
    body = {
        "photo_rights_status": "verified",
        "detailed_rights_status": detailed,
        "output_rights_status": detailed,
        "evidence_id": evidence_id,
        "notes": "권리자 이용허락 문서의 세 범위와 대상을 담당자가 확인함",
        "rights_version": status(client, headers, item)["rights_version"],
    }
    return evidence_id, body


def test_only_admin_with_actual_evidence_can_verify_three_rights_and_choose_b(client):
    headers = account(client, "rights")
    item = garment(client, headers)
    evidence_id, body = evidence_and_review(client, headers, item)
    uri = f"/api/v1/admin/garments/{item['id']}/rights-review"
    admin = {"X-Admin-Review-Key": "test-admin-key"}
    assert client.patch(uri, headers=headers, json=body).status_code == 403
    assert client.patch(uri, headers=admin, json={**body, "evidence_id": None}).status_code == 400
    assert (
        client.get(f"/api/v1/admin/rights-evidence/{evidence_id}", headers=headers).status_code
        == 403
    )
    doc = client.get(f"/api/v1/admin/rights-evidence/{evidence_id}", headers=admin)
    assert doc.status_code == 200 and "attachment" in doc.headers["content-disposition"]
    approved = client.patch(uri, headers=admin, json=body)
    assert approved.status_code == 200, approved.text
    assert approved.json()["selected_mode"] == "B"
    assert not approved.json()["b_available"]
    assert queue(client, headers, item).status_code == 503
    assert client.patch(uri, headers=admin, json=body).status_code == 409
    body.update(
        detailed_rights_status="unverified",
        output_rights_status="unverified",
        rights_version=approved.json()["rights_version"],
    )
    partial = client.patch(uri, headers=admin, json=body)
    assert partial.json()["selected_mode"] == "A"
    assert queue(client, headers, item).status_code == 202
    assert run_once(client.app.state.session_factory)
    history = client.get(uri.replace("rights-review", "rights-reviews"), headers=admin).json()
    assert len(history) == 2


def test_failure_retry_and_expired_worker_recovery(client):
    headers = account(client, "retry")
    item = garment(client, headers)
    assert queue(client, headers, item).status_code == 202

    def fail(_):
        raise RuntimeError("비공개 내부 오류")

    assert run_once(client.app.state.session_factory, generator=fail)
    result = status(client, headers, item)
    assert result["generation_status"] == "failed"
    assert result["generation_error"] == "GENERATION_FAILED"
    assert "비공개" not in str(result)
    assert queue(client, headers, item).status_code == 202
    with client.app.state.session_factory() as db:
        job = db.get(GenerationJob, status(client, headers, item)["job_id"])
        job.status, job.lease_until, job.attempts = "processing", time.time() - 10, 1
        db.commit()
    assert run_once(client.app.state.session_factory)
    assert status(client, headers, item)["generation_status"] == "completed"
    assert not run_once(client.app.state.session_factory)


@pytest.mark.parametrize("action", ["report", "withdraw", "model_delete", "garment_delete", "edit"])
def test_late_worker_cannot_restore_revoked_or_deleted_results(client, action):
    headers = account(client, "cancel")
    item = garment(client, headers)
    assert queue(client, headers, item).status_code == 202
    uri = f"/api/v1/garments/{item['id']}"

    def interrupted(spec):
        if action == "report":
            assert (
                client.post(
                    "/api/v1/reports",
                    headers=headers,
                    json={"garment_id": item["id"], "reason": "권리 침해 신고 확인 요청"},
                ).status_code
                == 201
            )
        elif action == "withdraw":
            assert (
                client.post(f"{uri}/rights-withdraw", headers=headers, json={}).status_code == 204
            )
        elif action == "model_delete":
            assert client.delete(f"{uri}/model", headers=headers).status_code == 204
        elif action == "garment_delete":
            assert client.delete(uri, headers=headers).status_code == 204
        else:
            assert (
                client.patch(
                    uri,
                    headers=headers,
                    json={"info": {**item["info"], "color": "red"}, "revision": item["revision"]},
                ).status_code
                == 200
            )
        return build_glb(spec)

    assert run_once(client.app.state.session_factory, generator=interrupted)
    assert client.get(f"{uri}/model", headers=headers).status_code == 404
    with client.app.state.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Asset)) == 0
    if action in {"report", "withdraw"}:
        assert queue(client, headers, item).status_code == 403
        assert (
            client.post(
                f"{uri}/photo-rights-confirmation",
                headers={**headers, "X-Upload-Rights": "confirmed"},
                json={},
            ).status_code
            == 403
        )


def test_dimensions_and_unsupported_types_are_not_fabricated(client):
    headers = account(client, "dimensions")
    item = garment(client, headers, "후드티")
    assert queue(client, headers, item).status_code == 422
    info = {
        "garment_type": "티셔츠",
        "category": "top",
        "measurements": [
            {
                "label": "총장",
                "value": 80,
                "unit": "cm",
                "kind": "length",
                "target": "garment",
                "source": "user_entered",
            }
        ],
    }
    spec = resolve_spec(info, {"back": {"primary_color": "red"}})
    assert spec["dimensions"]["length"] == {"value": 0.8, "source": "user_entered"}
    assert spec["color_source"] == "analysis_back"
    assert spec["back_observed"]
    assert spec["dimensions"]["depth"]["source"] == "estimated"
    info["measurements"][0]["target"] = "body"
    assert resolve_spec(info, {})["dimensions"]["length"]["source"] == "estimated"


def test_queue_survives_api_restart(tmp_path):
    auth._attempts.clear()
    settings = Settings(
        _env_file=None, database_url=f"sqlite:///{(tmp_path / 'durable.db').as_posix()}"
    )
    with TestClient(create_app(settings)) as first:
        headers = account(first, "restart")
        item = garment(first, headers)
        assert queue(first, headers, item).status_code == 202
    with TestClient(create_app(settings)) as second:
        assert status(second, headers, item)["generation_status"] == "queued"
        assert run_once(second.app.state.session_factory)
        assert status(second, headers, item)["generation_status"] == "completed"
        deleted = second.request(
            "DELETE",
            "/api/v1/auth/account",
            headers=headers,
            json={"username": "restart", "password": "correct-horse-battery"},
        )
        assert deleted.status_code == 204
        with second.app.state.session_factory() as db:
            for model in (Asset, GenerationJob, RightsEvidence, RightsReview):
                assert db.scalar(select(func.count()).select_from(model)) == 0


def test_actual_evidence_review_and_model_are_removed_on_account_deletion(client):
    headers = account(client, "evidence_owner")
    bob = account(client, "evidence_outsider")
    item = garment(client, headers)
    evidence_id, decision = evidence_and_review(client, headers, item, detailed="unverified")
    other_item = garment(client, bob)
    assert (
        client.post(
            f"/api/v1/garments/{other_item['id']}/rights-review",
            headers=bob,
            json={
                "license_reference": "타인 증빙 위조 참조",
                "revision": 1,
                "evidence_id": evidence_id,
            },
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/v1/admin/garments/{item['id']}/rights-review",
            headers={"X-Admin-Review-Key": "test-admin-key"},
            json=decision,
        ).status_code
        == 200
    )
    assert queue(client, headers, item).status_code == 202
    assert run_once(client.app.state.session_factory)
    with client.app.state.session_factory() as db:
        model_id = db.get(Garment, item["id"]).model_3d_asset_id
        assert db.scalar(select(func.count()).select_from(RightsEvidence)) == 1
        assert db.scalar(select(func.count()).select_from(RightsReview)) == 1
    assert client.get(f"/api/v1/assets/{model_id}", headers=bob).status_code == 404
    assert client.get(f"/api/v1/assets/{model_id}", headers=headers).status_code == 200
    deleted = client.request(
        "DELETE",
        "/api/v1/auth/account",
        headers=headers,
        json={"username": "evidence_owner", "password": "correct-horse-battery"},
    )
    assert deleted.status_code == 204
    with client.app.state.session_factory() as db:
        for model in (Asset, GenerationJob, RightsEvidence, RightsReview):
            assert db.scalar(select(func.count()).select_from(model)) == 0


def test_analysis_report_does_not_suspend_rights_and_bad_glb_fails(client):
    headers = account(client, "analysis_report")
    item = garment(client, headers)
    assert (
        client.post(
            "/api/v1/reports",
            headers=headers,
            json={
                "garment_id": item["id"],
                "reason": "색상 분석 결과 확인 요청",
                "kind": "analysis",
            },
        ).status_code
        == 201
    )
    assert queue(client, headers, item).status_code == 202
    assert run_once(client.app.state.session_factory, generator=lambda _: (b"not-a-glb", {}))
    assert status(client, headers, item)["generation_status"] == "failed"
    assert status(client, headers, item)["selected_mode"] == "A"
    assert queue(client, headers, item).status_code == 202
    assert run_once(client.app.state.session_factory)
    uri = f"/api/v1/garments/{item['id']}"
    asset_id = client.get(uri, headers=headers).json()["model_3d_asset_id"]
    assert client.post(f"{uri}/rights-withdraw", headers=headers, json={}).status_code == 204
    assert client.get(f"/api/v1/assets/{asset_id}", headers=headers).status_code == 404
    assert status(client, headers, item)["stage"] == "cancelled"
