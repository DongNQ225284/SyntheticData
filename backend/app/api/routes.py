from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from pathlib import Path

from backend.app.core.settings import Settings
from backend.app.deps import get_job_service, get_settings_dep, get_workspace_service
from backend.app.models.contracts import (
    BackgroundDeleteResponseModel,
    BackgroundUploadResponseModel,
    ExportRequestModel,
    ExportResponseModel,
    JobCreateRequestModel,
    JobCreateResponseModel,
    JobResponseModel,
    PreviewRequestModel,
    PreviewResponseModel,
    ResetResponseModel,
    SaveTemplateRequestModel,
    UploadResponseModel,
    ValidateTemplateRequestModel,
    ValidationResultModel,
    WorkingTemplateSnapshotModel,
)
from backend.app.services.job_service import JobService
from backend.app.services.workspace_service import WorkspaceService


router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/assets/upload", response_model=UploadResponseModel)
def upload_assets(
    file: UploadFile = File(...),
    workspace: WorkspaceService = Depends(get_workspace_service),
    jobs: JobService = Depends(get_job_service),
) -> UploadResponseModel:
    jobs.hard_reset()
    inventory = workspace.ingest_assets_archive(file)
    return UploadResponseModel(inventory=inventory)


@router.post("/working-template/reset", response_model=ResetResponseModel)
def reset_template(
    workspace: WorkspaceService = Depends(get_workspace_service),
    jobs: JobService = Depends(get_job_service),
) -> ResetResponseModel:
    jobs.hard_reset()
    workspace.reset()
    return ResetResponseModel(ok=True)


@router.get("/working-template", response_model=WorkingTemplateSnapshotModel)
def get_working_template(
    workspace: WorkspaceService = Depends(get_workspace_service),
    jobs: JobService = Depends(get_job_service),
) -> WorkingTemplateSnapshotModel:
    return workspace.snapshot(jobs.current_status, jobs.active_job_id)


@router.put("/working-template", response_model=WorkingTemplateSnapshotModel)
def save_working_template(
    payload: SaveTemplateRequestModel,
    workspace: WorkspaceService = Depends(get_workspace_service),
    jobs: JobService = Depends(get_job_service),
) -> WorkingTemplateSnapshotModel:
    validation = workspace.validation(payload.template)
    if validation.has_error:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail={"message": "Working template has validation errors.", "issues": validation.model_dump()["issues"]})
    workspace.save_template(payload.template)
    return workspace.snapshot(jobs.current_status, jobs.active_job_id)


@router.post("/working-template/backgrounds/upload", response_model=BackgroundUploadResponseModel)
def upload_background(
    file: UploadFile = File(...),
    workspace: WorkspaceService = Depends(get_workspace_service),
) -> BackgroundUploadResponseModel:
    return BackgroundUploadResponseModel(background_scene_id=workspace.add_background(file))


@router.delete("/working-template/backgrounds/{background_scene_id}", response_model=BackgroundDeleteResponseModel)
def delete_background(
    background_scene_id: str,
    workspace: WorkspaceService = Depends(get_workspace_service),
) -> BackgroundDeleteResponseModel:
    active_id = workspace.delete_background(background_scene_id)
    return BackgroundDeleteResponseModel(active_background_scene_id=active_id)


@router.post("/working-template/validate", response_model=ValidationResultModel)
def validate_working_template(
    payload: ValidateTemplateRequestModel,
    workspace: WorkspaceService = Depends(get_workspace_service),
) -> ValidationResultModel:
    return workspace.validation(payload.template)


@router.post("/working-template/preview", response_model=PreviewResponseModel)
def preview_working_template(
    payload: PreviewRequestModel,
    workspace: WorkspaceService = Depends(get_workspace_service),
) -> PreviewResponseModel:
    workspace.preview_scene(payload.background_scene_id)
    return PreviewResponseModel(preview_url="/api/working-template/preview/current.png")


@router.get("/working-template/preview/current.png")
def get_preview_image(
    settings: Settings = Depends(get_settings_dep),
) -> FileResponse:
    return FileResponse(settings.previews_root / "current.png", media_type="image/png")


@router.get("/runtime/{asset_path:path}")
def get_runtime_asset(
    asset_path: str,
    settings: Settings = Depends(get_settings_dep),
) -> FileResponse:
    candidate = (settings.runtime_root / asset_path).resolve()
    runtime_root = settings.runtime_root.resolve()
    if runtime_root not in candidate.parents and candidate != runtime_root:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Runtime asset not found.")
    if not candidate.is_file():
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Runtime asset not found.")
    return FileResponse(candidate)


@router.post("/jobs", response_model=JobCreateResponseModel)
def create_job(
    payload: JobCreateRequestModel,
    jobs: JobService = Depends(get_job_service),
) -> JobCreateResponseModel:
    if payload.count < 1:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="count must be an integer >= 1")
    job = jobs.start_job(payload.count)
    return JobCreateResponseModel(id=job.id, status="running")


@router.get("/jobs/{job_id}", response_model=JobResponseModel)
def get_job(job_id: str, jobs: JobService = Depends(get_job_service)) -> JobResponseModel:
    return jobs.read_job(job_id)


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str, jobs: JobService = Depends(get_job_service)) -> dict[str, bool]:
    jobs.cancel_job(job_id)
    return {"ok": True}


@router.post("/jobs/{job_id}/export", response_model=ExportResponseModel)
def export_job(
    job_id: str,
    payload: ExportRequestModel,
    jobs: JobService = Depends(get_job_service),
) -> ExportResponseModel:
    return jobs.export_job(job_id, payload.format)


@router.get("/jobs/{job_id}/download")
def download_job(job_id: str, format: str = "yolo", jobs: JobService = Depends(get_job_service)) -> FileResponse:
    return FileResponse(jobs.download_path(job_id, format), media_type="application/zip", filename=f"{job_id}_{format}.zip")
