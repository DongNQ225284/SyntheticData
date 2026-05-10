from __future__ import annotations

from pathlib import Path

from backend.app.models.contracts import AssetInventoryModel, TemplateModel, ValidationIssueModel, ValidationResultModel


VALID_ANCHORS = {
    "top_left",
    "top_center",
    "top_right",
    "center_left",
    "center",
    "center_right",
    "bottom_left",
    "bottom_center",
    "bottom_right",
}


def _error(path: str, message: str) -> ValidationIssueModel:
    return ValidationIssueModel(severity="error", path=path, message=message)


def _warning(path: str, message: str) -> ValidationIssueModel:
    return ValidationIssueModel(severity="warning", path=path, message=message)


def validate_template(
    template: TemplateModel,
    inventory: AssetInventoryModel,
    runtime_root: Path,
) -> ValidationResultModel:
    issues: list[ValidationIssueModel] = []
    class_names = {asset_class.name for asset_class in inventory.classes}
    subtype_map = {
        asset_class.name: {subtype.name for subtype in asset_class.subtypes}
        for asset_class in inventory.classes
    }

    if not template.background_scenes:
        issues.append(_error("background_scenes", "background_scenes must be a non-empty list"))

    total_blocks = 0
    scene_weights: list[float] = []
    for scene_index, scene in enumerate(template.background_scenes):
        scene_path = f"background_scenes[{scene_index}]"
        scene_weights.append(scene.scene_weight)
        if scene.scene_weight <= 0:
            issues.append(_error(f"{scene_path}.scene_weight", "scene_weight must be > 0"))

        width_range = scene.canvas_size_range.width
        height_range = scene.canvas_size_range.height
        if width_range[0] > width_range[1]:
            issues.append(_error(f"{scene_path}.canvas_size_range.width", "min must be <= max"))
        if height_range[0] > height_range[1]:
            issues.append(_error(f"{scene_path}.canvas_size_range.height", "min must be <= max"))

        background_file = runtime_root / scene.background.image_path
        if not background_file.is_file():
            issues.append(
                _error(
                    f"{scene_path}.background.image_path",
                    "background.image_path must point to an existing file on disk",
                )
            )

        if not scene.blocks:
            issues.append(_warning(f"{scene_path}.blocks", "scene has zero blocks"))

        for block_index, block in enumerate(scene.blocks):
            total_blocks += 1
            block_path = f"{scene_path}.blocks[{block_index}]"
            x, y, width, height = block.bbox
            if x < 0 or x > 1 or y < 0 or y > 1:
                issues.append(_error(f"{block_path}.bbox", "x and y must be in [0, 1]"))
            if width <= 0 or height <= 0:
                issues.append(_error(f"{block_path}.bbox", "w and h must be > 0"))
            if x + width > 1 or y + height > 1:
                issues.append(_error(f"{block_path}.bbox", "bbox must stay inside the page"))
            if 0 < width <= 0.03 or 0 < height <= 0.03:
                issues.append(_warning(f"{block_path}.bbox", "bbox is very small"))
            if block.class_name not in class_names:
                issues.append(_error(f"{block_path}.class", f"block class '{block.class_name}' not found in inventory"))
            known_subtypes = subtype_map.get(block.class_name, set())
            for subtype in block.allowed_subtypes:
                if subtype not in known_subtypes:
                    issues.append(
                        _error(
                            f"{block_path}.allowed_subtypes",
                            f"subtype '{subtype}' does not belong to class '{block.class_name}'",
                        )
                    )
            if not block.allowed_subtypes:
                issues.append(_warning(f"{block_path}.allowed_subtypes", "allowed_subtypes is empty"))
            if not 1 <= block.capacity <= 10:
                issues.append(_error(f"{block_path}.capacity", "capacity must be integer in 1..10"))
            if block.skip_prob < 0 or block.skip_prob >= 1:
                issues.append(_error(f"{block_path}.skip_prob", "skip_prob must satisfy 0 <= value < 1"))
            elif block.skip_prob > 0.75:
                issues.append(_warning(f"{block_path}.skip_prob", "skip_prob is very high"))
            if block.position_anchor is not None and block.position_anchor not in VALID_ANCHORS:
                issues.append(_error(f"{block_path}.position_anchor", "invalid position_anchor"))
            if block.augmentation.rotation_max < 0:
                issues.append(_error(f"{block_path}.augmentation.rotation_max", "rotation_max must be >= 0"))
            if block.augmentation.blur_max < 0:
                issues.append(_error(f"{block_path}.augmentation.blur_max", "blur_max must be >= 0"))
            if block.augmentation.noise_max < 0:
                issues.append(_error(f"{block_path}.augmentation.noise_max", "noise_max must be >= 0"))
            if block.augmentation.rotation_max > 30:
                issues.append(_warning(f"{block_path}.augmentation.rotation_max", "rotation_max is unusually large"))
            if block.augmentation.blur_max > 4:
                issues.append(_warning(f"{block_path}.augmentation.blur_max", "blur_max is unusually large"))
            if block.augmentation.noise_max > 0.2:
                issues.append(_warning(f"{block_path}.augmentation.noise_max", "noise_max is unusually large"))

    if total_blocks == 0:
        issues.append(_warning("background_scenes", "whole template has zero blocks"))
    if scene_weights:
        max_weight = max(scene_weights)
        min_weight = min(scene_weights)
        if min_weight > 0 and max_weight / min_weight >= 10:
            issues.append(_warning("background_scenes", "scene weights are very imbalanced"))

    has_error = any(issue.severity == "error" for issue in issues)
    has_warning = any(issue.severity == "warning" for issue in issues)
    return ValidationResultModel(issues=issues, has_error=has_error, has_warning=has_warning)
