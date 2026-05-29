"""
Generate PWA icon PNGs from SVG template.

Run this script once to create icon-192.png and icon-512.png:
    python .streamlit/static/generate_icons.py

Requires: Pillow (pip install Pillow)
If Pillow is not available, the app will work without icons
(browser will use a default placeholder).
"""
from __future__ import annotations

import os

ICON_DIR = os.path.dirname(os.path.abspath(__file__))


def generate_icon(size: int, filename: str) -> None:
    """Generate a simple branded icon PNG."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow not installed. Run: pip install Pillow")
        print("Skipping icon generation (app will work without custom icons)")
        return

    # Create image with gradient-like blue background
    img = Image.new("RGBA", (size, size), (15, 23, 42, 255))  # Dark blue
    draw = ImageDraw.Draw(img)

    # Draw a rounded rectangle background
    margin = size // 8
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=size // 6,
        fill=(59, 130, 246, 255),  # Blue
    )

    # Draw text "AI" in the center
    font_size = size // 3
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except (OSError, IOError):
        font = ImageFont.load_default()

    text = "AI"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) // 2
    y = (size - text_h) // 2 - size // 20
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)

    # Draw small briefcase emoji approximation (rectangle + handle)
    brief_y = y + text_h + size // 20
    brief_w = size // 4
    brief_h = size // 6
    brief_x = (size - brief_w) // 2
    draw.rounded_rectangle(
        [brief_x, brief_y, brief_x + brief_w, brief_y + brief_h],
        radius=size // 30,
        fill=(255, 255, 255, 200),
    )

    # Save
    filepath = os.path.join(ICON_DIR, filename)
    img.save(filepath, "PNG")
    print(f"Generated: {filepath} ({size}x{size})")


if __name__ == "__main__":
    generate_icon(192, "icon-192.png")
    generate_icon(512, "icon-512.png")
    print("Done! Icons saved to .streamlit/static/")
