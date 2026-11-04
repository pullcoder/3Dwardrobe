"""생성 엔진과 권리 모드를 분리한다. 미감사 실행 환경은 닫힌 상태로 유지한다."""

import platform
import subprocess
from functools import lru_cache

from app.core.errors import AppError

ENGINE_IDS = ("template", "triposr", "trellis2")


@lru_cache(maxsize=1)
def hardware():
    """API에서 torch/CUDA를 초기화하거나 가중치를 내려받지 않는다."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=True,
        )
        gpus = []
        for line in result.stdout.strip().splitlines():
            name, memory = line.rsplit(",", 1)
            gpus.append({"name": name.strip(), "memory_mib": int(memory.strip())})
    except (OSError, subprocess.SubprocessError, ValueError):
        gpus = []
    return {"system": platform.system(), "gpus": gpus}


def engine_catalog(environment=None):
    env = environment if environment is not None else hardware()
    memory = max((gpu["memory_mib"] for gpu in env["gpus"]), default=0)
    result = [
        {
            "id": "template",
            "name": "기존 의류 템플릿",
            "available": True,
            "kind": "procedural",
            "license_status": "project_original",
            "reasons": [],
            "requirements": "CPU · 기존 시각적 피팅 지원",
        }
    ]
    for engine, name, minimum in (("triposr", "TripoSR", 6144), ("trellis2", "TRELLIS.2", 24576)):
        reasons = []
        if engine == "trellis2" and env["system"] != "Linux":
            reasons.append("공식 검증 환경인 Linux가 필요합니다.")
        if memory < minimum:
            reasons.append(f"NVIDIA VRAM {minimum // 1024}GB 이상 실행 예산이 필요합니다.")
        reasons.append("격리된 CUDA 실행 환경·고정 가중치·전체 종속성 감사가 준비되지 않았습니다.")
        if engine == "trellis2":
            reasons.append(
                "공식 nvdiffrast/nvdiffrec 경로의 비상업 조건으로 상용 활성화를 차단합니다."
            )
        result.append(
            {
                "id": engine,
                "name": name,
                "available": False,
                "kind": "ai",
                "license_status": "blocked_noncommercial_dependencies"
                if engine == "trellis2"
                else "dependencies_pending",
                "reasons": reasons,
                "requirements": "Linux · NVIDIA 24GB+"
                if engine == "trellis2"
                else "CUDA · 기본 설정 약 6GB VRAM (공식 실행 예산)",
            }
        )
    return result


def require_engine(engine):
    entry = next((item for item in engine_catalog() if item["id"] == engine), None)
    if entry is None:
        raise AppError("UNKNOWN_ENGINE", "지원하지 않는 생성 엔진입니다.", 422)
    if not entry["available"]:
        raise AppError("ENGINE_UNAVAILABLE", " ".join(entry["reasons"]), 503)
    return entry


def fitting_gate(metadata):
    """형태 검사는 착용 구조의 증명이 아니다. AI 메시를 기존 계약으로 위장하지 않는다."""
    if metadata.get("generation_kind") == "ai" or metadata.get("engine") in {"triposr", "trellis2"}:
        raise AppError(
            "GARMENT_STRUCTURE_UNVERIFIED",
            "목·팔·허리·다리 공간, 두께와 신체 충돌이 검증되지 않은 AI 메시입니다. "
            "기존 의류 템플릿으로 다시 생성한 뒤 피팅해 주세요.",
            422,
        )
