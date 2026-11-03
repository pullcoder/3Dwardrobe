"""python -m app.generation_worker: API와 분리된 로컬 CPU 작업 큐 소비자."""

import argparse
import signal
import threading

from app.core.config import Settings
from app.core.database import create_database
from app.services.generation import run_once


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    engine, factory = create_database(Settings().database_url)
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    try:
        while not stop.is_set():
            worked = run_once(factory)
            if args.once:
                break
            if not worked:
                stop.wait(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
