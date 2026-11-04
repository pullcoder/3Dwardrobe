"""영속 DB 작업 큐. API는 등록만 하며 별도 프로세스 워커가 GLB를 생성한다."""

import logging
import time
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import delete, select, update

from app.core.errors import AppError
from app.models import Asset, Garment, GenerationJob
from app.services.garment_mesh import TEMPLATES, VERSION, build_glb, resolve_spec, validate_glb
from app.services.generation_engines import engine_catalog, require_engine
from app.services.generation_runtime import worker_status
from app.services.pants_silhouette import PANTS, analyze_pants, valid_shape
from app.services.top_silhouette import TOPS, analyze_top, valid_top

B_HIGH_FIDELITY_AVAILABLE = False
ACTIVE = ("queued", "processing")


def shape_asset(db, garment):
    for slot in ("cutout_front", "front"):
        asset = db.scalar(select(Asset).where(Asset.garment_id == garment.id, Asset.slot == slot))
        if asset:
            return asset
    return None


def b_available(db, garment):
    # 전체 AI 복원이 아닌, 검증된 사진의 티셔츠·바지 표면 투영만 지원한다.
    return garment.data.get("garment_type") in PANTS | TOPS and shape_asset(db, garment) is not None


def now():
    return datetime.now(UTC).isoformat()


def selected_mode(garment):
    statuses = (
        garment.photo_rights_status,
        garment.detailed_rights_status,
        garment.output_rights_status,
    )
    if any(s in {"disputed", "rejected"} for s in statuses):
        return None
    if garment.photo_rights_status not in {"confirmed", "verified"}:
        return None
    return "B" if all(s == "verified" for s in statuses) else "A"


def generation_read(db, garment):
    job = db.get(GenerationJob, garment.generation_job_id) if garment.generation_job_id else None
    mode = selected_mode(garment)
    return {
        "garment_id": garment.id,
        "selected_mode": mode,
        "b_available": b_available(db, garment),
        "b_high_fidelity_available": B_HIGH_FIDELITY_AVAILABLE,
        "photo_rights_status": garment.photo_rights_status,
        "detailed_rights_status": garment.detailed_rights_status,
        "output_rights_status": garment.output_rights_status,
        "rights_version": garment.rights_version,
        "rights_reviewed_at": garment.rights_reviewed_at,
        "generation_status": garment.generation_status,
        "job_id": garment.generation_job_id,
        "stage": garment.generation_status
        if garment.generation_status in {"idle", "cancelled"}
        else job.stage
        if job
        else "idle",
        "generation_error": garment.generation_error,
        "model_ready": bool(
            garment.model_3d_asset_id
            and mode
            and garment.generation_status == "completed"
            and (garment.reconstruction_mode != "B" or mode == "B")
        ),
        "model_format": garment.model_format,
        "model_version": garment.model_version,
        "model_metadata": job.result_metadata
        if job
        and garment.model_3d_asset_id
        and mode
        and (garment.reconstruction_mode != "B" or mode == "B")
        else None,
        "updated_at": garment.updated_at,
        "supported_types": list(TEMPLATES),
        "runtime": worker_status(db),
        "engines": engine_catalog(),
        "selected_engine": job.snapshot.get("engine", "template") if job else "template",
        "failure": {"stage": job.failure_stage, "exception_type": job.exception_type}
        if job and job.status == "failed"
        else None,
    }


def invalidate_generation(db, garment, reason="CANCELLED", bump_rights=False):
    """삭제/철회/신고/수정 시 늦게 끝나는 작업도 결과를 되살릴 수 없게 한다."""
    db.execute(
        update(GenerationJob)
        .where(GenerationJob.garment_id == garment.id, GenerationJob.status.in_(ACTIVE))
        .values(
            status="cancelled",
            stage="cancelled",
            error_code=reason,
            claim_token=None,
            updated_at=now(),
        )
    )
    db.execute(delete(Asset).where(Asset.garment_id == garment.id, Asset.slot == "model_3d"))
    values = {
        "generation_status": "cancelled",
        "generation_error": reason,
        "model_3d_status": "cancelled",
        "model_3d_asset_id": None,
        "generated_model_path": None,
        "model_format": None,
        "model_version": None,
        "updated_at": now(),
    }
    if bump_rights:
        values["rights_version"] = Garment.rights_version + 1
    db.execute(update(Garment).where(Garment.id == garment.id).values(**values))


