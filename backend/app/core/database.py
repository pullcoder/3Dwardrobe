from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def create_database(url: str):
    """PostgreSQL 우선. Docker가 없는 로컬 개발에서는 명시적 SQLite 대체를 사용한다."""
    if url.startswith("sqlite") and ":memory:" not in url:
        Path("storage").mkdir(exist_ok=True)
    options = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
    if ":memory:" in url:
        options["poolclass"] = StaticPool
    engine = create_engine(url, **options)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA secure_delete=ON")

    return engine, sessionmaker(engine, expire_on_commit=False)


def get_db(request):
    return Session(request.app.state.engine)
