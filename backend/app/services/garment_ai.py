"""의류 AI의 서비스 경계. 기존 호출부와 문서의 import 경로를 유지한다."""

from app.ai.garment_analysis import INFERENCE_LOCK, GarmentAI, image_from_bytes

__all__ = ["INFERENCE_LOCK", "GarmentAI", "image_from_bytes"]
