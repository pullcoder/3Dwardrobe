"""자체 제작 사진으로 외곽→기하, A 픽셀 비복제, 제한 B 권한 경계를 검증한다."""

import base64
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from sqlalchemy import func, select
from test_garments import account, create
from test_generation import queue, status

from app.core.config import Settings
from app.core.errors import AppError
from app.main import create_app
from app.models import Asset, Garment, GenerationJob
from app.services import auth
from app.services.garment_mesh import build_glb, resolve_spec, validate_glb
from app.services.generation import run_once
from app.services.pants_materials import generic_check
from app.services.pants_silhouette import analyze_pants


def pants_photo(wide=True, alpha=True):
    mask = Image.new("L", (400, 700))
    polygon = (
        [
            (90, 20),
            (310, 20),
            (335, 220),
            (360, 670),
            (215, 670),
            (200, 335),
            (185, 670),
            (40, 670),
            (65, 220),
        ]
        if wide
        else [
            (90, 20),
            (310, 20),
            (305, 220),
            (280, 670),
            (220, 670),
            (200, 335),
            (180, 670),
            (120, 670),
            (95, 220),
        ]
    )
    ImageDraw.Draw(mask).polygon(polygon, fill=255)
    photo = Image.new("RGBA", mask.size, (130, 130, 140, 255))
    draw = ImageDraw.Draw(photo)
    for x in range(0, 400, 12):
        draw.line((x, 0, x, 700), fill=(240, 240, 245), width=2)
    draw.rectangle((140, 80, 190, 100), fill=(255, 0, 255))
    photo.putalpha(mask)
    if not alpha:
        background = Image.new("RGBA", photo.size, "white")
        background.alpha_composite(photo)
        photo = background.convert("RGB")
    output = BytesIO()
    photo.save(output, format="PNG")
    return output.getvalue()


def info():
    return {
        "name": "자체 제작 와이드 팬츠",
        "garment_type": "슬랙스",
        "category": "bottom",
        "color": "회색",
        "pattern": "체크",
        "fit": "와이드핏",
        "measurements": [],
    }


def photo_body(temporary=False):
    encoded = {"content_type": "image/png", "data": base64.b64encode(pants_photo()).decode()}
    return {
        "info": info(),
        "images": {"front": encoded, "cutout_front": encoded},
        "analysis": {},
        "original_image_retention": "temporary" if temporary else "consented_storage",
    }


@pytest.fixture
def client():
    auth._attempts.clear()
    with TestClient(
        create_app(Settings(_env_file=None, database_url="sqlite:///:memory:"))
    ) as client:
        yield client


@pytest.mark.parametrize("alpha", [True, False])
def test_photo_silhouette_measures_nonconstant_leg_width_and_rise(alpha):
    wide = analyze_pants(pants_photo(True, alpha))
    narrow = analyze_pants(pants_photo(False, alpha))
    assert len(wide["rows"]) == 49 and 0.35 < wide["rise_ratio"] < 0.6
    a = resolve_spec(info(), {"silhouette": wide})
    b = resolve_spec(info(), {"silhouette": narrow})
    assert a["dimensions"]["hem_width"]["value"] > b["dimensions"]["hem_width"]["value"] * 1.5
    assert a["pants"]["observed"] and a["pants"]["fit_inference"] == "wide"
    ca, ma = build_glb(a)
    cb, _ = build_glb(b)
    da, db = validate_glb(ca), validate_glb(cb)
    assert ma["triangle_count"] > 5000
    pa = da["accessors"][da["meshes"][1]["primitives"][0]["attributes"]["POSITION"]]
    pb = db["accessors"][db["meshes"][1]["primitives"][0]["attributes"]["POSITION"]]
    assert pa["max"][0] - pa["min"][0] > pb["max"][0] - pb["min"][0] + 0.05
    assert ma["fitting_contract"] == "stylefit.pants.v2" and ma["back_geometry"] == "estimated"


