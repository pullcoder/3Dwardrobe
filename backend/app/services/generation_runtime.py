"""같은 DB의 실제 생성 워커 응답만 표시한다. PID·사진·DB 주소는 노출하지 않는다."""

import time

from sqlalchemy import delete, func, select

from app.models import GenerationWorker
from app.services.garment_mesh import VERSION

HEARTBEAT_TTL = 15


def heartbeat(factory, worker_id):
    with factory() as db:
        db.execute(delete(GenerationWorker).where(GenerationWorker.last_seen < time.time() - 86400))
        db.merge(GenerationWorker(id=worker_id, engine_version=VERSION, last_seen=time.time()))
        db.commit()


def worker_status(db):
    seen = db.scalar(
        select(func.max(GenerationWorker.last_seen)).where(
            GenerationWorker.engine_version == VERSION
        )
    )
    return {"engine": VERSION, "worker_online": bool(seen and seen >= time.time() - HEARTBEAT_TTL)}
