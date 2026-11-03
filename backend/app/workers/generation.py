"""python -m app.generation_worker: API와 분리된 로컬 CPU 작업 큐 소비자."""

import argparse
import logging
import signal
import threading
from uuid import uuid4

from app.core.config import Settings
from app.core.database import create_database
from app.models import GenerationWorker
from app.services.generation import run_once
from app.services.generation_runtime import heartbeat


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    engine, factory = create_database(Settings().database_url)
    stop = threading.Event()
    worker_id = str(uuid4())
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    try:
        while not stop.is_set():
            try:
                heartbeat(factory, worker_id)
                worked = run_once(factory)
            except Exception as error:
                # 예외 메시지/SQL 매개변수/개인 사진을 출력하지 않는다.
                logging.error(
                    "generation_worker_unavailable exception_type=%s", type(error).__name__
                )
                if args.once:
                    raise SystemExit(1) from None
                stop.wait(3)
                continue
            if args.once:
                break
            if not worked:
                stop.wait(1)
    finally:
        try:
            with factory() as db:
                row = db.get(GenerationWorker, worker_id)
                if row:
                    db.delete(row)
                    db.commit()
        except Exception:
            logging.error("generation_worker_shutdown_registry_unavailable")
        engine.dispose()


if __name__ == "__main__":
    main()