def enqueue(db, garment, engine="template"):
    mode = selected_mode(garment)
    if not mode:
        raise AppError(
            "RIGHTS_REQUIRED", "사진 처리 권한을 확인하거나 권리 검토를 진행해 주세요.", 403
        )
    require_engine(engine)
    if mode == "B" and engine == "template" and not b_available(db, garment):
        raise AppError(
            "B_UNAVAILABLE",
            "B 사진 외형은 저장된 앞면과 세 권한 검증이 있는 티셔츠·바지만 지원합니다.",
            503,
        )
    if garment.generation_status in ACTIVE:
        raise AppError("GENERATION_ACTIVE", "이미 생성 작업이 진행 중입니다.", 409)
    has_back = (
        db.scalar(select(Asset.id).where(Asset.garment_id == garment.id, Asset.slot == "back"))
        is not None
    )
    spec = resolve_spec(garment.data, garment.analysis, has_back)
    if garment.data.get("garment_type") in PANTS:
        asset = shape_asset(db, garment)
        analysis = dict(garment.analysis)
        shape = analysis.get("silhouette")
        if asset and (not valid_shape(shape) or mode == "B"):
            try:
                shape = analyze_pants(asset.content)
                analysis["silhouette"] = shape
            except AppError as error:
                if mode == "B":
                    raise
                spec["pants"]["warnings"].append(
                    f"저장 사진의 외곽 분석 실패({error.code}). "
                    "형태 분석용 누끼를 다시 입력해 주세요."
                )
        if valid_shape(shape):
            spec = resolve_spec(garment.data, analysis, has_back)
        if mode == "B":
            spec["projection_asset_id"] = asset.id
            spec["projection_bbox"] = shape["bbox"]
            spec["projection_size"] = shape["image_size"]
    if spec.get("top_panel"):
        asset = shape_asset(db, garment)
        analysis = dict(garment.analysis)
        shape = analysis.get("silhouette")
        if not valid_top(shape) and asset:
            try:
                shape = analyze_top(asset.content)
                analysis["silhouette"] = shape
            except AppError as error:
                spec["top_panel"]["warnings"].append(
                    f"사진 외곽 분석 실패({error.code}). 일반 패턴을 사용합니다."
                )
        if valid_top(shape):
            spec = resolve_spec(garment.data, analysis, has_back)
        if mode == "B" and engine == "template":
            if not valid_top(shape):
                raise AppError("CUTOUT_REQUIRED", "펼친 티셔츠의 누끼를 확인해 주세요.", 422)
            spec["projection_asset_id"] = asset.id
            spec["projection_bbox"] = shape["bbox"]
            spec["projection_size"] = shape["image_size"]
    if mode == "B" and engine == "template":
        for slot in ("cutout_back", "back"):
            back = db.scalar(
                select(Asset).where(Asset.garment_id == garment.id, Asset.slot == slot)
            )
            if back:
                spec["back_projection_asset_id"] = back.id
                break
    spec["mode"] = mode
    spec["engine"] = engine
    if engine != "template":
        asset = db.scalar(
            select(Asset).where(Asset.garment_id == garment.id, Asset.slot == "cutout_front")
        )
        if not asset:
            raise AppError("CUTOUT_REQUIRED", "저장된 3단계 누끼 이미지가 필요합니다.", 422)
        spec["ai_asset_id"] = asset.id
    job_id = str(uuid4())
    changed = db.execute(
        update(Garment)
        .where(
            Garment.id == garment.id,
            Garment.revision == garment.revision,
            Garment.rights_version == garment.rights_version,
            Garment.generation_status == garment.generation_status,
            Garment.generation_job_id == garment.generation_job_id,
        )
        .values(
            generation_status="queued",
            generation_job_id=job_id,
            generation_error=None,
            model_3d_status="queued",
            reconstruction_mode=mode,
            model_3d_asset_id=None,
            generated_model_path=None,
            model_format=None,
            model_version=None,
            updated_at=now(),
        )
    )
    if not changed.rowcount:
        raise AppError("CONFLICT", "의류 상태가 변경되었습니다. 다시 조회해 주세요.", 409)
    db.execute(delete(Asset).where(Asset.garment_id == garment.id, Asset.slot == "model_3d"))
    job = GenerationJob(
        id=job_id,
        garment_id=garment.id,
        status="queued",
        stage="queued",
        mode=mode,
        snapshot=spec,
        rights_version=garment.rights_version,
        garment_revision=garment.revision,
        created_at=now(),
        updated_at=now(),
    )
    db.add(job)
    db.flush()
    return job


def suspend_rights(db, garment, reason):
    invalidate_generation(db, garment, reason, bump_rights=True)
    db.execute(
        update(Garment)
        .where(Garment.id == garment.id)
        .values(
            photo_rights_status="disputed",
            detailed_rights_status="disputed",
            output_rights_status="disputed",
            rights_status="pending",
        )
    )


