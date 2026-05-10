from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Settings:
    backend_root: Path
    app_resources_root: Path
    runtime_root: Path
    default_background_name: str = "white.jpg"
    allowed_asset_suffixes: tuple[str, ...] = (".png", ".jpg", ".jpeg")
    allowed_background_suffixes: tuple[str, ...] = (".png", ".jpg", ".jpeg")
    allowed_archive_suffixes: tuple[str, ...] = (".zip", ".rar")

    @property
    def default_background_path(self) -> Path:
        return self.app_resources_root / "default_backgrounds" / self.default_background_name

    @property
    def assets_root(self) -> Path:
        return self.runtime_root / "assets"

    @property
    def backgrounds_root(self) -> Path:
        return self.runtime_root / "backgrounds"

    @property
    def previews_root(self) -> Path:
        return self.runtime_root / "previews"

    @property
    def jobs_root(self) -> Path:
        return self.runtime_root / "jobs"

    @property
    def template_path(self) -> Path:
        return self.runtime_root / "template.json"


def get_settings() -> Settings:
    backend_root = Path(__file__).resolve().parents[2]
    return Settings(
        backend_root=backend_root,
        app_resources_root=backend_root / "app_resources",
        runtime_root=backend_root / "tmp" / "synth_app",
    )
