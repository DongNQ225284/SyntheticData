from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from backend.app.models.contracts import BackgroundSceneModel, TemplateModel


# Known-class palette — mirrors the frontend CLASS_COLOR_PALETTE in EditorScreen.tsx
_CLASS_COLOR_PALETTE: dict[str, tuple[int, int, int]] = {
    "figure":     ( 29, 143, 255),
    "table":      (  0, 168, 107),
    "note":       (255, 138,   0),
    "text":       (168,  85, 247),
    "dimension":  (236,  72, 153),
    "symbol":     ( 20, 184, 166),
    "stamp":      (245, 158,  11),
    "titleblock": ( 99, 102, 241),
    "border":     (100, 116, 139),
}


def _get_class_color(class_name: str) -> tuple[int, int, int]:
    """Return an RGB tuple for a class name.

    Uses the curated palette first; falls back to a deterministic HSL colour
    derived from a hash of the class name so that any extra classes still get
    a distinct, stable colour.
    """
    if class_name in _CLASS_COLOR_PALETTE:
        return _CLASS_COLOR_PALETTE[class_name]
    # Deterministic hue: same hash algorithm as getClassColor() in EditorScreen.tsx
    h = 0
    for ch in class_name:
        h = ((h * 31) + ord(ch)) & 0xFFFFFFFF
    hue = h % 360
    # Convert HSL(hue, 70%, 48%) to RGB
    import colorsys
    r, g, b = colorsys.hls_to_rgb(hue / 360.0, 0.48, 0.70)
    return (int(r * 255), int(g * 255), int(b * 255))


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_names = ["DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", "Arial.ttf"]
    for font_name in font_names:
        try:
            return ImageFont.truetype(font_name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def overlay_blocks(canvas: Image.Image, scene: BackgroundSceneModel, canvas_width: int, canvas_height: int) -> Image.Image:
    """Composite colored block-region overlays onto an already-generated canvas.

    The canvas may be grayscale (mode "L") or RGB — it is converted to RGB
    before drawing. Block rectangles are drawn as semi-transparent fills with
    a solid border and a small label badge, color-coded by class name.
    """
    base = canvas.convert("RGB")
    width, height = canvas_width, canvas_height

    label_font = load_font(max(12, width // 200), bold=True)

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for block in scene.blocks:
        left   = int(block.bbox[0] * width)
        top    = int(block.bbox[1] * height)
        right  = left + int(block.bbox[2] * width)
        bottom = top  + int(block.bbox[3] * height)

        r, g, b = _get_class_color(block.class_name)

        draw.rectangle((left, top, right, bottom), outline=(r, g, b, 220), width=max(3, width // 800))

        label = f"{block.id} · {block.class_name}"
        text_w = int(draw.textlength(label, font=label_font))
        pad = max(6, width // 600)
        badge_h = max(22, width // 150)
        bx1, by1 = left + pad, top + pad
        bx2, by2 = bx1 + text_w + pad * 2, by1 + badge_h
        draw.rounded_rectangle((bx1, by1, bx2, by2), radius=6, fill=(r, g, b, 220))
        draw.text((bx1 + pad, by1 + pad // 2), label, font=label_font, fill=(255, 255, 255, 255))

    result = Image.alpha_composite(base.convert("RGBA"), overlay)
    return result.convert("RGB")


def render_preview(template: TemplateModel, scene: BackgroundSceneModel, runtime_root: Path) -> Image.Image:
    """Render a layout-only preview (no generated objects — block regions only).

    Loads the background at native resolution and draws colored block overlays.
    Useful for a fast structural view without running asset generation.
    """
    background_path = runtime_root / scene.background.image_path
    with Image.open(background_path) as src:
        canvas = src.convert("RGB").copy()
    width, height = canvas.size
    return overlay_blocks(canvas, scene, width, height)


