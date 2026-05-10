from __future__ import annotations

import json
import shutil
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import HTTPException

from backend.app.core.settings import Settings
from backend.app.engine.generation import generate_dataset
from backend.app.engine.coco_converter import convert_to_coco
from backend.app.models.contracts import ExportResponseModel, JobResponseModel, TemplateModel
from backend.app.services.workspace_service import WorkspaceService


@dataclass(slots=True)
class JobMeta:
    id: str
    status: str
    count: int
    generated_count: int
    created_at: str
    updated_at: str
    zip_ready: bool
    download_url: str | None
    error: str | None
    seed: int


class JobService:
    def __init__(self, settings: Settings, workspace: WorkspaceService) -> None:
        self.settings = settings
        self.workspace = workspace
        self._lock = threading.Lock()
        self._cancel_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._active_job_id: str | None = None

    @property
    def active_job_id(self) -> str | None:
        return self._active_job_id

    @property
    def current_status(self) -> str:
        if self._active_job_id is None:
            return "idle"
        try:
            return self.read_job(self._active_job_id).status
        except HTTPException:
            return "idle"

    def _job_dir(self, job_id: str) -> Path:
        return self.settings.jobs_root / job_id

    def _job_meta_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "meta.json"

    def _write_meta(self, meta: JobMeta) -> None:
        self._job_dir(meta.id).mkdir(parents=True, exist_ok=True)
        self._job_meta_path(meta.id).write_text(json.dumps(asdict(meta), indent=2) + "\n", encoding="utf-8")

    def _read_meta(self, job_id: str) -> JobMeta:
        meta_path = self._job_meta_path(job_id)
        if not meta_path.is_file():
            raise HTTPException(status_code=404, detail="Job not found.")
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
        return JobMeta(**payload)

    def _touch_meta(self, job_id: str, **updates: object) -> JobMeta:
        meta = self._read_meta(job_id)
        for key, value in updates.items():
            setattr(meta, key, value)
        meta.updated_at = datetime.now(timezone.utc).isoformat()
        self._write_meta(meta)
        return meta

    def _next_job_id(self) -> str:
        date_prefix = datetime.now(timezone.utc).strftime("%Y%m%d")
        index = 1
        while True:
            candidate = f"job_{date_prefix}_{index:03d}"
            if not self._job_dir(candidate).exists():
                return candidate
            index += 1

    def start_job(self, count: int) -> JobResponseModel:
        with self._lock:
            if self._active_job_id is not None and self.read_job(self._active_job_id).status == "running":
                raise HTTPException(
                    status_code=409,
                    detail="A generate job is already running. Please wait until it finishes or reset the workspace.",
                )

            template = self.workspace.load_template()
            validation = self.workspace.validation(template)
            if validation.has_error:
                raise HTTPException(
                    status_code=400,
                    detail="Working template is not ready to generate. Please fix validation errors in the Editor.",
                )

            now = datetime.now(timezone.utc).isoformat()
            job_id = self._next_job_id()
            meta = JobMeta(
                id=job_id,
                status="running",
                count=count,
                generated_count=0,
                created_at=now,
                updated_at=now,
                zip_ready=False,
                download_url=None,
                error=None,
                seed=int(datetime.now().timestamp()),
            )
            self._write_meta(meta)
            self._cancel_event = threading.Event()
            self._active_job_id = job_id
            self._thread = threading.Thread(target=self._run_job, args=(job_id, template), daemon=True)
            self._thread.start()
            return self.read_job(job_id)

    def _run_job(self, job_id: str, template: TemplateModel) -> None:
        job_dir = self._job_dir(job_id)
        output_dir = job_dir / "output"
        try:
            generate_dataset(
                template=template,
                assets_root=self.settings.assets_root,
                runtime_root=self.settings.runtime_root,
                output_dir=output_dir,
                count=self._read_meta(job_id).count,
                seed=self._read_meta(job_id).seed,
                job_blocker=self._cancel_event.is_set,
                progress_callback=lambda generated: self._touch_meta(job_id, generated_count=generated),
            )
            if self._cancel_event.is_set():
                self._touch_meta(job_id, status="cancelled")
            else:
                self._touch_meta(job_id, status="succeeded")
        except Exception as exc:
            status = "cancelled" if self._cancel_event.is_set() else "failed"
            self._touch_meta(job_id, status=status, error=str(exc))
        finally:
            with self._lock:
                if self._active_job_id == job_id:
                    self._active_job_id = None

    def read_job(self, job_id: str) -> JobResponseModel:
        meta = self._read_meta(job_id)
        return JobResponseModel(
            id=meta.id,
            status=meta.status,  # type: ignore[arg-type]
            count=meta.count,
            generated_count=meta.generated_count,
            created_at=datetime.fromisoformat(meta.created_at),
            updated_at=datetime.fromisoformat(meta.updated_at),
            zip_ready=meta.zip_ready,
            download_url=meta.download_url,
            error=meta.error,
        )

    def cancel_job(self, job_id: str) -> None:
        meta = self._read_meta(job_id)
        if meta.status == "running":
            self._cancel_event.set()
            self._touch_meta(job_id, status="cancelled")

    def cancel_active(self) -> None:
        if self._active_job_id is not None:
            self.cancel_job(self._active_job_id)

    def export_job(self, job_id: str, format: str = "yolo") -> ExportResponseModel:
        meta = self._read_meta(job_id)
        if meta.status != "succeeded":
            raise HTTPException(status_code=400, detail="Job output is not ready for export.")
        export_dir = self._job_dir(job_id) / f"export_{format}"
        export_dir.mkdir(parents=True, exist_ok=True)
        zip_path = export_dir / "dataset.zip"
        if not zip_path.exists():
            output_dir = self._job_dir(job_id) / "output"
            if format == "coco":
                coco_dir = export_dir / "coco_output"
                convert_to_coco(output_dir, coco_dir)
                with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
                    for path in sorted(coco_dir.rglob("*")):
                        if path.is_file():
                            archive.write(path, path.relative_to(coco_dir))
            else:
                with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
                    for path in sorted(output_dir.rglob("*")):
                        if path.is_file():
                            archive.write(path, path.relative_to(output_dir))
        download_url = f"/api/jobs/{job_id}/download?format={format}"
        self._touch_meta(job_id, zip_ready=True, download_url=download_url)
        return ExportResponseModel(download_url=download_url)

    def download_path(self, job_id: str, format: str = "yolo") -> Path:
        meta = self._read_meta(job_id)
        if meta.status != "succeeded":
            raise HTTPException(status_code=400, detail="Job has not succeeded.")
        zip_path = self._job_dir(job_id) / f"export_{format}" / "dataset.zip"
        if not zip_path.is_file():
            raise HTTPException(status_code=404, detail="Export zip not found.")
        return zip_path

    def hard_reset(self) -> None:
        self.cancel_active()
        if self.settings.jobs_root.exists():
            shutil.rmtree(self.settings.jobs_root)
        self._active_job_id = None
