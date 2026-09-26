"""Synthetic top-down 'aerial' imagery (stand-in for Nearmap / CAPE captures)."""
from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1200, 800


def _font(size: int):
    for f in ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_aerial(path: Path, style: str, date: str, label: str, seed: int = 1):
    rng = random.Random(seed)
    img = Image.new("RGB", (W, H), (118, 138, 96))
    d = ImageDraw.Draw(img)
    # texture: grass noise + trees
    for _ in range(9000):
        x, y = rng.randrange(W), rng.randrange(H)
        g = rng.randint(-14, 14)
        d.point((x, y), fill=(118 + g, 138 + g, 96 + g))
    for _ in range(70):
        x, y, r = rng.randrange(W), rng.randrange(H), rng.randint(8, 22)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(64 + rng.randint(-8, 8), 92 + rng.randint(-8, 8), 58))
    # road
    d.rectangle((0, 690, W, 760), fill=(92, 94, 98))
    for x in range(0, W, 60):
        d.rectangle((x, 723, x + 30, 727), fill=(230, 214, 120))
    # parking / yard
    d.rectangle((120, 470, 1080, 680), fill=(108, 110, 114))
    for x in range(140, 1070, 34):
        d.line((x, 480, x, 540), fill=(215, 215, 215), width=2)
        d.line((x, 610, x, 670), fill=(215, 215, 215), width=2)
    # building footprint
    bx0, by0, bx1, by1 = 170, 90, 1030, 450
    roof = (176, 180, 186)
    d.rectangle((bx0 + 8, by0 + 8, bx1 + 8, by1 + 8), fill=(70, 74, 70))  # shadow
    d.rectangle((bx0, by0, bx1, by1), fill=roof)
    for x in range(bx0 + 40, bx1, 120):
        d.rectangle((x, by0 + 40, x + 36, by0 + 70), fill=(150, 154, 160))  # HVAC
    if style == "roof_hail":
        for _ in range(1400):
            x, y = rng.randint(bx0, bx1), rng.randint(by0, by1)
            r = rng.randint(1, 3)
            d.ellipse((x - r, y - r, x + r, y + r), fill=(138, 118, 96))
        for _ in range(9):
            x, y = rng.randint(bx0 + 40, bx1 - 140), rng.randint(by0 + 90, by1 - 80)
            d.rectangle((x, y, x + rng.randint(60, 140), y + rng.randint(30, 70)), fill=(120, 98, 80))
        d.line((bx0 + 300, by0, bx0 + 300, by1), fill=(150, 150, 154), width=3)
    if style in ("lot_full", "roof_ok", "yard_empty", "yard_racks", "roof_hail"):
        n = 70 if style == "lot_full" else 26
        for _ in range(n):
            row = rng.choice([500, 632])
            x = rng.randrange(142, 1060, 34)
            col = rng.choice([(200, 30, 30), (240, 240, 240), (30, 30, 30), (40, 80, 160), (160, 160, 170), (90, 90, 95)])
            d.rectangle((x + 4, row, x + 26, row + 40), fill=col)
    if style == "lot_empty":
        for _ in range(4):
            x = rng.randrange(142, 1060, 34)
            d.rectangle((x + 4, 632, x + 26, 672), fill=(160, 160, 170))
        d.rectangle((bx0 + 20, by0 + 20, bx0 + 520, by1 - 20), outline=(150, 60, 60), width=4)
        d.text((bx0 + 40, by0 + 30), "Anchor unit — no activity, signage removed", fill=(150, 40, 40), font=_font(20))
    if style == "yard_racks":
        for i in range(8):
            x0 = 170 + i * 110
            d.rectangle((x0, 548, x0 + 90, 600), fill=(214, 120, 36))
            d.rectangle((x0, 548, x0 + 90, 556), fill=(170, 90, 20))
        d.text((170, 520), "New high-bay racking + battery pallet staging (not present 2024)", fill=(255, 235, 200), font=_font(18))
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, 44), fill=(15, 22, 36))
    d.text((16, 11), f"{label}", fill=(255, 255, 255), font=_font(20))
    d.text((W - 360, 11), f"Capture {date} · 7.5 cm GSD", fill=(180, 200, 220), font=_font(18))
    d.text((16, H - 30), "SAMPLE · synthetic imagery (stand-in for aerial vendor)", fill=(255, 255, 255), font=_font(15))
    # north arrow
    d.polygon([(W - 40, 70), (W - 52, 100), (W - 28, 100)], fill=(255, 255, 255))
    d.text((W - 46, 102), "N", fill=(255, 255, 255), font=_font(14))
    img.save(path, optimize=True)
