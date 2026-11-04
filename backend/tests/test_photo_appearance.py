"""직접 그린 색상 표식으로 사진/앞뒤/상하 방향과 실제 API 권리 경계를 검증한다."""

import base64
import struct
from io import BytesIO

import numpy as np
import pytest
from PIL import Image, ImageDraw
from test_garments import account, create
from test_generation import client as client
from test_generation import evidence_and_review, queue, status
from test_pants_quality import pants_photo
from test_top_pipeline import info as top_info
from test_top_pipeline import photo as top_photo

from app.core.errors import AppError
from app.services.garment_mesh import build_glb, make_meshes, resolve_spec, validate_glb
from app.services.generation import run_once
from app.services.pants_silhouette import analyze_pants
from app.services.photo_materials import panel
from app.services.top_silhouette import analyze_top


def marked_photo(kind, back=False):
    image = Image.open(BytesIO(top_photo() if kind == "top" else pants_photo())).convert("RGBA")
    mask = image.getchannel("A")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, image.width, image.height // 2), fill="yellow" if back else "red")
    draw.rectangle(
        (0, image.height // 2, image.width, image.height), fill="purple" if back else "blue"
    )
    image.putalpha(mask)
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


def photo_spec(kind, back=True):
    content = marked_photo(kind)
    analyze = analyze_top if kind == "top" else analyze_pants
    shape = analyze(content)
    info = (
        top_info()
        if kind == "top"
        else {"garment_type": "슬랙스", "category": "bottom", "color": "파랑"}
    )
    return {
        **resolve_spec(info, {"silhouette": shape}),
        "mode": "B",
        "_front_png": content,
        "_front_bbox": shape["bbox"],
        "_front_size": shape["image_size"],
        "_verified_projection": True,
        **({"_back_png": marked_photo(kind, True)} if back else {}),
    }


def atlas_from_glb(content):
    doc = validate_glb(content)
    view = doc["bufferViews"][doc["images"][0]["bufferView"]]
    start = 28 + struct.unpack_from("<I", content, 12)[0] + view["byteOffset"]
    return Image.open(BytesIO(content[start : start + view["byteLength"]])).convert("RGB")


@pytest.mark.parametrize("kind", ["top", "bottom"])
def test_real_embedded_photo_atlas_has_distinct_front_back_and_correct_uv_orientation(kind):
    spec = photo_spec(kind)
    content, metadata = build_glb(spec)
    atlas = atlas_from_glb(content)
    assert len(content) < 2 * 1024 * 1024
    assert metadata["photo_appearance"]["back"] == "verified_photo"
    assert metadata["fitting_contract"] in {"stylefit.panel.v3", "stylefit.pants.v2"}
    assert atlas.getpixel((atlas.width // 4, atlas.height // 4))[0] > 200
    assert atlas.getpixel((atlas.width // 4, atlas.height * 3 // 4))[2] > 200
    rear = atlas.getpixel((atlas.width * 3 // 4, atlas.height // 4))
    assert rear[0] > 200 and rear[1] > 200
    meshes = make_meshes(spec)
    positions = np.concatenate([np.array(m["positions"]).reshape(-1, 3) for m in meshes])
    uv = np.concatenate([np.array(m["uvs"]).reshape(-1, 2) for m in meshes])
    # glTF의 V=0은 이미지 상단. 허리/다리처럼 분리된 부위도 전체 옷 기준으로 검사한다.
    assert np.mean(uv[positions[:, 1] > positions[:, 1].max() * 0.9, 1]) < 0.15
    assert np.mean(uv[positions[:, 1] < positions[:, 1].max() * 0.1, 1]) > 0.85
    assert np.mean(uv[positions[:, 2] > 0.01, 0]) < 0.5
    assert np.mean(uv[positions[:, 2] < -0.01, 0]) > 0.5


@pytest.mark.parametrize("kind", ["top", "bottom"])
def test_missing_rear_stays_estimated_and_a_never_reuses_photo_pixels(kind):
    spec = photo_spec(kind, False)
    _, meta = build_glb(spec)
    assert meta["photo_appearance"]["back"] == "estimated"
    spec["mode"] = "A"
    content, meta = build_glb(spec)
    assert "images" not in validate_glb(content)
    assert "photo_appearance" not in meta


def test_edge_extension_does_not_composite_white_background():
    image = Image.new("RGBA", (100, 100))
    ImageDraw.Draw(image).rectangle((20, 20, 80, 80), fill=(25, 65, 125, 255))
    output = BytesIO()
    image.save(output, "PNG")
    result = np.asarray(panel(output.getvalue()))
    assert np.max(result[:, :, 0]) < 30 and np.min(result[:, :, 2]) > 120
    output = BytesIO()
    Image.new("RGB", (100, 100), "white").save(output, "PNG")
    with pytest.raises(AppError):
        panel(output.getvalue())


@pytest.mark.parametrize("kind", ["top", "bottom"])
def test_saved_photos_require_review_then_generate_fit_and_revoke(client, kind):
    headers = account(client, "photo-" + kind)
    front, back = marked_photo(kind), marked_photo(kind, True)

    def encode(data):
        return {"content_type": "image/png", "data": base64.b64encode(data).decode()}

    info = (
        top_info()
        if kind == "top"
        else {"name": "사진 바지", "garment_type": "슬랙스", "category": "bottom"}
    )
    response = create(
        client,
        headers,
        {
            "info": info,
            "images": {
                "front": encode(front),
                "cutout_front": encode(front),
                "back": encode(back),
                "cutout_back": encode(back),
            },
            "original_image_retention": "consented_storage",
        },
    )
    assert response.status_code == 201, response.text
    item = response.json()
    assert queue(client, headers, item).status_code == 202
    assert run_once(client.app.state.session_factory)
    assert status(client, headers, item)["model_metadata"]["mode"] == "A"
    evidence, decision = evidence_and_review(client, headers, item)
    reviewed = client.patch(
        f"/api/v1/admin/garments/{item['id']}/rights-review",
        headers={"X-Admin-Review-Key": "test-admin-key"},
        json=decision,
    )
    assert reviewed.status_code == 200 and evidence
    assert queue(client, headers, item).status_code == 202
    assert run_once(client.app.state.session_factory)
    state = status(client, headers, item)
    assert state["model_metadata"]["photo_appearance"]["back"] == "verified_photo"
    assert (
        client.get(f"/api/v1/fittings/resources/{item['id']}", headers=headers).status_code == 200
    )
    assert (
        client.post(
            f"/api/v1/garments/{item['id']}/rights-withdraw", headers=headers, json={}
        ).status_code
        == 204
    )
    assert client.get(f"/api/v1/garments/{item['id']}/model", headers=headers).status_code == 404
