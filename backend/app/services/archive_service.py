from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable

from fastapi import HTTPException, UploadFile

from backend.app.core.settings import Settings


SYSTEM_ARTIFACT_NAMES = {".DS_Store", "Thumbs.db"}
SYSTEM_ARTIFACT_PREFIXES = {"__MACOSX"}
VALID_NAME_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789_-")


def _invalid_name(name: str) -> bool:
    return not name or name.startswith(".") or any(char not in VALID_NAME_CHARS for char in name)


def _clean_members(members: Iterable[str]) -> list[Path]:
    paths: list[Path] = []
    for member in members:
        candidate = Path(member)
        if not candidate.name:
            continue
        if any(part in SYSTEM_ARTIFACT_PREFIXES for part in candidate.parts):
            continue
        if candidate.name in SYSTEM_ARTIFACT_NAMES:
            continue
        paths.append(candidate)
    return paths


def _strip_wrapper(paths: list[Path]) -> list[Path]:
    top_levels = {path.parts[0] for path in paths if path.parts}
    if len(top_levels) != 1:
        return paths
    wrapper = next(iter(top_levels))
    wrapped = [Path(*path.parts[1:]) for path in paths if len(path.parts) > 1]
    return wrapped or paths


def _raise(status_code: int, detail: str) -> None:
    raise HTTPException(status_code=status_code, detail=detail)


def _validate_tree(extracted_root: Path, settings: Settings) -> None:
    valid_class_dirs = [path for path in extracted_root.iterdir() if path.is_dir()]
    if not valid_class_dirs:
        _raise(400, "Archive root must contain class directories only.")
    if any(path.is_file() for path in extracted_root.iterdir()):
        _raise(400, "Archive root must contain class directories only.")

    valid_image_count = 0
    for class_dir in sorted(valid_class_dirs):
        if _invalid_name(class_dir.name):
            _raise(400, f"Invalid class name: '{class_dir.name}'. Use lowercase letters, numbers, '-' or '_'.")
        for child in sorted(class_dir.iterdir()):
            if child.name.startswith("."):
                _raise(400, f"Unsupported hidden path: {child.relative_to(extracted_root)}")
            if child.is_file():
                if child.suffix.lower() not in settings.allowed_asset_suffixes:
                    _raise(400, f"Unsupported asset file: {child.relative_to(extracted_root)}")
                valid_image_count += 1
                continue
            if _invalid_name(child.name):
                _raise(400, f"Invalid subtype name: '{child.name}'. Use lowercase letters, numbers, '-' or '_'.")
            for nested in sorted(child.iterdir()):
                if nested.is_dir():
                    _raise(400, f"Invalid subtype directory depth under class '{class_dir.name}'.")
                if nested.suffix.lower() not in settings.allowed_asset_suffixes:
                    _raise(400, f"Unsupported asset file: {nested.relative_to(extracted_root)}")
                valid_image_count += 1
    if valid_image_count == 0:
        _raise(400, "No valid asset images found in archive.")


def _extract_zip(archive_path: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        cleaned_members = _clean_members(archive.namelist())
        members = _strip_wrapper(cleaned_members)
        if not members:
            _raise(400, "Archive root must contain class directories only.")
        wrapper_name = None
        if cleaned_members:
            top_levels = {path.parts[0] for path in cleaned_members if path.parts}
            if len(top_levels) == 1:
                wrapper_name = next(iter(top_levels))
        for info in archive.infolist():
            raw_path = Path(info.filename)
            if any(part in SYSTEM_ARTIFACT_PREFIXES for part in raw_path.parts):
                continue
            if raw_path.name in SYSTEM_ARTIFACT_NAMES or not raw_path.name:
                continue
            path = raw_path
            if wrapper_name is not None and raw_path.parts and raw_path.parts[0] == wrapper_name:
                path = Path(*raw_path.parts[1:])
            if not path.parts:
                continue
            target = destination / path
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)


def _extract_rar(archive_path: Path, destination: Path) -> None:
    try:
        import rarfile  # type: ignore
    except ImportError as exc:
        raise HTTPException(
            status_code=400,
            detail="Unsupported archive format. Only .zip is available in this local environment because .rar extraction support is missing.",
        ) from exc

    with rarfile.RarFile(archive_path) as archive:
        cleaned_members = _clean_members(archive.namelist())
        members = _strip_wrapper(cleaned_members)
        if not members:
            _raise(400, "Archive root must contain class directories only.")
        wrapper_name = None
        if cleaned_members:
            top_levels = {path.parts[0] for path in cleaned_members if path.parts}
            if len(top_levels) == 1:
                wrapper_name = next(iter(top_levels))
        for info in archive.infolist():
            raw_path = Path(info.filename)
            if any(part in SYSTEM_ARTIFACT_PREFIXES for part in raw_path.parts):
                continue
            if raw_path.name in SYSTEM_ARTIFACT_NAMES or not raw_path.name:
                continue
            path = raw_path
            if wrapper_name is not None and raw_path.parts and raw_path.parts[0] == wrapper_name:
                path = Path(*raw_path.parts[1:])
            if not path.parts:
                continue
            target = destination / path
            if info.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)


def extract_and_validate_archive(upload: UploadFile, settings: Settings) -> Path:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in settings.allowed_archive_suffixes:
        _raise(400, "Unsupported archive format. Only .zip and .rar are accepted.")

    temp_dir = Path(tempfile.mkdtemp(prefix="synth_upload_"))
    archive_path = temp_dir / f"upload{suffix}"
    with archive_path.open("wb") as output:
        upload.file.seek(0)
        shutil.copyfileobj(upload.file, output)

    extracted_root = temp_dir / "extracted"
    extracted_root.mkdir(parents=True, exist_ok=True)
    if suffix == ".zip":
        _extract_zip(archive_path, extracted_root)
    else:
        _extract_rar(archive_path, extracted_root)
    _validate_tree(extracted_root, settings)
    return extracted_root
