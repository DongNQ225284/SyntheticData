from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps

from backend.app.engine.inventory import AssetFile, iter_asset_files
from backend.app.models.contracts import BackgroundSceneModel, BlockModel, TemplateModel


if hasattr(Image, "Resampling"):
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
    RESAMPLE_BICUBIC = Image.Resampling.BICUBIC
else:
    RESAMPLE_LANCZOS = Image.LANCZOS
    RESAMPLE_BICUBIC = Image.BICUBIC


@dataclass(slots=True)
class LoadedAsset:
    class_id: int
    class_name: str
    subtype_name: str | None
    path: Path
    image: Image.Image


@dataclass(slots=True)
class Annotation:
    class_id: int
    class_name: str
    subtype_name: str | None
    block_id: str
    bbox_xyxy: tuple[int, int, int, int]
    polygon_xy: list[tuple[float, float]]


def to_document_rgba(image: Image.Image) -> Image.Image:
    source = image.convert("RGBA")
    grayscale = source.convert("L")
    source_alpha = source.getchannel("A")
    darkness = ImageChops.invert(grayscale)
    alpha = ImageChops.multiply(darkness, source_alpha)
    black = Image.new("L", source.size, 0)
    return Image.merge("RGBA", (black, black, black, alpha))


def prepare_asset_image(path: Path) -> Image.Image:
    with Image.open(path) as source:
        image = to_document_rgba(source)
    bbox = image.getbbox()
    if bbox is not None:
        image = image.crop(bbox)
    return image


def load_assets(assets_root: Path) -> tuple[list[LoadedAsset], list[str]]:
    groups = iter_asset_files(assets_root)
    class_names = sorted({asset.class_name for asset in groups})
    class_ids = {class_name: index for index, class_name in enumerate(class_names)}
    assets: list[LoadedAsset] = []
    for asset_file in groups:
        assets.append(
            LoadedAsset(
                class_id=class_ids[asset_file.class_name],
                class_name=asset_file.class_name,
                subtype_name=asset_file.subtype_name,
                path=asset_file.path,
                image=prepare_asset_image(asset_file.path),
            )
        )
    return assets, class_names


def sample_scene(template: TemplateModel, rng: random.Random):
    total_weight = sum(scene.scene_weight for scene in template.background_scenes)
    threshold = rng.uniform(0, total_weight)
    running = 0.0
    for scene in template.background_scenes:
        running += scene.scene_weight
        if threshold <= running:
            return scene
    return template.background_scenes[-1]


def load_background_native(background_path: Path) -> Image.Image:
    """Load the background image at its original pixel dimensions (no crop, no forced resize)."""
    with Image.open(background_path) as source:
        return source.convert("L").copy()


def rotate_point(x: float, y: float, center_x: float, center_y: float, angle_radians: float) -> tuple[float, float]:
    translated_x = x - center_x
    translated_y = y - center_y
    cos_angle = math.cos(angle_radians)
    sin_angle = math.sin(angle_radians)
    rotated_x = (translated_x * cos_angle) + (translated_y * sin_angle)
    rotated_y = (-translated_x * sin_angle) + (translated_y * cos_angle)
    return rotated_x + center_x, rotated_y + center_y


def extract_polygon(width: int, height: int, angle_degrees: float, crop_bbox: tuple[int, int, int, int]) -> list[tuple[float, float]]:
    corners = [
        (0.0, 0.0),
        (float(width), 0.0),
        (float(width), float(height)),
        (0.0, float(height)),
    ]
    center_x = width / 2.0
    center_y = height / 2.0
    angle_radians = math.radians(angle_degrees)
    rotated = [rotate_point(x, y, center_x, center_y, angle_radians) for x, y in corners]
    min_x = min(x for x, _ in rotated)
    min_y = min(y for _, y in rotated)
    crop_x1, crop_y1, _, _ = crop_bbox
    return [(x - min_x - crop_x1, y - min_y - crop_y1) for x, y in rotated]


def apply_augmentation(image: Image.Image, block: BlockModel, rng: random.Random) -> tuple[Image.Image, list[tuple[float, float]]]:
    angle = rng.uniform(-block.augmentation.rotation_max, block.augmentation.rotation_max)
    transformed = image.rotate(angle, expand=True, resample=RESAMPLE_BICUBIC)
    crop_bbox = transformed.getbbox()
    if crop_bbox is None:
        return image, [(0.0, 0.0), (float(image.width), 0.0), (float(image.width), float(image.height)), (0.0, float(image.height))]
    transformed = transformed.crop(crop_bbox)
    if block.augmentation.blur_max > 0:
        transformed = transformed.filter(ImageFilter.GaussianBlur(radius=rng.uniform(0, block.augmentation.blur_max)))
    if block.augmentation.noise_max > 0:
        enhancer = ImageEnhance.Contrast(transformed)
        transformed = enhancer.enhance(1 + rng.uniform(0, block.augmentation.noise_max * 8))
    polygon = extract_polygon(image.width, image.height, angle, crop_bbox)
    return transformed, polygon


