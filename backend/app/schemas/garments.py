from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["top", "bottom", "outer"]


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(min_length=12, max_length=128)


class Measurement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(max_length=80)
    size: str | None = Field(default=None, max_length=30)
    value: float | None = Field(default=None, ge=0, le=10000)
    unit: Literal["cm", "mm", "inch", "unknown"] = "unknown"
    kind: Literal["flat", "circumference", "length", "unknown"] = "unknown"
    target: Literal["garment", "body", "unknown"] = "unknown"
    source: Literal["ocr", "user_entered"] = "user_entered"


class Composition(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=60)
    percent: float | None = Field(default=None, ge=0, le=100)
    source: Literal["ocr", "user_entered"] = "user_entered"


class GarmentInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=80)
    category: Category
    garment_type: str = Field(default="unknown", max_length=60)
    color: str = Field(default="", max_length=100)
    secondary_color: str | None = Field(default=None, max_length=100)
    pattern: str = Field(default="unknown", max_length=80)
    sleeve: str = Field(default="unknown", max_length=60)
    neckline: str = Field(default="unknown", max_length=60)
    fit: str = Field(default="unknown", max_length=60)
    visual_features: str = Field(default="", max_length=500)
    size: str = Field(default="", max_length=100)
    material: str = Field(default="미확인", max_length=200)
    composition: list[Composition] = Field(default_factory=list, max_length=30)
    measurements: list[Measurement] = Field(default_factory=list, max_length=100)
    description: str = Field(default="", max_length=2000)


class ImageInput(BaseModel):
    content_type: Literal["image/jpeg", "image/png", "image/webp"]
    data: str = Field(max_length=14_000_000)


class GarmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    info: GarmentInfo
    analysis: dict = Field(default_factory=dict)
    images: dict[str, ImageInput]
    reconstruction_mode: Literal["A"] = "A"
    source_type: Literal["self_photographed", "licensed_image", "other"] = "other"
    original_image_retention: Literal["temporary", "consented_storage"] = "temporary"


class GarmentPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    info: GarmentInfo
    revision: int = Field(ge=1)


class RightsReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    license_reference: str = Field(min_length=5, max_length=1000)
    revision: int = Field(ge=1)
    evidence_id: str | None = Field(default=None, max_length=36)


class RightsDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    photo_rights_status: Literal["unverified", "verified", "rejected", "disputed"]
    detailed_rights_status: Literal["unverified", "verified", "rejected", "disputed"]
    output_rights_status: Literal["unverified", "verified", "rejected", "disputed"]
    evidence_id: str | None = Field(default=None, max_length=36)
    notes: str = Field(min_length=10, max_length=2000)
    rights_version: int = Field(ge=1)


class ReportInput(BaseModel):
    garment_id: str | None = None
    reason: str = Field(min_length=5, max_length=2000)
    kind: Literal["rights", "analysis"] = "rights"


class ReportStatus(BaseModel):
    status: Literal["reviewing", "resolved", "rejected"]
