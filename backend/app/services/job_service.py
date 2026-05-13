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
from backend.app.models.contracts import ExportResponseModel, JobResponseModel, SplitConfig, TemplateModel
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

    def _build_split_assignment(
        self, image_names: list[str], split: SplitConfig
    ) -> dict[str, str]:
        """Deterministically assign each image to a split."""
        import random as _random

        total = len(image_names)
        if total == 0:
            return {}

        # Normalise ratios so they always sum to 1
        raw_total = split.train + split.valid + split.test
        if raw_total <= 0:
            train_r, valid_r = 1.0, 0.0
        else:
            train_r = split.train / raw_total
            valid_r = split.valid / raw_total

        n_valid = round(total * valid_r)
        n_test = round(total * (1.0 - train_r - valid_r))
        n_train = total - n_valid - n_test

        # Shuffle deterministically using the job id as seed
        rng = _random.Random(self._active_job_id or "seed")
        shuffled = list(image_names)
        rng.shuffle(shuffled)

        assignment: dict[str, str] = {}
        for name in shuffled[:n_train]:
            assignment[name] = "train"
        for name in shuffled[n_train : n_train + n_valid]:
            assignment[name] = "valid"
        for name in shuffled[n_train + n_valid :]:
            assignment[name] = "test"
        return assignment

    def export_job(self, job_id: str, format: str = "yolo", split: SplitConfig | None = None) -> ExportResponseModel:
        if split is None:
            split = SplitConfig()
        meta = self._read_meta(job_id)
        if meta.status != "succeeded":
            raise HTTPException(status_code=400, detail="Job output is not ready for export.")

        use_splits = not (split.valid == 0.0 and split.test == 0.0)

        # Build a stable cache key that includes the split ratios
        split_key = f"{split.train:.4f}_{split.valid:.4f}_{split.test:.4f}"
        export_dir = self._job_dir(job_id) / f"export_{format}_{split_key}"
        export_dir.mkdir(parents=True, exist_ok=True)
        zip_path = export_dir / "dataset.zip"

        if not zip_path.exists():
            output_dir = self._job_dir(job_id) / "output"

            # Build split assignment from the available images
            images_src = output_dir / "images"
            image_names = sorted(p.name for p in images_src.iterdir() if p.is_file()) if images_src.exists() else []
            assignment = self._build_split_assignment(image_names, split) if use_splits else {}

            if format == "coco":
                coco_dir = export_dir / "coco_output"
                convert_to_coco(output_dir, coco_dir, split_assignment=assignment if use_splits else None)
                with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
                    for path in sorted(coco_dir.rglob("*")):
                        if path.is_file():
                            archive.write(path, path.relative_to(coco_dir))

            else:  # YOLO
                if use_splits:
                    yolo_dir = export_dir / "yolo_output"
                    yolo_dir.mkdir(parents=True, exist_ok=True)
                    self._build_yolo_split(output_dir, yolo_dir, assignment, split)
                    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
                        for path in sorted(yolo_dir.rglob("*")):
                            if path.is_file():
                                archive.write(path, path.relative_to(yolo_dir))
                else:
                    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
                        for path in sorted(output_dir.rglob("*")):
                            if path.is_file():
                                archive.write(path, path.relative_to(output_dir))

        download_url = f"/api/jobs/{job_id}/download?format={format}&split_key={split_key}"
        self._touch_meta(job_id, zip_ready=True, download_url=download_url)
        return ExportResponseModel(download_url=download_url)

    def _build_yolo_split(
        self,
        output_dir: Path,
        yolo_dir: Path,
        assignment: dict[str, str],
        split: SplitConfig,
    ) -> None:
        """Arrange images and labels into per-split subdirectories for YOLO."""
        import shutil as _shutil

        for split_name in ("train", "valid", "test"):
            (yolo_dir / "images" / split_name).mkdir(parents=True, exist_ok=True)
            (yolo_dir / "labels" / split_name).mkdir(parents=True, exist_ok=True)

        images_src = output_dir / "images"
        labels_src = output_dir / "labels"

        for image_name, split_name in assignment.items():
            src_img = images_src / image_name
            if src_img.exists():
                _shutil.copy2(src_img, yolo_dir / "images" / split_name / image_name)
            stem = Path(image_name).stem
            label_name = f"{stem}.txt"
            src_lbl = labels_src / label_name
            if src_lbl.exists():
                _shutil.copy2(src_lbl, yolo_dir / "labels" / split_name / label_name)

        # Write data.yaml
        class_names: list[str] = []
        data_yaml_src = output_dir / "data.yaml"
        if data_yaml_src.exists():
            try:
                # The generation engine writes class names as:
                #   names:
                #     0: classname
                # Parse manually to avoid pyyaml dependency.
                raw_text = data_yaml_src.read_text(encoding="utf-8")
                in_names = False
                names_dict: dict[int, str] = {}
                for raw_line in raw_text.splitlines():
                    if raw_line.strip().startswith("names:"):
                        in_names = True
                        continue
                    if in_names:
                        stripped = raw_line.strip()
                        if not stripped or stripped.startswith("#"):
                            continue
                        # Lines like "  0: classname"
                        if ":" in stripped and not stripped.startswith("-"):
                            idx_str, _, val = stripped.partition(":")
                            try:
                                names_dict[int(idx_str.strip())] = val.strip()
                            except ValueError:
                                in_names = False
                        else:
                            in_names = False
                class_names = [names_dict[k] for k in sorted(names_dict.keys())]
            except Exception:
                pass


        raw_total = split.train + split.valid + split.test
        if raw_total <= 0:
            raw_total = 1.0
        train_pct = split.train / raw_total
        valid_pct = split.valid / raw_total
        test_pct = split.test / raw_total

        lines = [
            "path: .",
        ]
        if train_pct > 0:
            lines.append("train: images/train")
        if valid_pct > 0:
            lines.append("val: images/valid")
        if test_pct > 0:
            lines.append("test: images/test")
        lines += [
            f"nc: {len(class_names)}",
            "names:",
            *[f"  {i}: {name}" for i, name in enumerate(class_names)],
        ]
        (yolo_dir / "data.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def download_path(self, job_id: str, format: str = "yolo", split_key: str = "1.0000_0.0000_0.0000") -> Path:
        meta = self._read_meta(job_id)
        if meta.status != "succeeded":
            raise HTTPException(status_code=400, detail="Job has not succeeded.")
        zip_path = self._job_dir(job_id) / f"export_{format}_{split_key}" / "dataset.zip"
        if not zip_path.is_file():
            raise HTTPException(status_code=404, detail="Export zip not found.")
        return zip_path

    def hard_reset(self) -> None:
        self.cancel_active()
        if self.settings.jobs_root.exists():
            shutil.rmtree(self.settings.jobs_root)
        self._active_job_id = None