def resize_asset_to_block(
    image: Image.Image,
    block_width: int,
    block_height: int,
    anchor: str | None,
    rng: random.Random,
) -> Image.Image:
    """Resize the asset to a random fraction of the block size, preserving aspect ratio.

    - Image fits within 80 % of block (small): target = random(70 %, 80 %) × block.
    - Image exceeds 80 % of block in either dimension (large): target = random(80 %, 90 %) × block.

    The constraining dimension (whichever requires the greater scale-down) is used so
    the result never overflows the target rectangle. The anchor parameter is kept for
    API compatibility but does not affect sizing.
    """
    if image.width <= 0 or image.height <= 0:
        return image
    is_large = image.width > block_width * 0.8 or image.height > block_height * 0.8
    target_ratio = rng.uniform(0.80, 0.90) if is_large else rng.uniform(0.70, 0.80)
    scale = min(
        (block_width  * target_ratio) / image.width,
        (block_height * target_ratio) / image.height,
    )
    return image.resize(
        (max(1, int(image.width * scale)), max(1, int(image.height * scale))),
        RESAMPLE_LANCZOS,
    )


def choose_candidates(assets: list[LoadedAsset], block: BlockModel) -> list[LoadedAsset]:
    candidates = [asset for asset in assets if asset.class_name == block.class_name]
    if block.allowed_subtypes:
        candidates = [asset for asset in candidates if asset.subtype_name in set(block.allowed_subtypes)]
    return candidates


def block_rect(block: BlockModel, width: int, height: int) -> tuple[int, int, int, int]:
    left = int(block.bbox[0] * width)
    top = int(block.bbox[1] * height)
    block_width = max(1, int(block.bbox[2] * width))
    block_height = max(1, int(block.bbox[3] * height))
    return left, top, block_width, block_height


