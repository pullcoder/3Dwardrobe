"""API와 실제 GLB 워커를 같은 DB로 함께 실행하는 로컬 개발 진입점."""

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from alembic import command as migrations
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from app.core.config import Settings
from app.core.database import create_database


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--initialize-empty", action="store_true", help="테이블 없는 새 DB만 초기화"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    settings = Settings()
    engine, _ = create_database(settings.database_url)
    try:
        config = Config(str(root / "alembic.ini"))
        head = ScriptDirectory.from_config(config).get_current_head()
        with engine.connect() as connection:
            empty = not inspect(connection).get_table_names()
        if empty and args.initialize_empty:
            migrations.upgrade(config, "head")
        with engine.connect() as connection:
            version = (
                connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
                if inspect(connection).has_table("alembic_version")
                else None
            )
        if version != head:
            parser.exit(
                1, "DB 스키마를 확인하세요. 백업 후 python -m alembic upgrade head가 필요합니다.\n"
            )
    finally:
        engine.dispose()
    env = {**os.environ, "DATABASE_URL": settings.database_url}
    children = []
    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, stop)
    exit_code = 0
    try:
        for command in (
            ["app.generation_worker"],
            [
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(args.port),
                "--no-access-log",
            ],
        ):
            children.append(subprocess.Popen([sys.executable, "-m", *command], cwd=root, env=env))
        print("StyleFit API와 GLB 생성 워커를 동일 DB로 실행했습니다.", flush=True)
        while not stopping:
            if any(child.poll() is not None for child in children):
                print("API 또는 생성 워커가 종료되어 함께 중지합니다.", file=sys.stderr, flush=True)
                exit_code = 1
                break
            time.sleep(0.25)
    finally:
        for child in children:
            if child.poll() is None:
                if os.name == "nt":
                    # Windows venv 실행기의 자식 Python도 함께 정리한다.
                    subprocess.run(
                        ["taskkill", "/PID", str(child.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
                else:
                    child.terminate()
        for child in children:
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
