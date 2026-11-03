"""실제 워커 부재를 숨기지 않고, 실패 단계와 민감 정보 제거를 검증한다."""

import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from test_garments import account
from test_generation import garment, queue, status

from app.core.config import Settings
from app.main import create_app
from app.models import GenerationWorker
from app.services import auth, garment_mesh
from app.services.generation import run_once
from app.services.generation_runtime import heartbeat, worker_status


@pytest.fixture
def client():
    auth._attempts.clear()
    with TestClient(
        create_app(Settings(_env_file=None, database_url="sqlite:///:memory:"))
    ) as instance:
        yield instance


def test_worker_heartbeat_is_bound_to_this_database_and_expires(client):
    headers = account(client, "worker_health")
    item = garment(client, headers)
    assert not status(client, headers, item)["runtime"]["worker_online"]
    worker_id = str(uuid4())
    heartbeat(client.app.state.session_factory, worker_id)
    assert status(client, headers, item)["runtime"]["worker_online"]
    with client.app.state.session_factory() as db:
        db.get(GenerationWorker, worker_id).last_seen = time.time() - 20
        db.commit()
        assert not worker_status(db)["worker_online"]


@pytest.mark.parametrize(
    "stage",
    ["mesh", "exporting", "validating", "asset_storage", "database_update", "database_commit"],
)
def test_failure_stage_and_no_private_exception_text(client, monkeypatch, caplog, stage):
    headers = account(client, "failure_trace")
    item = garment(client, headers)
    assert queue(client, headers, item).status_code == 202
    secret = "private-photo-user-body-details"
    generator = garment_mesh.build_glb
    if stage == "mesh":

        def fail(_):
            raise RuntimeError(secret)

        monkeypatch.setattr(garment_mesh, "make_meshes", fail)
    elif stage == "exporting":
        original = garment_mesh.struct.pack

        def fail_pack(fmt, *values):
            if fmt == "<4sII":
                raise RuntimeError(secret)
            return original(fmt, *values)

        monkeypatch.setattr(garment_mesh.struct, "pack", fail_pack)
    elif stage == "validating":

        def generator(_):
            return b"not-a-GLB", {}
    else:
        fired = False

        def fail_statement(connection, cursor, statement, parameters, context, executemany):
            nonlocal fired
            if stage == "asset_storage":
                matches = statement.startswith("INSERT INTO garment_assets")
            elif stage == "database_update":
                matches = (
                    statement.startswith("UPDATE garments") and "generated_model_path" in statement
                )
            else:
                matches = (
                    statement.startswith("UPDATE generation_jobs")
                    and "result_metadata" in statement
                )
            if matches and not fired:
                fired = True
                raise RuntimeError(secret)

        event.listen(client.app.state.engine, "before_cursor_execute", fail_statement)
    assert run_once(client.app.state.session_factory, generator=generator)
    result = status(client, headers, item)
    assert result["generation_status"] == "failed"
    assert result["failure"]["stage"] == stage
    assert result["failure"]["exception_type"]
    assert secret not in str(result) and secret not in caplog.text
    assert client.get(f"/api/v1/garments/{item['id']}/model", headers=headers).status_code == 404


def test_glb_cannot_be_an_empty_scene():
    import json
    import struct

    document = json.dumps(
        {"buffers": [{"byteLength": 0}], "meshes": [], "nodes": [], "scenes": [], "materials": []}
    ).encode()
    document += b" " * (-len(document) % 4)
    empty = (
        struct.pack("<4sII", b"glTF", 2, len(document) + 28)
        + struct.pack("<I4s", len(document), b"JSON")
        + document
        + struct.pack("<I4s", 0, b"BIN\0")
    )
    with pytest.raises(ValueError, match="empty GLB scene"):
        garment_mesh.validate_glb(empty)


def test_color_and_length_change_actual_mesh_and_material():
    def model(length, color):
        spec = garment_mesh.resolve_spec(
            {
                "category": "top",
                "garment_type": "티셔츠",
                "color": color,
                "measurements": [
                    {
                        "label": "총장",
                        "value": length,
                        "unit": "cm",
                        "kind": "length",
                        "target": "garment",
                        "source": "user_entered",
                    }
                ],
            },
            {},
        )
        content, metadata = garment_mesh.build_glb(spec)
        return garment_mesh.validate_glb(content), metadata

    small, small_meta = model(60, "red")
    large, large_meta = model(85, "blue")
    assert (
        small["materials"][0]["pbrMetallicRoughness"]["baseColorFactor"]
        != large["materials"][0]["pbrMetallicRoughness"]["baseColorFactor"]
    )
    assert (
        large_meta["bounds"]["max"][1] - large_meta["bounds"]["min"][1]
        > small_meta["bounds"]["max"][1] - small_meta["bounds"]["min"][1] + 0.2
    )