def anchor_position(anchor: str, left: int, top: int, block_width: int, block_height: int, obj_w: int, obj_h: int) -> tuple[int, int]:
    x_map = {
        "left": left,
        "center": left + max(0, (block_width - obj_w) // 2),
        "right": left + max(0, block_width - obj_w),
    }
    y_map = {
        "top": top,
        "center": top + max(0, (block_height - obj_h) // 2),
        "bottom": top + max(0, block_height - obj_h),
    }
    vertical, horizontal = anchor.split("_", 1) if "_" in anchor else ("center", anchor)
    return x_map[horizontal], y_map[vertical]


def random_position(left: int, top: int, block_width: int, block_height: int, obj_w: int, obj_h: int, rng: random.Random) -> tuple[int, int]:
    max_left = left + max(0, block_width - obj_w)
    max_top = top + max(0, block_height - obj_h)
    return rng.randint(left, max_left), rng.randint(top, max_top)


def paste_asset(canvas: Image.Image, asset_image: Image.Image, x: int, y: int) -> None:
    region = canvas.crop((x, y, x + asset_image.width, y + asset_image.height))
    region.paste(0, mask=asset_image.getchannel("A"))
    canvas.paste(region, (x, y))


def to_yolo_line(polygon_xy: list[tuple[float, float]], class_id: int, width: int, height: int) -> str:
    normalized_points = [
        f"{min(1.0, max(0.0, x / width)):.6f} {min(1.0, max(0.0, y / height)):.6f}"
        for x, y in polygon_xy
    ]
    return f"{class_id} " + " ".join(normalized_points)


def boxes_overlap(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    """Return True if two axis-aligned bounding boxes (x1,y1,x2,y2) intersect."""
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def generate_single_sample(scene: BackgroundSceneModel, assets: list[LoadedAsset], runtime_root: Path, rng: random.Random) -> tuple[Image.Image, list[Annotation], int, int]:
    # Step 1 — load background at its native (original) resolution
    background_path = runtime_root / scene.background.image_path
    canvas = load_background_native(background_path)
    native_width, native_height = canvas.size

    annotations: list[Annotation] = []
    placed_boxes: list[tuple[int, int, int, int]] = []  # tracks xyxy in native space

    # Step 2 — place all objects using the native canvas dimensions
    for block in scene.blocks:
        candidates = choose_candidates(assets, block)
        if not candidates:
            continue
        left, top, block_width, block_height = block_rect(block, native_width, native_height)
        for _ in range(block.capacity):
            if rng.random() < block.skip_prob:
                continue
            asset = rng.choice(candidates)
            resized = resize_asset_to_block(asset.image, block_width, block_height, block.position_anchor, rng)
            augmented, polygon = apply_augmentation(resized, block, rng)
            if augmented.width >= block_width or augmented.height >= block_height:
                shrink = min((block_width * 0.9) / max(1, augmented.width), (block_height * 0.9) / max(1, augmented.height))
                if shrink <= 0:
                    continue
                augmented = augmented.resize(
                    (max(1, int(augmented.width * shrink)), max(1, int(augmented.height * shrink))),
                    RESAMPLE_LANCZOS,
                )

            # --- Position resolution with optional overlap check ---
            MAX_RETRIES = 8
            x, y = 0, 0
            placed = False
            attempts = MAX_RETRIES if not scene.allow_overlap else 1
            for attempt in range(attempts):
                if block.position_anchor is None:
                    cx, cy = random_position(left, top, block_width, block_height, augmented.width, augmented.height, rng)
                else:
                    cx, cy = anchor_position(block.position_anchor, left, top, block_width, block_height, augmented.width, augmented.height)

                candidate_box = (cx, cy, cx + augmented.width, cy + augmented.height)
                if scene.allow_overlap or not any(boxes_overlap(candidate_box, pb) for pb in placed_boxes):
                    x, y = cx, cy
                    placed = True
                    break
                if block.position_anchor is not None:
                    break

            if not placed:
                continue

            paste_asset(canvas, augmented, x, y)
            final_box = (x, y, x + augmented.width, y + augmented.height)
            placed_boxes.append(final_box)
            placed_polygon = [(point_x + x, point_y + y) for point_x, point_y in polygon]
            annotations.append(
                Annotation(
                    class_id=asset.class_id,
                    class_name=asset.class_name,
                    subtype_name=asset.subtype_name,
                    block_id=block.id,
                    bbox_xyxy=final_box,
                    polygon_xy=placed_polygon,
                )
            )

    # Step 3 — resize the fully-composed image to a random target resolution
    target_width = rng.randint(scene.canvas_size_range.width[0], scene.canvas_size_range.width[1])
    target_height = rng.randint(scene.canvas_size_range.height[0], scene.canvas_size_range.height[1])
    canvas = canvas.resize((target_width, target_height), RESAMPLE_LANCZOS)

    # Step 4 — scale all annotation coordinates to match the new pixel space
    scale_x = target_width / native_width
    scale_y = target_height / native_height
    scaled_annotations: list[Annotation] = []
    for ann in annotations:
        x1, y1, x2, y2 = ann.bbox_xyxy
        scaled_annotations.append(
            Annotation(
                class_id=ann.class_id,
                class_name=ann.class_name,
                subtype_name=ann.subtype_name,
                block_id=ann.block_id,
                bbox_xyxy=(
                    int(x1 * scale_x),
                    int(y1 * scale_y),
                    int(x2 * scale_x),
                    int(y2 * scale_y),
                ),
                polygon_xy=[(px * scale_x, py * scale_y) for px, py in ann.polygon_xy],
            )
        )

    return canvas, scaled_annotations, target_width, target_height


def generate_dataset(
    *,
    template: TemplateModel,
    assets_root: Path,
    runtime_root: Path,
    output_dir: Path,
    count: int,
    seed: int,
    job_blocker: Callable[[], bool],
    progress_callback: Callable[[int], None],
) -> None:
    rng = random.Random(seed)
    assets, class_names = load_assets(assets_root)
    images_dir = output_dir / "images"
    labels_dir = output_dir / "labels"
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "metadata.jsonl"
    data_yaml_path = output_dir / "data.yaml"

    data_yaml_path.write_text(
        "\n".join(
            [
                f"path: {output_dir}",
                "train: images",
                "val: images",
                f"nc: {len(class_names)}",
                "names:",
                *[f"  {class_id}: {class_name}" for class_id, class_name in enumerate(class_names)],
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    with manifest_path.open("w", encoding="utf-8") as manifest:
        for index in range(count):
            if job_blocker():
                raise RuntimeError("Job cancelled")

            scene = sample_scene(template, rng)
            canvas, annotations, canvas_width, canvas_height = generate_single_sample(scene, assets, runtime_root, rng)

            image_name = f"sample_{index:05d}.png"
            label_name = f"sample_{index:05d}.txt"
            canvas.save(images_dir / image_name)
            label_lines = [to_yolo_line(annotation.polygon_xy, annotation.class_id, canvas_width, canvas_height) for annotation in annotations]
            (labels_dir / label_name).write_text("\n".join(label_lines) + ("\n" if label_lines else ""), encoding="utf-8")
            manifest.write(
                json.dumps(
                    {
                        "image": f"images/{image_name}",
                        "label": f"labels/{label_name}",
                        "layout_template": template.name,
                        "scene_id": scene.id,
                        "annotations": [
                            {
                                "class_id": annotation.class_id,
                                "class_name": annotation.class_name,
                                "subtype_name": annotation.subtype_name,
                                "block_id": annotation.block_id,
                                "bbox_xyxy": list(annotation.bbox_xyxy),
                                "polygon_xy": [list(point) for point in annotation.polygon_xy],
                            }
                            for annotation in annotations
                        ],
                    }
                )
                + "\n"
            )
            progress_callback(index + 1)
