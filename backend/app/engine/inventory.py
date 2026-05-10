from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.app.models.contracts import AssetClassModel, AssetInventoryModel, AssetSubtypeModel


SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}


@dataclass(frozen=True, slots=True)
class AssetFile:
    class_name: str
    subtype_name: str | None
    path: Path


def iter_asset_files(objects_dir: Path) -> list[AssetFile]:
    asset_files: list[AssetFile] = []
    if not objects_dir.exists():
        return asset_files

    for class_dir in sorted(path for path in objects_dir.iterdir() if path.is_dir()):
        for path in sorted(class_dir.iterdir()):
            if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES:
                asset_files.append(AssetFile(class_name=class_dir.name, subtype_name=None, path=path))
            elif path.is_dir():
                for file_path in sorted(path.iterdir()):
                    if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES:
                        asset_files.append(
                            AssetFile(class_name=class_dir.name, subtype_name=path.name, path=file_path)
                        )
    return asset_files


def scan_inventory(objects_dir: Path) -> AssetInventoryModel:
    classes: list[AssetClassModel] = []
    if not objects_dir.exists():
        return AssetInventoryModel(classes=[])

    for class_dir in sorted(path for path in objects_dir.iterdir() if path.is_dir()):
        subtypes: list[AssetSubtypeModel] = []
        root_file_count = 0
        for child in sorted(class_dir.iterdir()):
            if child.is_file() and child.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES:
                root_file_count += 1
            elif child.is_dir():
                count = sum(
                    1
                    for path in child.iterdir()
                    if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
                )
                subtypes.append(AssetSubtypeModel(name=child.name, file_count=count))
        classes.append(AssetClassModel(name=class_dir.name, root_file_count=root_file_count, subtypes=subtypes))
    return AssetInventoryModel(classes=classes)
