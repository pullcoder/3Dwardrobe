from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def client():
    """격리된 로컬 API로 검증한다."""
    with TestClient(
        create_app(Settings(_env_file=None, database_url="sqlite:///:memory:"))
    ) as test_client:
        yield test_client


def photo(format="PNG", size=(32, 48)):
    """실제 디코딩 가능한 테스트 이미지를 메모리에서 만든다."""
    buffer = BytesIO()
    Image.new("RGB", size, "white").save(buffer, format=format)
    return buffer.getvalue()


def upload(client, data, mime="image/png", **headers):
    """권리 확인을 포함한 검증 요청을 보낸다."""
    return client.post(
        "/api/v1/uploads/validate",
        content=data,
        headers={"Content-Type": mime, "X-Upload-Rights": "confirmed", **headers},
    )


def test_health_reports_actual_installed_capabilities(client):
    result = client.get("/api/v1/health").json()
    assert result["features"] == {
        "image_validation": True,
        "ai": all(
            client.app.state.garment_ai.status()[key]
            for key in ("classification", "segmentation", "ocr")
        ),
        "storage": True,
        "auth": True,
    }


@pytest.mark.parametrize(
    "format,mime", [("PNG", "image/png"), ("JPEG", "image/jpeg"), ("WEBP", "image/webp")]
)
def test_valid_image_not_retained(client, format, mime):
    response = upload(client, photo(format), mime)
    assert response.status_code == 200
    assert response.json() == {
        "content_type": mime,
        "size_bytes": len(photo(format)),
        "width": 32,
        "height": 48,
        "retained": False,
        "ai_processed": False,
    }
    assert response.headers["cache-control"] == "no-store"


def test_requires_rights_confirmation(client):
    response = client.post("/api/v1/uploads/validate", content=photo())
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "RIGHTS_REQUIRED"


@pytest.mark.parametrize(
    "data,mime,code",
    [
        (b"not an image", "image/png", "INVALID_IMAGE"),
        (b"<svg></svg>", "image/svg+xml", "UNSUPPORTED_IMAGE"),
        (photo(), "image/jpeg", "IMAGE_TYPE_MISMATCH"),
        (b"", "image/png", "INVALID_IMAGE"),
        (photo()[:45], "image/png", "INVALID_IMAGE"),
    ],
)
def test_rejects_invalid_content(client, data, mime, code):
    response = upload(client, data, mime)
    assert response.status_code in {400, 415}
    assert response.json()["error"]["code"] == code


def test_size_limit_even_without_declared_length():
    with TestClient(create_app(Settings(_env_file=None, max_upload_bytes=8))) as client:
        response = upload(client, iter([b"1234", b"56789"]))
    assert response.status_code == 413


def test_pixel_limit():
    with TestClient(create_app(Settings(_env_file=None, max_image_pixels=10))) as client:
        assert upload(client, photo()).status_code == 413


def test_cross_origin_blocked(client):
    response = upload(client, photo(), origin="https://untrusted.example")
    assert response.status_code == 403
    assert response.headers["cache-control"] == "no-store"


def test_remote_client_blocked():
    with TestClient(create_app(Settings(_env_file=None)), client=("192.0.2.1", 1234)) as client:
        assert client.get("/api/v1/health").status_code == 403


def test_production_setting_rejected():
    with pytest.raises(ValueError):
        Settings(_env_file=None, app_env="production")
