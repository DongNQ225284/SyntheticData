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


def render_preview(template: TemplateModel, scene: BackgroundSceneModel, runtime_root: Path) -> Image.Image:
    """Render the layout template as a colored-overlay visualization.

    Loads the background at its native resolution (RGB), then draws one
    semi-transparent filled rectangle per block — color-coded by class —
    with a compact label badge in the top-left corner of each block.
    """
    background_path = runtime_root / scene.background.image_path
    with Image.open(background_path) as src:
        canvas = src.convert("RGB").copy()

    width, height = canvas.size
    label_font = load_font(18, bold=True)

    # Draw overlays on a separate RGBA layer and composite at the end
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for block in scene.blocks:
        left   = int(block.bbox[0] * width)
        top    = int(block.bbox[1] * height)
        right  = left + int(block.bbox[2] * width)
        bottom = top  + int(block.bbox[3] * height)

        r, g, b = _get_class_color(block.class_name)

        # Semi-transparent fill (alpha ~50/255 ≈ 20 %)
        draw.rectangle((left, top, right, bottom), fill=(r, g, b, 50))
        # Solid border (alpha 200)
        draw.rectangle((left, top, right, bottom), outline=(r, g, b, 200), width=4)

        # Label badge
        label = f"{block.id} · {block.class_name}"
        text_w = int(draw.textlength(label, font=label_font))
        badge_pad = 8
        bx1, by1 = left + 10, top + 10
        bx2, by2 = bx1 + text_w + badge_pad * 2, by1 + 30
        draw.rounded_rectangle((bx1, by1, bx2, by2), radius=8, fill=(r, g, b, 220))
        draw.text((bx1 + badge_pad, by1 + 6), label, font=label_font, fill=(255, 255, 255, 255))

    # Composite the overlay on top of the RGB background
    canvas_rgba = canvas.convert("RGBA")
    canvas_rgba = Image.alpha_composite(canvas_rgba, overlay)
    return canvas_rgba.convert("RGB")

