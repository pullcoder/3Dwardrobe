"""기존 python -m app.generation_worker 실행 명령을 유지하는 진입점."""

from app.workers.generation import main

if __name__ == "__main__":
    main()
