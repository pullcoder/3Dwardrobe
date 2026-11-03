"""도메인별 DB 모델. 기존 from app.models import ... 경로를 유지한다."""

from app.models.base import Base
from app.models.fittings import Fitting, Outfit, SavedMannequin
from app.models.garments import Asset, Garment
from app.models.generation import GenerationJob, GenerationWorker, RightsEvidence, RightsReview
from app.models.recommendations import Recommendation, StylePreference
from app.models.reports import Report
from app.models.users import LoginSession, User

__all__ = [
    "Base",
    "User",
    "LoginSession",
    "Garment",
    "Asset",
    "GenerationJob",
    "GenerationWorker",
    "RightsEvidence",
    "RightsReview",
    "Report",
    "SavedMannequin",
    "Fitting",
    "Outfit",
    "Recommendation",
    "StylePreference",
]
