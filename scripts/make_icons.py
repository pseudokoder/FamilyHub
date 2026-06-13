"""Generate the PWA icons (run once; the PNGs are committed).

    python scripts/make_icons.py

TEACHING NOTE: app icons are just PNGs at fixed sizes — 192 and 512 for
Android/Chrome (from the web manifest), 180 for the iPhone home screen
(apple-touch-icon). Rather than hand-draw them, this script renders them
with Pillow — the same library the app already uses for thumbnails — so
the icon is reproducible: change the colors here, re-run, done.
"""

import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "..", "app", "static", "icons")

BACKGROUND = "#0d6efd"   # Bootstrap "primary" blue — matches the navbar
TEXT = "FH"

# Try real bold fonts per-OS; Pillow's built-in default is the fallback
# (small but never crashes).
FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf",                              # Windows
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",      # Debian/Ubuntu
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",    # Fedora
]


def _font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def make_icon(size, filename):
    img = Image.new("RGB", (size, size), BACKGROUND)
    draw = ImageDraw.Draw(img)
    font = _font(int(size * 0.42))
    # textbbox measures the rendered text so we can center it for real —
    # (0,0) anchored text has font-specific padding baked into the box.
    box = draw.textbbox((0, 0), TEXT, font=font)
    text_w, text_h = box[2] - box[0], box[3] - box[1]
    draw.text(((size - text_w) / 2 - box[0], (size - text_h) / 2 - box[1]),
              TEXT, font=font, fill="white")
    path = os.path.join(OUT_DIR, filename)
    img.save(path)
    print(f"wrote {path}")


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    make_icon(192, "icon-192.png")
    make_icon(512, "icon-512.png")   # also the "maskable" icon
    make_icon(180, "icon-180.png")   # apple-touch-icon (iPhone home screen)