def test_a_embeds_only_generated_generic_check_not_input_logo():
    spec = resolve_spec(info(), {"silhouette": analyze_pants(pants_photo())})
    spec["_front_png"] = pants_photo()
    content, meta = build_glb(spec)
    doc = validate_glb(content)
    offset = 28 + int.from_bytes(content[12:16], "little")
    view = doc["bufferViews"][doc["images"][0]["bufferView"]]
    png = content[offset + view["byteOffset"] : offset + view["byteOffset"] + view["byteLength"]]
    assert png == generic_check(meta["color"]) and png != pants_photo()
    assert meta["texture_policy"] == "procedural_generic_check"
    assert (
        doc["accessors"][doc["meshes"][0]["primitives"][0]["attributes"]["TEXCOORD_0"]]["type"]
        == "VEC2"
    )


def test_manual_measurements_and_selected_size_override_photo_estimates():
    details = info()
    details["size"] = "M"
    details["measurements"] = [
        {
            "label": "밑단단면",
            "value": 12,
            "unit": "cm",
            "kind": "flat",
            "target": "garment",
            "size": "L",
            "source": "user_entered",
        },
        {
            "label": "밑단단면",
            "value": 280,
            "unit": "mm",
            "kind": "flat",
            "target": "garment",
            "size": "M",
            "source": "user_entered",
        },
    ]
    spec = resolve_spec(details, {"silhouette": analyze_pants(pants_photo())})
    assert spec["dimensions"]["hem_width"] == {"value": 0.28, "source": "user_entered"}


def test_temporary_registration_keeps_numeric_shape_and_never_pixels_or_client_forgery(client):
    headers = account(client, "shape_private")
    body = photo_body(True)
    body["analysis"] = {"silhouette": {"forged": True}}
    created = create(client, headers, body).json()
    assert created["analysis"]["silhouette"]["method"] == "pants_silhouette_v1"
    with client.app.state.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Asset)) == 0
    assert queue(client, headers, created).status_code == 202
    assert run_once(client.app.state.session_factory)
    assert (
        status(client, headers, created)["model_metadata"]["shape_source"]
        == "photo_silhouette_estimate"
    )


def test_silhouette_reupload_owner_rights_revision_and_no_pixel_storage(client):
    alice, bob = account(client, "shape_owner"), account(client, "shape_other")
    item = create(client, alice, photo_body(True)).json()
    uri = f"/api/v1/garments/{item['id']}/silhouette"
    consent = {
        "X-Upload-Rights": "confirmed",
        "X-Image-Processing-Consent": "confirmed",
        "Content-Type": "image/png",
    }
    assert client.post(uri, headers={**bob, **consent}, content=pants_photo()).status_code == 404
    assert client.post(uri, headers=alice, content=pants_photo()).status_code == 400
    result = client.post(uri, headers={**alice, **consent}, content=pants_photo(False))
    assert result.status_code == 200, result.text
    assert result.json()["revision"] == 2
    assert client.get(f"/api/v1/garments/{item['id']}", headers=alice).json()["assets"] == {}


