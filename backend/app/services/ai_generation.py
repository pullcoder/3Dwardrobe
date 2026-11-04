"""별도 워커 전용 AI 경로. 미지원 엔진을 템플릿 성공으로 바꾸지 않는다."""

import time
from pathlib import Path
from tempfile import TemporaryDirectory

from app.ai.generated_mesh import inspect_glb
from app.ai.generation_adapters import ADAPTERS
from app.ai.generation_input import prepare_input
from app.core.errors import AppError
from app.services.generation_engines import require_engine


def generate_ai(spec, progress):
    engine = spec["engine"]
    require_engine(engine)
    if spec["mode"] == "B" and not spec.get("_verified_details"):
        raise AppError("RIGHTS_REQUIRED", "B 세부 표현의 세 권한 검증이 필요합니다.", 403)
    progress("preprocessing")
    image, preprocessing = prepare_input(spec["_ai_content"], spec["_ai_mime"], spec["mode"])
    weights = Path(__file__).resolve().parents[2] / "models" / "engines" / engine
    if not weights.is_dir():
        raise AppError("MODEL_UNAVAILABLE", "감사된 로컬 가중치가 없습니다.", 503)
    start = time.perf_counter()
    with TemporaryDirectory(prefix="stylefit-generated-") as folder:
        output = Path(folder) / "result.glb"
        progress("inference")
        metrics = ADAPTERS[engine]().generate(image, weights, output)
        progress("postprocessing")
        content = output.read_bytes()
        quality = inspect_glb(content)
    return content, {
        "engine": engine,
        "generation_kind": "ai",
        "version": f"{engine}-experimental-1",
        "mode": spec["mode"],
        "category": spec["category"],
        "garment_type": spec["garment_type"],
        "dimensions": {},
        "unit": "uncalibrated",
        "coordinate_system": "unverified",
        "fitting_contract": None,
        "wearable": False,
        "preprocessing": preprocessing,
        "mesh_quality": quality,
        "triangle_count": quality["triangle_count"],
        "elapsed_seconds": time.perf_counter() - start,
        **metrics,
        "warnings": [
            "AI 생성 결과의 착용 구조는 미검증입니다.",
            "피팅하려면 기존 의류 템플릿으로 다시 생성해 주세요.",
        ],
    }
