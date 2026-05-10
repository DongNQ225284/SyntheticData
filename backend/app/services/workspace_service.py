from __future__ import annotations

import json
import shutil
from pathlib import Path

import time
import random
from fastapi import HTTPException, UploadFile

from backend.app.core.settings import Settings
from backend.app.engine.inventory import scan_inventory
from backend.app.engine.generation import generate_single_sample, load_assets
from backend.app.engine.template_defaults import default_scene, default_template, next_scene_id
from backend.app.engine.validation import validate_template
from backend.app.models.contracts import AssetInventoryModel, TemplateModel, WorkingTemplateSnapshotModel
from backend.app.services.archive_service import extract_and_validate_archive


class WorkspaceService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def initialize(self) -> None:
        self.settings.app_resources_root.mkdir(parents=True, exist_ok=True)
        self.settings.runtime_root.mkdir(parents=True, exist_ok=True)
        self.settings.assets_root.mkdir(parents=True, exist_ok=True)
        self.settings.backgrounds_root.mkdir(parents=True, exist_ok=True)
        self.settings.previews_root.mkdir(parents=True, exist_ok=True)
        self.settings.jobs_root.mkdir(parents=True, exist_ok=True)
        self._ensure_default_template()

    def _ensure_default_template(self) -> None:
        self._ensure_default_background()
        if not self.settings.template_path.exists():
            self.save_template(default_template())

    def _ensure_default_background(self) -> None:
        self.settings.backgrounds_root.mkdir(parents=True, exist_ok=True)
        target = self.settings.backgrounds_root / self.settings.default_background_name
        if not self.settings.default_background_path.exists():
            raise RuntimeError(f"Default background missing: {self.settings.default_background_path}")
        shutil.copy2(self.settings.default_background_path, target)

    def reset(self) -> None:
        if self.settings.runtime_root.exists():
            shutil.rmtree(self.settings.runtime_root)
        self.initialize()

    def ingest_assets_archive(self, upload: UploadFile) -> AssetInventoryModel:
        extracted_root = extract_and_validate_archive(upload, self.settings)
        self.reset()
        for class_dir in extracted_root.iterdir():
            if class_dir.is_dir():
                shutil.copytree(class_dir, self.settings.assets_root / class_dir.name)
        self.save_template(default_template())
        return self.inventory()

    def inventory(self) -> AssetInventoryModel:
        return scan_inventory(self.settings.assets_root)

    def load_template(self) -> TemplateModel:
        if not self.settings.template_path.exists():
            template = default_template()
            self.save_template(template)
            return template
        payload = json.loads(self.settings.template_path.read_text(encoding="utf-8"))
        return TemplateModel.model_validate(payload)

    def save_template(self, template: TemplateModel) -> None:
        self.settings.template_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings.template_path.write_text(
            json.dumps(template.model_dump(by_alias=True), indent=2) + "\n",
            encoding="utf-8",
        )

    def validation(self, template: TemplateModel | None = None):
        current = template or self.load_template()
        return validate_template(current, self.inventory(), self.settings.runtime_root)

    def snapshot(self, job_status: str, active_job_id: str | None) -> WorkingTemplateSnapshotModel:
        template = self.load_template()
        validation = self.validation(template)
        return WorkingTemplateSnapshotModel(
            template=template,
            validation=validation,
            inventory=self.inventory(),
            job={"status": job_status, "active_job_id": active_job_id},
        )

    def add_background(self, upload: UploadFile) -> str:
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix not in self.settings.allowed_background_suffixes:
            raise HTTPException(status_code=400, detail="Unsupported background file type.")

        template = self.load_template()
        existing_ids = [scene.id for scene in template.background_scenes]
        scene_id = next_scene_id(existing_ids)
        filename = self._next_background_filename(Path(upload.filename or f"{scene_id}{suffix}").stem, suffix)
        target = self.settings.backgrounds_root / filename
        with target.open("wb") as output:
            upload.file.seek(0)
            shutil.copyfileobj(upload.file, output)

        base_scene = template.background_scenes[0]
        template.background_scenes.append(
            default_scene(
                background_id=scene_id,
                name=Path(filename).stem,
                image_path=f"backgrounds/{filename}",
            ).model_copy(
                update={
                    "canvas_size_range": base_scene.canvas_size_range,
                    "scene_weight": 1,
                }
            )
        )
        self.save_template(template)
        return scene_id

    def _next_background_filename(self, stem: str, suffix: str) -> str:
        candidate = f"{stem}{suffix}"
        index = 1
        while (self.settings.backgrounds_root / candidate).exists():
            candidate = f"{stem}_{index}{suffix}"
            index += 1
        return candidate

    def delete_background(self, scene_id: str) -> str:
        template = self.load_template()
        if len(template.background_scenes) <= 1:
            raise HTTPException(status_code=400, detail="The last remaining scene cannot be deleted.")
            
        target_scene = next((s for s in template.background_scenes if s.id == scene_id), None)
        if not target_scene:
            raise HTTPException(status_code=404, detail="Background scene not found.")

        # Delete physical image file if it exists
        try:
            image_path = self.settings.runtime_root / target_scene.background.image_path
            if image_path.exists():
                image_path.unlink()
        except Exception:
            pass

        next_scenes = [scene for scene in template.background_scenes if scene.id != scene_id]
        template.background_scenes = next_scenes
        self.save_template(template)
        return next_scenes[0].id

    def preview_scene(self, scene_id: str) -> Path:
        template = self.load_template()
        scene = next((item for item in template.background_scenes if item.id == scene_id), None)
        if scene is None:
            raise HTTPException(status_code=404, detail="Preview could not be generated for the selected scene.")
        
        assets, _ = load_assets(self.settings.assets_root)
        rng = random.Random(int(time.time() * 1000))
        canvas, _, _, _ = generate_single_sample(scene, assets, self.settings.runtime_root, rng)

        preview_path = self.settings.previews_root / "current.png"
        self.settings.previews_root.mkdir(parents=True, exist_ok=True)
        canvas.save(preview_path)
        return preview_path