def model_asset(db, garment):
    if (
        not selected_mode(garment)
        or (garment.reconstruction_mode == "B" and selected_mode(garment) != "B")
        or garment.generation_status != "completed"
        or not garment.model_3d_asset_id
    ):
        raise AppError("MODEL_UNAVAILABLE", "현재 이용할 수 있는 3D 모델이 없습니다.", 404)
    asset = db.get(Asset, garment.model_3d_asset_id)
    if not asset or asset.garment_id != garment.id or asset.slot != "model_3d":
        raise AppError("MODEL_UNAVAILABLE", "3D 모델을 찾을 수 없습니다.", 404)
    return asset


def run_once(factory, generator=build_glb):
    """다중 워커는 조건부 claim과 lease 토큰으로 같은 작업의 이중 저장을 막는다."""
    with factory() as db:
        # 재시작 후 만료된 작업만 회수한다. 유효한 다른 워커의 작업을 가로채지 않는다.
        expired = db.scalars(
            select(GenerationJob).where(
                GenerationJob.status == "processing", GenerationJob.lease_until < time.time()
            )
        ).all()
        for old in expired:
            recovered_status = "failed" if old.attempts >= 3 else "queued"
            error = "WORKER_TIMEOUT" if old.attempts >= 3 else None
            recovered = db.execute(
                update(GenerationJob)
                .where(
                    GenerationJob.id == old.id,
                    GenerationJob.status == "processing",
                    GenerationJob.claim_token == old.claim_token,
                    GenerationJob.lease_until < time.time(),
                )
                .values(
                    status=recovered_status,
                    stage=recovered_status,
                    error_code=error,
                    claim_token=None,
                    lease_until=None,
                    updated_at=now(),
                )
            )
            if recovered.rowcount:
                db.execute(
                    update(Garment)
                    .where(
                        Garment.generation_job_id == old.id,
                        Garment.generation_status == "processing",
                    )
                    .values(
                        generation_status=recovered_status,
                        model_3d_status=recovered_status,
                        generation_error=error,
                        updated_at=now(),
                    )
                )
        db.commit()
        job = db.scalar(
            select(GenerationJob)
            .where(GenerationJob.status == "queued")
            .order_by(GenerationJob.created_at)
            .limit(1)
        )
        if not job:
            return False
        job_id, token = job.id, str(uuid4())
        claimed = db.execute(
            update(GenerationJob)
            .where(GenerationJob.id == job_id, GenerationJob.status == "queued")
            .values(
                status="processing",
                stage="mesh",
                lease_until=time.time()
                + (120 if job.snapshot.get("engine", "template") == "template" else 1800),
                claim_token=token,
                attempts=GenerationJob.attempts + 1,
                updated_at=now(),
            )
        )
        if not claimed.rowcount:
            db.rollback()
            return True
        garment = db.get(Garment, job.garment_id)
        if (
            not garment
            or garment.generation_job_id != job_id
            or garment.rights_version != job.rights_version
            or garment.revision != job.garment_revision
            or selected_mode(garment) != job.mode
        ):
            job.status, job.stage = "cancelled", "cancelled"
            job.claim_token, job.lease_until = None, None
            db.execute(
                update(Garment)
                .where(Garment.generation_job_id == job_id)
                .values(
                    generation_status="cancelled",
                    model_3d_status="cancelled",
                    generation_error="STALE_INPUT",
                    updated_at=now(),
                )
            )
            db.commit()
            return True
        db.execute(
            update(Garment)
            .where(Garment.generation_job_id == job_id)
            .values(generation_status="processing", model_3d_status="processing", updated_at=now())
        )
        snapshot = dict(job.snapshot)
        if snapshot.get("engine", "template") != "template":
            source = db.get(Asset, snapshot.get("ai_asset_id"))
            if not source or source.garment_id != garment.id or source.slot != "cutout_front":
                job.status, job.stage, job.error_code = "failed", "failed", "SOURCE_UNAVAILABLE"
                job.claim_token, job.lease_until = None, None
                garment.generation_status = garment.model_3d_status = "failed"
                garment.generation_error = "SOURCE_UNAVAILABLE"
                db.commit()
                return True
            snapshot["_ai_content"], snapshot["_ai_mime"] = source.content, source.mime
            snapshot["_verified_details"] = selected_mode(garment) == "B"
        if job.mode == "B" and snapshot.get("engine", "template") == "template":
            asset = db.get(Asset, snapshot.get("projection_asset_id"))
            if (
                not asset
                or asset.garment_id != garment.id
                or asset.slot not in {"front", "cutout_front"}
            ):
                job.status, job.stage, job.error_code = "failed", "failed", "SOURCE_UNAVAILABLE"
                job.claim_token, job.lease_until = None, None
                garment.generation_status = garment.model_3d_status = "failed"
                garment.generation_error = "SOURCE_UNAVAILABLE"
                db.commit()
                return True
            snapshot["_front_png"] = asset.content
            snapshot["_front_bbox"] = snapshot["projection_bbox"]
            snapshot["_front_size"] = snapshot["projection_size"]
            snapshot["_verified_projection"] = True
            if snapshot.get("back_projection_asset_id"):
                back = db.get(Asset, snapshot["back_projection_asset_id"])
                if back and back.garment_id == garment.id and back.slot in {"back", "cutout_back"}:
                    snapshot["_back_png"] = back.content
        db.commit()
    phase = "mesh"

    def progress(stage):
        nonlocal phase
        phase = stage
        with factory() as db:
            db.execute(
                update(GenerationJob)
                .where(
                    GenerationJob.id == job_id,
                    GenerationJob.claim_token == token,
                    GenerationJob.status == "processing",
                )
                .values(stage=stage, updated_at=now())
            )
            db.commit()

    try:
        if snapshot.get("engine", "template") != "template":
            from app.services.ai_generation import generate_ai

            content, metadata = generate_ai(snapshot, progress)
        else:
            content, metadata = (
                build_glb(snapshot, progress=progress)
                if generator is build_glb
                else generator(snapshot)
            )
        phase = "validating"
        with factory() as db:
            changed = db.execute(
                update(GenerationJob)
                .where(
                    GenerationJob.id == job_id,
                    GenerationJob.claim_token == token,
                    GenerationJob.status == "processing",
                )
                .values(stage="validating", updated_at=now())
            )
            db.commit()
            if not changed.rowcount:
                return True
        if snapshot.get("engine", "template") == "template":
            validate_glb(content)
        else:
            from app.ai.generated_mesh import inspect_glb

            inspect_glb(content)
        phase = "saving"
        with factory() as db:
            job = db.get(GenerationJob, job_id)
            garment = db.get(Garment, job.garment_id) if job else None
            if not job or job.claim_token != token or job.status != "processing" or not garment:
                return True
            retained = db.execute(
                update(GenerationJob)
                .where(
                    GenerationJob.id == job_id,
                    GenerationJob.claim_token == token,
                    GenerationJob.status == "processing",
                    GenerationJob.lease_until > time.time(),
                )
                .values(stage="saving", updated_at=now())
            )
            if not retained.rowcount:
                db.rollback()
                return True
            asset_id = str(uuid4())
            phase = "database_update"
            changed = db.execute(
                update(Garment)
                .where(
                    Garment.id == garment.id,
                    Garment.generation_job_id == job_id,
                    Garment.rights_version == job.rights_version,
                    Garment.revision == job.garment_revision,
                    Garment.generation_status == "processing",
                )
                .values(
                    generation_status="completed",
                    model_3d_status="completed",
                    model_3d_asset_id=asset_id,
                    generated_model_path=f"private:garment/{garment.id}/{asset_id}.glb",
                    model_format="glb",
                    model_version=metadata.get("version", VERSION),
                    generation_error=None,
                    updated_at=now(),
                )
            )
            if not changed.rowcount or selected_mode(garment) != job.mode:
                db.rollback()
                return True
            phase = "asset_storage"
            db.add(
                Asset(
                    id=asset_id,
                    garment_id=garment.id,
                    slot="model_3d",
                    content=content,
                    mime="model/gltf-binary",
                )
            )
            db.flush()
            job.status, job.stage, job.result_metadata, job.updated_at = (
                "completed",
                "completed",
                metadata,
                now(),
            )
            job.claim_token, job.lease_until = None, None
            phase = "database_commit"
            db.commit()
    except Exception as error:
        logging.error("generation_failed stage=%s exception_type=%s", phase, type(error).__name__)
        # 라이브러리 예외/사용자 입력·경로를 로그나 응답에 노출하지 않는다.
        with factory() as db:
            changed = db.execute(
                update(GenerationJob)
                .where(
                    GenerationJob.id == job_id,
                    GenerationJob.claim_token == token,
                    GenerationJob.status == "processing",
                )
                .values(
                    status="failed",
                    stage="failed",
                    error_code="GENERATION_FAILED",
                    failure_stage=phase,
                    exception_type=type(error).__name__[:80],
                    claim_token=None,
                    lease_until=None,
                    updated_at=now(),
                )
            )
            if changed.rowcount:
                db.execute(
                    update(Garment)
                    .where(Garment.generation_job_id == job_id)
                    .values(
                        generation_status="failed",
                        model_3d_status="failed",
                        generation_error="GENERATION_FAILED",
                        updated_at=now(),
                    )
                )
            db.commit()
    return True
