"""자체 제작 입력으로 연결 패널/개구부/실루엣 출처와 인증 경계를 검증한다."""

import base64
from io import BytesIO

import pytest
from PIL import Image, ImageDraw
from test_garments import account, create
from test_pants_quality import client as client

from app.services.garment_mesh import build_glb, resolve_spec, validate_glb
from app.services.top_silhouette import analyze_top


def photo(width=480):
    image = Image.new("RGBA", (900, 700))
    left, right = 450 - width / 2, 450 + width / 2
    ImageDraw.Draw(image).polygon(
        [
            (left, 660),
            (left, 300),
            (80, 340),
            (20, 180),
            (left + 15, 65),
            (355, 35),
            (380, 65),
            (450, 85),
            (520, 65),
            (545, 35),
            (right - 15, 65),
            (880, 180),
            (820, 340),
            (right, 300),
            (right, 660),
        ],
        fill=(210, 210, 215, 255),
    )
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def info(fit="regular"):
    return {
        "name": "직접 제작 티셔츠",
        "garment_type": "티셔츠",
        "category": "top",
        "color": "흰색",
        "fit": fit,
        "measurements": [],
    }


@pytest.mark.parametrize("neckline", ["라운드넥", "브이넥"])
def test_connected_tshirt_has_four_openings_without_reversed_or_degenerate_faces(neckline):
    spec = resolve_spec({**info(), "neckline": neckline}, {})
    content, meta = build_glb(spec)
    assert meta["fitting_contract"] == "stylefit.panel.v3"
    assert meta["mesh_quality"] == {
        "connected_components": 1,
        "boundary_loops": 4,
        "boundary_branches": 0,
        "degenerate_triangles": 0,
        "nonmanifold_edges": 0,
        "inconsistent_winding_edges": 0,
        "self_intersections": "not_evaluated_in_runtime",
    }
    doc = validate_glb(content)
    assert len(doc["meshes"]) == 1 and doc["meshes"][0]["name"] == "body"
    assert "TEXCOORD_0" in doc["meshes"][0]["primitives"][0]["attributes"]


def test_photo_width_and_explicit_measurement_change_pattern_not_only_color():
    a = resolve_spec(info(), {"silhouette": analyze_top(photo(480))})
    b = resolve_spec(info(), {"silhouette": analyze_top(photo(350))})
    assert a["dimensions"]["width"]["value"] > b["dimensions"]["width"]["value"] * 1.2
    assert a["top_panel"]["observed"]
    manual = {
        **info(),
        "measurements": [
            {
                "label": "가슴단면",
                "value": 60,
                "unit": "cm",
                "kind": "flat",
                "target": "garment",
                "source": "user_entered",
            }
        ],
    }
    assert resolve_spec(manual, {"silhouette": analyze_top(photo())})["dimensions"]["width"] == {
        "value": 0.6,
        "source": "user_entered",
    }
    assert (
        resolve_spec(info("오버핏"), {})["dimensions"]["width"]["value"]
        > resolve_spec(info(), {})["dimensions"]["width"]["value"]
    )


def test_top_temporary_analysis_and_reupload_ownership(client):
    alice, bob = account(client, "tee-owner"), account(client, "tee-other")
    item = create(
        client,
        alice,
        {
            "info": info(),
            "images": {
                "front": {"content_type": "image/png", "data": base64.b64encode(photo()).decode()}
            },
            "original_image_retention": "temporary",
        },
    ).json()
    assert item["analysis"]["silhouette"]["kind"] == "top" and not item["assets"]
    uri = f"/api/v1/garments/{item['id']}/silhouette"
    consent = {
        "Content-Type": "image/png",
        "X-Upload-Rights": "confirmed",
        "X-Image-Processing-Consent": "confirmed",
    }
    assert client.post(uri, headers={**bob, **consent}, content=photo()).status_code == 404
    assert client.post(uri, headers=alice, content=photo()).status_code == 400
    response = client.post(uri, headers={**alice, **consent}, content=photo(350))
    assert response.status_code == 200 and response.json()["revision"] == item["revision"] + 1
