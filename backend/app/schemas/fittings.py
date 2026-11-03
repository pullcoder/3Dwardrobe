"""사진·관절·임의 3D 경로를 받지 않는 최소 체형 및 시각적 피팅 계약."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Part = Literal["top", "bottom", "outer"]
MeasurementKey = Literal["height", "shoulder", "chest", "waist", "hip", "arm", "leg"]


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)


class BodyValues(StrictInput):
    height: float | None = Field(default=None, ge=80, le=250)
    shoulder: float | None = Field(default=None, ge=15, le=90)
    chest: float | None = Field(default=None, ge=30, le=250)
    waist: float | None = Field(default=None, ge=30, le=250)
    hip: float | None = Field(default=None, ge=30, le=250)
    arm: float | None = Field(default=None, ge=15, le=120)
    leg: float | None = Field(default=None, ge=20, le=150)

    @model_validator(mode="after")
    def proportions(self):
        height = self.height or 170
        if (self.arm and self.arm > height * 0.48) or (self.leg and self.leg > height * 0.62):
            raise ValueError("체형 길이 비율을 확인해 주세요.")
        return self


class MannequinProfile(StrictInput):
    mode: Literal["manual", "photo"]
    values: BodyValues
    origins: dict[MeasurementKey, Literal["estimated", "user_entered"]] = Field(
        default_factory=dict
    )


class FitAdjustment(StrictInput):
    shoulder: float = Field(default=1, ge=0.8, le=1.25)
    chest: float = Field(default=1, ge=0.8, le=1.25)
    waist: float = Field(default=1, ge=0.8, le=1.25)
    hip: float = Field(default=1, ge=0.8, le=1.25)
    sleeve: float = Field(default=1, ge=0.75, le=1.25)
    length: float = Field(default=1, ge=0.75, le=1.25)
    offset_y: float = Field(default=0, ge=-0.12, le=0.12)
    clearance: float = Field(default=0.012, ge=0, le=0.06)
    hidden: bool = False


class FittingInput(StrictInput):
    mannequin: MannequinProfile
    body_storage_consent: bool = False
    slots: dict[Part, str | None] = Field(default_factory=dict)
    adjustments: dict[Part, FitAdjustment] = Field(default_factory=dict)


class FittingPatch(FittingInput):
    revision: int = Field(ge=1)


class OutfitInput(StrictInput):
    fitting_id: str = Field(min_length=36, max_length=36)
    name: str = Field(min_length=1, max_length=80)
