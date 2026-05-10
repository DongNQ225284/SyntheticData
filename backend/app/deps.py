from __future__ import annotations

from functools import lru_cache

from backend.app.core.settings import Settings, get_settings
from backend.app.services.job_service import JobService
from backend.app.services.workspace_service import WorkspaceService


@lru_cache
def get_settings_dep() -> Settings:
    return get_settings()


@lru_cache
def get_workspace_service() -> WorkspaceService:
    service = WorkspaceService(get_settings_dep())
    service.initialize()
    return service


@lru_cache
def get_job_service() -> JobService:
    return JobService(get_settings_dep(), get_workspace_service())
