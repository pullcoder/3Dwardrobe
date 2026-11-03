"""추천 입력에는 사진·사용자 ID·임의 의류/모델 경로를 받지 않는다."""

from typing import Literal

from pydantic import Field, model_validator

from app.schemas.fittings import MannequinProfile, StrictInput

Style = Literal[
    "minimal", "casual", "street", "formal", "business_casual", "sporty", "vintage", "other"
]
Fit = Literal["slim", "regular", "oversized", "any"]
Purpose = Literal["daily", "work", "occasion", "exercise", "travel", "any"]
Season = Literal["spring", "summer", "autumn", "winter", "any"]
Mood = Literal["calm", "neat", "active", "expressive", "any"]


class StylePreferences(StrictInput):
    styles: list[Style] = Field(default_factory=list, max_length=8)
    fit: Fit = "any"
    preferred_colors: list[str] = Field(default_factory=list, max_length=12)
    avoided_colors: list[str] = Field(default_factory=list, max_length=12)
    preferred_types: list[str] = Field(default_factory=list, max_length=14)
    purpose: Purpose = "any"
    season: Season = "any"
    mood: Mood = "any"

    @model_validator(mode="after")
    def lists(self):
        for key in ("styles", "preferred_colors", "avoided_colors", "preferred_types"):
            values = getattr(self, key)
            if any(not value or len(value) > 40 for value in values):
                raise ValueError("선호 목록을 확인해 주세요.")
            setattr(self, key, list(dict.fromkeys(values)))
        return self


class PreferenceUpdate(StylePreferences):
    revision: int = Field(default=0, ge=0)


class RecommendationInput(StrictInput):
    count: int = Field(default=4, ge=3, le=5)
    body: MannequinProfile | None = None
    mannequin_id: str | None = Field(default=None, min_length=36, max_length=36)
    body_processing_consent: bool = False

    @model_validator(mode="after")
    def one_body(self):
        if self.body and self.mannequin_id:
            raise ValueError("체형 입력 방식은 하나만 선택해 주세요.")
        if (self.body or self.mannequin_id) and not self.body_processing_consent:
            raise ValueError("추천용 체형 수치 처리에 동의해 주세요.")
        return self


class RecommendationFeedback(StrictInput):
    feedback: Literal["like", "dislike", "exclude", "none"]


class RecommendationApply(StrictInput):
    mannequin_id: str | None = Field(default=None, min_length=36, max_length=36)
