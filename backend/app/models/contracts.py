from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


AnchorValue = Literal[
    "top_left",
    "top_center",
    "top_right",
    "center_left",
    "center",
    "center_right",
    "bottom_left",
    "bottom_center",
    "bottom_right",
]
JobStatus = Literal["idle", "running", "succeeded", "failed", "cancelled"]
IssueSeverity = Literal["error", "warning"]


class AssetSubtypeModel(BaseModel):
    name: str
    file_count: int


class AssetClassModel(BaseModel):
    name: str
    root_file_count: int = 0
    subtypes: list[AssetSubtypeModel]


class AssetInventoryModel(BaseModel):
    classes: list[AssetClassModel]


class ValidationIssueModel(BaseModel):
    severity: IssueSeverity
    path: str
    message: str


class ValidationResultModel(BaseModel):
    issues: list[ValidationIssueModel]
    has_error: bool
    has_warning: bool


class BackgroundModel(BaseModel):
    id: str
    name: str
    image_path: str


class CanvasSizeRangeModel(BaseModel):
    width: tuple[int, int]
    height: tuple[int, int]


class AugmentationModel(BaseModel):
    rotation_max: float = 0
    blur_max: float = 0
    noise_max: float = 0


class BlockModel(BaseModel):
    id: str
    bbox: tuple[float, float, float, float]
    class_name: str = Field(alias="class")
    allowed_subtypes: list[str]
    capacity: int
    skip_prob: float
    position_anchor: AnchorValue | None
    augmentation: AugmentationModel

    model_config = {"populate_by_name": True}


class BackgroundSceneModel(BaseModel):
    id: str
    scene_weight: float
    canvas_size_range: CanvasSizeRangeModel
    background: BackgroundModel
    blocks: list[BlockModel]
    allow_overlap: bool = True


class TemplateModel(BaseModel):
    version: Literal[2]
    name: str
    description: str
    background_scenes: list[BackgroundSceneModel]


class JobStateModel(BaseModel):
    status: JobStatus
    active_job_id: str | None


class WorkingTemplateSnapshotModel(BaseModel):
    template: TemplateModel
    validation: ValidationResultModel
    inventory: AssetInventoryModel
    job: JobStateModel


class SaveTemplateRequestModel(BaseModel):
    template: TemplateModel


class ValidateTemplateRequestModel(BaseModel):
    template: TemplateModel


class PreviewRequestModel(BaseModel):
    background_scene_id: str


class PreviewResponseModel(BaseModel):
    preview_url: str


class UploadResponseModel(BaseModel):
    inventory: AssetInventoryModel


class BackgroundUploadResponseModel(BaseModel):
    background_scene_id: str


class BackgroundDeleteResponseModel(BaseModel):
    active_background_scene_id: str


class JobCreateRequestModel(BaseModel):
    count: int


class JobCreateResponseModel(BaseModel):
    id: str
    status: Literal["running"]


class JobResponseModel(BaseModel):
    id: str
    status: JobStatus
    count: int
    generated_count: int
    created_at: datetime
    updated_at: datetime
    zip_ready: bool
    download_url: str | None
    error: str | None


class SplitConfig(BaseModel):
    train: float = Field(default=1.0, ge=0.0, le=1.0)
    valid: float = Field(default=0.0, ge=0.0, le=1.0)
    test: float = Field(default=0.0, ge=0.0, le=1.0)


class ExportRequestModel(BaseModel):
    format: Literal["yolo", "coco"]
    split: SplitConfig = Field(default_factory=SplitConfig)


class ExportResponseModel(BaseModel):
    download_url: str


class ResetResponseModel(BaseModel):
    ok: bool

