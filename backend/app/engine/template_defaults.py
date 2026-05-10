from __future__ import annotations

from backend.app.models.contracts import (
    AssetInventoryModel,
    AugmentationModel,
    BackgroundModel,
    BackgroundSceneModel,
    BlockModel,
    CanvasSizeRangeModel,
    TemplateModel,
)


DEFAULT_WIDTH_RANGE = (3200, 3500)
DEFAULT_HEIGHT_RANGE = (2000, 2400)


def next_scene_id(scene_ids: list[str]) -> str:
    index = 1
    used = set(scene_ids)
    while True:
        candidate = f"bg_{index:03d}"
        if candidate not in used:
            return candidate
        index += 1


def next_block_id(block_ids: list[str]) -> str:
    index = 1
    used = set(block_ids)
    while True:
        candidate = f"block_{index:03d}"
        if candidate not in used:
            return candidate
        index += 1


def default_scene(background_id: str, name: str, image_path: str) -> BackgroundSceneModel:
    return BackgroundSceneModel(
        id=background_id,
        scene_weight=1,
        canvas_size_range=CanvasSizeRangeModel(width=DEFAULT_WIDTH_RANGE, height=DEFAULT_HEIGHT_RANGE),
        background=BackgroundModel(id=background_id, name=name, image_path=image_path),
        blocks=[],
        allow_overlap=True,
    )


def default_template() -> TemplateModel:
    return TemplateModel(
        version=2,
        name="new_layout_v2",
        description="Template with multiple background scenes.",
        background_scenes=[default_scene("bg_001", "white", "backgrounds/white.jpg")],
    )


def default_block(
    block_id: str,
    bbox: tuple[float, float, float, float],
    inventory: AssetInventoryModel,
) -> BlockModel:
    default_class = inventory.classes[0].name if inventory.classes else "figure"
    default_subtypes = []
    for asset_class in inventory.classes:
        if asset_class.name == default_class:
            default_subtypes = [subtype.name for subtype in asset_class.subtypes]
            break
    return BlockModel(
        id=block_id,
        bbox=bbox,
        class_name=default_class,
        allowed_subtypes=default_subtypes,
        capacity=1,
        skip_prob=0,
        position_anchor=None,
        augmentation=AugmentationModel(rotation_max=0, blur_max=0, noise_max=0),
    )