def test_b_front_projection_requires_three_verified_rights_and_actual_source(client):
    headers = account(client, "projection_owner")
    outsider = account(client, "projection_other")
    item = create(client, headers, photo_body()).json()
    assert queue(client, headers, item).status_code == 202
    assert run_once(client.app.state.session_factory)
    assert status(client, headers, item)["model_metadata"]["mode"] == "A"
    with client.app.state.session_factory() as db:
        garment = db.get(Garment, item["id"])
        garment.photo_rights_status = garment.detailed_rights_status = (
            garment.output_rights_status
        ) = "verified"
        db.commit()
    assert queue(client, headers, item).status_code == 202
    with client.app.state.session_factory() as db:
        job = db.get(GenerationJob, status(client, headers, item)["job_id"])
        assert "_front_png" not in job.snapshot
    assert run_once(client.app.state.session_factory)
    state = status(client, headers, item)
    assert state["model_metadata"]["texture_policy"] == "verified_front_projection"
    assert state["model_metadata"]["mode"] == "B"
    assert state["model_metadata"]["back_appearance"] == "generic_estimated"
    uri = f"/api/v1/garments/{item['id']}/model"
    content = client.get(uri, headers=headers).content
    doc = validate_glb(content)
    view = doc["bufferViews"][doc["images"][0]["bufferView"]]
    start = 28 + int.from_bytes(content[12:16], "little") + view["byteOffset"]
    with Image.open(BytesIO(content[start : start + view["byteLength"]])) as atlas:
        pixels = list(atlas.convert("RGB").crop((0, 0, 384, 640)).get_flattened_data())
    assert any(r > 220 and g < 40 and b > 220 for r, g, b in pixels)
    assert (
        client.post(
            f"/api/v1/garments/{item['id']}/generate-3d", headers=headers, json={"mode": "B"}
        ).status_code
        == 400
    )
    assert client.get(uri, headers=outsider).status_code == 404
    assert (
        client.post(
            f"/api/v1/garments/{item['id']}/rights-withdraw", headers=headers, json={}
        ).status_code
        == 204
    )
    assert client.get(uri, headers=headers).status_code == 404
    assert queue(client, headers, item).status_code == 403


def test_unusable_photo_does_not_fabricate_observed_shape():
    output = BytesIO()
    Image.new("RGB", (200, 300), "white").save(output, format="PNG")
    with pytest.raises(AppError):
        analyze_pants(output.getvalue())
    spec = resolve_spec(info(), {})
    assert (
        not spec["pants"]["observed"] and spec["dimensions"]["hem_width"]["source"] == "estimated"
    )


def test_cloth_sections_and_shared_part_normals_preserve_connected_surface():
    from app.services.garment_mesh import make_meshes

    spec = resolve_spec(info(), {"silhouette": analyze_pants(pants_photo())})
    meshes = make_meshes(spec)
    # 밑위의 두 부위가 좌표/음영 모두 연속이어야 한다.
    upper = meshes[0]
    upper_points = {
        tuple(round(v, 6) for v in upper["positions"][i : i + 3]): upper["normals"][i : i + 3]
        for i in range(0, len(upper["positions"]), 3)
    }
    shared = 0
    for mesh in meshes[1:]:
        for i in range(0, len(mesh["positions"]), 3):
            key = tuple(round(v, 6) for v in mesh["positions"][i : i + 3])
            if key in upper_points:
                shared += 1
                assert mesh["normals"][i : i + 3] == pytest.approx(upper_points[key], abs=1e-6)
    assert shared > 100
    # 넓은 천 패널은 원통의 둥근 단면보다 앞면이 납작하다.
    leg = meshes[1]
    center_row = [leg["positions"][i : i + 3] for i in range(32 * 49 * 3, 33 * 49 * 3, 3)]
    assert center_row[12][2] > center_row[24][2] * 0.8
    # 가장자리에는 안쪽으로 접힌 단의 정점이 있어 단순 단면보다 실제 두께가 보인다.
    ys = [leg["positions"][i] for i in range(1, len(leg["positions"]), 3)]
    assert any(0.007 < y < 0.009 for y in ys)


def test_previous_v2_generic_material_glb_remains_valid(monkeypatch):
    from app.services import garment_mesh, pants_materials

    spec = resolve_spec(info(), {"silhouette": analyze_pants(pants_photo())})
    monkeypatch.setattr(garment_mesh, "PANTS_VERSION", "stylefit-pants-2.0")
    monkeypatch.setattr(pants_materials, "generic_check", pants_materials.legacy_check)
    old, _ = build_glb(spec)
    monkeypatch.setattr(garment_mesh, "PANTS_VERSION", "stylefit-pants-2.1")
    assert validate_glb(old)["nodes"][0]["extras"]["version"] == "stylefit-pants-2.0"
