from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services import auth


def test_total_json_limit_before_parse():
    with TestClient(
        create_app(
            Settings(_env_file=None, database_url="sqlite:///:memory:", max_request_bytes=1024)
        )
    ) as client:
        response = client.post(
            "/api/v1/auth/register",
            content=b"a" * 1025,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 413


def test_expired_session_is_rejected():
    from sqlalchemy import update

    from app.models import LoginSession

    auth._attempts.clear()
    with TestClient(
        create_app(Settings(_env_file=None, database_url="sqlite:///:memory:"))
    ) as client:
        response = client.post(
            "/api/v1/auth/register", json={"username": "expiry", "password": "test-password-1234"}
        )
        headers = {"Authorization": f"Bearer {response.json()['token']}"}
        with client.app.state.session_factory() as db:
            db.execute(update(LoginSession).values(expires_at=0))
            db.commit()
        assert client.get("/api/v1/garments", headers=headers).status_code == 401
