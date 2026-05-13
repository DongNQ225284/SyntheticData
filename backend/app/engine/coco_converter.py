from __future__ import annotations

import json
import shutil
from pathlib import Path
from PIL import Image


def _empty_coco() -> dict:
    return {"images": [], "annotations": [], "categories": []}


def convert_to_coco(
    output_dir: Path,
    coco_dir: Path,
    split_assignment: dict[str, str] | None = None,
) -> None:
    """Convert YOLO-style output_dir into COCO format under coco_dir.

    Parameters
    ----------
    output_dir:
        Directory produced by the generation engine (contains images/, labels/,
        metadata.jsonl).
    coco_dir:
        Destination directory for the COCO export.
    split_assignment:
        Optional mapping of image filename → split name ("train" | "valid" | "test").
        When provided the output will be:
            coco_dir/images/train/   coco_dir/images/valid/   coco_dir/images/test/
            coco_dir/annotations/instance_train.json  …
        When *None* all images go into coco_dir/images/ with a single
        instances_default.json.
    """
    coco_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = output_dir / "metadata.jsonl"
    if not manifest_path.exists():
        return

    use_splits = split_assignment is not None

    if use_splits:
        split_names = ["train", "valid", "test"]
        # Create per-split image directories
        for split in split_names:
            (coco_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        annotations_dir = coco_dir / "annotations"
        annotations_dir.mkdir(parents=True, exist_ok=True)

        split_data: dict[str, dict] = {s: _empty_coco() for s in split_names}
        split_ann_id: dict[str, int] = {s: 1 for s in split_names}
        split_img_id: dict[str, int] = {s: 1 for s in split_names}
        split_categories: dict[str, dict[int, str]] = {s: {} for s in split_names}
    else:
        images_dir = coco_dir / "images"
        if images_dir.exists():
            shutil.rmtree(images_dir)
        images_dir.mkdir(parents=True, exist_ok=True)
        coco_format = _empty_coco()
        categories_set: dict[int, str] = {}
        annotation_id = 1
        image_id = 1

    with open(manifest_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)

            image_rel_path: str = data["image"]
            image_name = Path(image_rel_path).name
            image_full_path = output_dir / image_rel_path

            width, height = 0, 0
            if image_full_path.exists():
                with Image.open(image_full_path) as img:
                    width, height = img.size

            annotations_raw = data.get("annotations", [])

            if use_splits:
                assert split_assignment is not None
                split = split_assignment.get(image_name, "train")
                dest_dir = coco_dir / "images" / split
                if image_full_path.exists():
                    shutil.copy2(image_full_path, dest_dir / image_name)

                img_id = split_img_id[split]
                split_data[split]["images"].append(
                    {"id": img_id, "file_name": f"images/{split}/{image_name}", "width": width, "height": height}
                )

                for ann in annotations_raw:
                    class_id = ann["class_id"]
                    class_name = ann["class_name"]
                    if class_id not in split_categories[split]:
                        split_categories[split][class_id] = class_name

                    polygon_xy = ann.get("polygon_xy", [])
                    segmentation = []
                    for pt in polygon_xy:
                        segmentation.extend(pt)

                    if polygon_xy:
                        xs = [pt[0] for pt in polygon_xy]
                        ys = [pt[1] for pt in polygon_xy]
                        x_min, x_max = min(xs), max(xs)
                        y_min, y_max = min(ys), max(ys)
                        bbox = [x_min, y_min, x_max - x_min, y_max - y_min]
                    else:
                        bbox = [0, 0, 0, 0]

                    area = bbox[2] * bbox[3]
                    split_data[split]["annotations"].append(
                        {
                            "id": split_ann_id[split],
                            "image_id": img_id,
                            "category_id": class_id,
                            "segmentation": [segmentation],
                            "bbox": bbox,
                            "area": area,
                            "iscrowd": 0,
                        }
                    )
                    split_ann_id[split] += 1

                split_img_id[split] += 1

            else:
                if image_full_path.exists():
                    shutil.copy2(image_full_path, images_dir / image_name)

                coco_format["images"].append(
                    {"id": image_id, "file_name": f"images/{image_name}", "width": width, "height": height}
                )

                for ann in annotations_raw:
                    class_id = ann["class_id"]
                    class_name = ann["class_name"]
                    if class_id not in categories_set:
                        categories_set[class_id] = class_name

                    polygon_xy = ann.get("polygon_xy", [])
                    segmentation = []
                    for pt in polygon_xy:
                        segmentation.extend(pt)

                    if polygon_xy:
                        xs = [pt[0] for pt in polygon_xy]
                        ys = [pt[1] for pt in polygon_xy]
                        x_min, x_max = min(xs), max(xs)
                        y_min, y_max = min(ys), max(ys)
                        bbox = [x_min, y_min, x_max - x_min, y_max - y_min]
                    else:
                        bbox = [0, 0, 0, 0]

                    area = bbox[2] * bbox[3]
                    coco_format["annotations"].append(
                        {
                            "id": annotation_id,
                            "image_id": image_id,
                            "category_id": class_id,
                            "segmentation": [segmentation],
                            "bbox": bbox,
                            "area": area,
                            "iscrowd": 0,
                        }
                    )
                    annotation_id += 1

                image_id += 1

    if use_splits:
        assert split_assignment is not None
        for split in split_names:
            for cid, cname in split_categories[split].items():
                split_data[split]["categories"].append(
                    {"id": cid, "name": cname, "supercategory": "none"}
                )
            out_path = coco_dir / "annotations" / f"instances_{split}.json"
            with open(out_path, "w", encoding="utf-8") as fout:
                json.dump(split_data[split], fout, indent=2)
    else:
        for cid, cname in categories_set.items():
            coco_format["categories"].append({"id": cid, "name": cname, "supercategory": "none"})
        with open(coco_dir / "instances_default.json", "w", encoding="utf-8") as fout:
            json.dump(coco_format, fout, indent=2)
