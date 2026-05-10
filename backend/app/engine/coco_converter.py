import json
import shutil
from pathlib import Path
from PIL import Image

def convert_to_coco(output_dir: Path, coco_dir: Path) -> None:
    coco_dir.mkdir(parents=True, exist_ok=True)
    images_dir = coco_dir / "images"
    if images_dir.exists():
        shutil.rmtree(images_dir)
    shutil.copytree(output_dir / "images", images_dir)
    
    manifest_path = output_dir / "metadata.jsonl"
    if not manifest_path.exists():
        return
        
    coco_format = {
        "images": [],
        "annotations": [],
        "categories": []
    }
    
    categories_set = {}
    annotation_id = 1
    image_id = 1
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            
            image_rel_path = data["image"]
            image_full_path = output_dir / image_rel_path
            
            width, height = 0, 0
            if image_full_path.exists():
                with Image.open(image_full_path) as img:
                    width, height = img.size
                    
            coco_format["images"].append({
                "id": image_id,
                "file_name": Path(image_rel_path).name,
                "width": width,
                "height": height
            })
            
            for ann in data.get("annotations", []):
                class_id = ann["class_id"]
                class_name = ann["class_name"]
                if class_id not in categories_set:
                    categories_set[class_id] = class_name
                    
                polygon_xy = ann.get("polygon_xy", [])
                segmentation = []
                for pt in polygon_xy:
                    segmentation.extend(pt)
                
                # compute bounding box from polygon
                if polygon_xy:
                    xs = [pt[0] for pt in polygon_xy]
                    ys = [pt[1] for pt in polygon_xy]
                    x_min, x_max = min(xs), max(xs)
                    y_min, y_max = min(ys), max(ys)
                    bbox = [x_min, y_min, x_max - x_min, y_max - y_min]
                else:
                    bbox = [0, 0, 0, 0]
                    
                area = bbox[2] * bbox[3] # rough estimate
                
                coco_format["annotations"].append({
                    "id": annotation_id,
                    "image_id": image_id,
                    "category_id": class_id,
                    "segmentation": [segmentation],
                    "bbox": bbox,
                    "area": area,
                    "iscrowd": 0
                })
                annotation_id += 1
            image_id += 1
            
    for cid, cname in categories_set.items():
        coco_format["categories"].append({
            "id": cid,
            "name": cname,
            "supercategory": "none"
        })
        
    with open(coco_dir / "instances_default.json", "w", encoding="utf-8") as f:
        json.dump(coco_format, f, indent=2)
