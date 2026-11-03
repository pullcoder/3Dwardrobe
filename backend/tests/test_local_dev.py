"""테스트 전용 워커를 추가하지 않고 실제 통합 실행 명령을 검증한다."""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
from sqlalchemy import create_engine, inspect
from test_garments import payload

ROOT = Path(__file__).resolve().parents[1]


def test_uninitialized_database_is_not_silently_migrated(tmp_path):
    database = f"sqlite:///{(tmp_path / 'old.db').as_posix()}"
    result = subprocess.run(
        [sys.executable, "-m", "app.local_dev"],
        cwd=ROOT,
        env={**os.environ, "DATABASE_URL": database},
        capture_output=True,
        timeout=15,
    )
    assert result.returncode == 1
    engine = create_engine(database)
    assert inspect(engine).get_table_names() == []
    engine.dispose()


def test_one_command_starts_api_and_real_worker_on_same_database(tmp_path):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, "-m", "app.local_dev", "--initialize-empty", "--port", str(port)],
        cwd=ROOT,
        env={**os.environ, "DATABASE_URL": f"sqlite:///{(tmp_path / 'runtime.db').as_posix()}"},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=2) as client:
            deadline = time.monotonic() + 20
            while True:
                assert process.poll() is None
                try:
                    if client.get("/api/v1/health").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                assert time.monotonic() < deadline
                time.sleep(0.1)
            response = client.post(
                "/api/v1/auth/register",
                json={"username": "runtime_tshirt", "password": "actual-worker-integration"},
            )
            assert response.status_code == 201, response.text
            headers = {"Authorization": f"Bearer {response.json()['token']}"}
            body = payload()
            body["info"]["garment_type"] = "티셔츠"
            saved = client.post(
                "/api/v1/garments",
                headers={
                    **headers,
                    "X-Upload-Rights": "confirmed",
                    "X-Image-Storage-Consent": "confirmed",
                },
                json=body,
            )
            assert saved.status_code == 201, saved.text
            uri = f"/api/v1/garments/{saved.json()['id']}"
            assert client.post(uri + "/generate-3d", headers=headers, json={}).status_code == 202
            deadline = time.monotonic() + 15
            while True:
                state = client.get(uri + "/generation-status", headers=headers).json()
                if state["generation_status"] == "completed":
                    break
                assert state["generation_status"] in {"queued", "processing"}
                assert time.monotonic() < deadline
                time.sleep(0.1)
            assert state["runtime"]["worker_online"]
            model = client.get(uri + "/model", headers=headers)
            assert model.status_code == 200 and model.content.startswith(b"glTF")
            assert state["model_metadata"]["triangle_count"] > 100
    finally:
        if process.poll() is None:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            else:
                process.terminate()
            process.wait(timeout=15)
