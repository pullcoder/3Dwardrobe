import json
import struct
from io import BytesIO

import pytest
from PIL import Image, ImageDraw
from sqlalchemy import select
from test_garments import account
from test_generation import client, garment  # noqa: F401

from app.ai.generated_mesh import inspect_glb
from app.ai.generation_adapters import Trellis2Adapter, TripoSRAdapter
from app.ai.generation_input import prepare_input
from app.core.errors import AppError
from app.models import GenerationJob
from app.services.garment_mesh import build_glb, resolve_spec
from app.services.generation import run_once
from app.services.generation_engines import engine_catalog, fitting_gate


def cutout():
    image = Image.new("RGBA", (100, 120))
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 10, 80, 110), fill="red")
    draw.rectangle((30, 30, 50, 50), fill="blue")
    buffer = BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def test_environment_and_license_gates_are_independent():
    low = engine_catalog({"system": "Windows", "gpus": [{"memory_mib": 2048}]})
    high = engine_catalog({"system": "Linux", "gpus": [{"memory_mib": 81920}]})
    assert low[0]["available"]
    assert all(not item["available"] for item in low[1:] + high[1:])
    assert any("Linux" in reason for reason in low[2]["reasons"])
    assert high[2]["license_status"] == "blocked_noncommercial_dependencies"
    assert len(high[1]["reasons"]) < len(low[1]["reasons"])


@pytest.mark.parametrize("engine", ["triposr", "trellis2"])
def test_unavailable_engine_preserves_existing_model_and_job(client, engine):  # noqa: F811
    headers = account(client, "engine-user")
    item = garment(client, headers)
    base = f"/api/v1/garments/{item['id']}"
    assert client.post(base + "/generate-3d", headers=headers, json={}).status_code == 202
    assert run_once(client.app.state.session_factory)
    previous = client.get(base + "/model", headers=headers).content
    response = client.post(base + "/generate-3d", headers=headers, json={"engine": engine})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ENGINE_UNAVAILABLE"
    with client.app.state.session_factory() as db:
        jobs = db.scalars(select(GenerationJob)).all()
        assert len(jobs) == 1 and jobs[0].status == "completed"
    assert client.get(base + "/model", headers=headers).content == previous
    status = client.get(base + "/generation-status", headers=headers).json()
    assert status["selected_engine"] == "template"
    assert len(status["engines"]) == 3
    assert client.post(base + "/generate-3d", headers=headers, json={}).status_code == 202


def test_a_input_discards_source_pixels_and_preserves_aspect():
    a, report = prepare_input(cutout(), "image/png", "A")
    b, _ = prepare_input(cutout(), "image/png", "B")
    assert a.size == b.size == (896, 896)
    assert a.getchannel("A").tobytes() == b.getchannel("A").tobytes()
    assert set(a.get_flattened_data()) != set(b.get_flattened_data())
    assert all(r == g == blue for r, g, blue, alpha in a.get_flattened_data() if alpha == 255)
    assert report["aspect_ratio_preserved"]
    assert report["texture_policy"] == "silhouette_only"


def test_opaque_input_does_not_silently_skip_segmentation():
    buffer = BytesIO()
    Image.new("RGB", (100, 100), "red").save(buffer, "PNG")
    with pytest.raises(AppError, match="3단계"):
        prepare_input(buffer.getvalue(), "image/png", "A")


def test_glb_reload_and_fitting_are_separate_checks():
    content, metadata = build_glb(resolve_spec({"garment_type": "티셔츠", "category": "top"}, {}))
    report = inspect_glb(content)
    assert report["triangle_count"] > 100 and report["glb_reloaded"]
    assert report["wearable"] is False
    with pytest.raises(ValueError):
        inspect_glb(content[:-5])
    fitting_gate(metadata)
    for engine in ("triposr", "trellis2"):
        with pytest.raises(AppError, match="착용|AI 메시"):
            fitting_gate({**metadata, "engine": engine, "generation_kind": "ai"})


def test_glb_accepts_uint32_faces_and_rejects_external_or_negative_references():
    positions = struct.pack("<12f", 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1)
    indices = struct.pack("<12I", 0, 2, 1, 0, 1, 3, 0, 3, 2, 1, 2, 3)
    binary = positions + indices
    doc = {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(positions)},
            {"buffer": 0, "byteOffset": len(positions), "byteLength": len(indices)},
        ],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": 4, "type": "VEC3"},
            {"bufferView": 1, "componentType": 5125, "count": 12, "type": "SCALAR"},
        ],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
    }

    def encode():
        chunk = json.dumps(doc).encode()
        chunk += b" " * (-len(chunk) % 4)
        return (
            struct.pack("<4sII", b"glTF", 2, 28 + len(chunk) + len(binary))
            + struct.pack("<I4s", len(chunk), b"JSON")
            + chunk
            + struct.pack("<I4s", len(binary), b"BIN\0")
            + binary
        )

    assert inspect_glb(encode())["triangle_count"] == 4
    doc["buffers"][0]["uri"] = "https://example.invalid/private.bin"
    with pytest.raises(ValueError, match="external"):
        inspect_glb(encode())
    del doc["buffers"][0]["uri"]
    doc["meshes"][0]["primitives"][0]["attributes"]["POSITION"] = -1
    with pytest.raises(ValueError, match="reference"):
        inspect_glb(encode())


@pytest.mark.parametrize("adapter", [TripoSRAdapter, Trellis2Adapter])
def test_disabled_adapter_never_imports_or_downloads_weights(adapter, tmp_path):
    with pytest.raises(AppError):
        adapter().generate(None, tmp_path, tmp_path / "output.glb")
    assert not list(tmp_path.iterdir())


def test_fitting_endpoint_blocks_ai_even_with_forged_template_contract(client):  # noqa: F811
    headers = account(client, "ai-fitting")
    item = garment(client, headers)
    base = f"/api/v1/garments/{item['id']}"
    assert client.post(base + "/generate-3d", headers=headers, json={}).status_code == 202
    assert run_once(client.app.state.session_factory)
    with client.app.state.session_factory() as db:
        job = db.scalar(select(GenerationJob))
        job.result_metadata = {**job.result_metadata, "generation_kind": "ai", "engine": "triposr"}
        db.commit()
    response = client.get(f"/api/v1/fittings/resources/{item['id']}", headers=headers)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "GARMENT_STRUCTURE_UNVERIFIED"
    assert client.get(base + "/model", headers=headers).status_code == 200
