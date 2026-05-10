from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from backend.app.models.contracts import BackgroundSceneModel, TemplateModel


CLASS_COLORS = {
    "figure": "#2188ff",
    "table": "#00a86b",
    "note": "#ff8a00",
}


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_names = ["DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", "Arial.ttf"]
    for font_name in font_names:
        try:
            return ImageFont.truetype(font_name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _fit_background(image_path: Path, width: int, height: int) -> Image.Image:
    with Image.open(image_path) as source:
        background = ImageOps.fit(source.convert("RGB"), (width, height), method=Image.Resampling.LANCZOS)
    return background


def _scene_size(scene: BackgroundSceneModel) -> tuple[int, int]:
    width = int((scene.canvas_size_range.width[0] + scene.canvas_size_range.width[1]) / 2)
    height = int((scene.canvas_size_range.height[0] + scene.canvas_size_range.height[1]) / 2)
    return width, height


def render_preview(template: TemplateModel, scene: BackgroundSceneModel, runtime_root: Path) -> Image.Image:
    width, height = _scene_size(scene)
    background_path = runtime_root / scene.background.image_path
    canvas = _fit_background(background_path, width, height)
    draw = ImageDraw.Draw(canvas, "RGBA")
    title_font = load_font(24, bold=True)
    label_font = load_font(18, bold=True)
    body_font = load_font(14)

    for block in scene.blocks:
        left = int(block.bbox[0] * width)
        top = int(block.bbox[1] * height)
        right = left + int(block.bbox[2] * width)
        bottom = top + int(block.bbox[3] * height)
        color = CLASS_COLORS.get(block.class_name, "#ef4444")
        rgba = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5)) + (56,)
        draw.rectangle((left, top, right, bottom), outline=color, width=6, fill=rgba)
        label = f"{block.id} · {block.class_name}"
        label_width = draw.textlength(label, font=label_font)
        draw.rounded_rectangle((left + 10, top + 10, left + 28 + label_width, top + 42), radius=12, fill=color)
        draw.text((left + 16, top + 16), label, font=label_font, fill="white")
        draw.text(
            (left + 12, min(bottom - 28, top + 52)),
            f"{block.allowed_subtypes[:3]}",
            font=body_font,
            fill="#111827",
        )

    header = Image.new("RGBA", (width, 72), (255, 255, 255, 220))
    header_draw = ImageDraw.Draw(header)
    header_draw.text((24, 18), template.name, font=title_font, fill="#111827")
    header_draw.text((24, 46), f"{scene.id} · weight {scene.scene_weight:g}", font=body_font, fill="#4b5563")
    canvas.paste(header, (0, 0), header)
    return canvas
