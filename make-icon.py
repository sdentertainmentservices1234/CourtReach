#!/usr/bin/env python3
"""Regenerate CourtReach's PWA app icons — the real brand monogram (the
chevron-arrow + dot + "CR" wordmark used in the header/login, lifted from that
SVG's own path data, viewBox 0 0 44 44) on the navy top band of a court-island
tile, with a case/item number ("24", IBM Plex Mono — the app's own number
font) on the light bottom band. Owner's pick among 4 options (Aug 2026):
full monogram > abstract grid, > a bare "C1" with no brand mark.

Deterministic (Pillow + real TTFs, no base64). Run: python3 make-icon.py
Writes icon-512.png, icon-192.png, apple-touch-icon.png, favicon-32.png.

Fonts (auto-downloaded to /tmp/fonts/ if missing):
  - IBM Plex Mono Bold — the case number (app.css --mono)
  - Source Serif 4 (variable, opsz/wght set to semibold) — stands in for the
    header's Georgia/Iowan Old Style/Palatino stack, which isn't freely
    redistributable; visually close serif for the "CR" wordmark.
"""
import os, urllib.request
from PIL import Image, ImageDraw, ImageFont

NAVY  = (20, 26, 34, 255)     # #141a22 — app.css --navy
GOLD  = (203, 182, 130, 255)  # #cbb682 — the header monogram's own gold
INK   = (22, 27, 34, 255)     # #161b22 — app.css --ink
WHITE = (255, 255, 255, 255)

MONO = "/tmp/fonts/IBMPlexMono-Bold.ttf"
MONO_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/ibmplexmono/IBMPlexMono-Bold.ttf"
SERIF = "/tmp/fonts/IowanOldStyle.ttf"   # Source Serif 4 (variable), despite the filename
SERIF_URL = ("https://raw.githubusercontent.com/google/fonts/main/ofl/sourceserif4/"
             "SourceSerif4%5Bopsz%2Cwght%5D.ttf")

def ensure(path, url):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        print(f"downloading {os.path.basename(path)}…")
        urllib.request.urlretrieve(url, path)

ensure(MONO, MONO_URL)
ensure(SERIF, SERIF_URL)

def serif_font(px):
    f = ImageFont.truetype(SERIF, px)
    try: f.set_variation_by_axes([14.0, 600.0])  # opsz, wght — semibold
    except Exception: pass
    return f

def centered_text(d, xc, yc, text, font, fill):
    bbox = d.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text((xc - w / 2 - bbox[0], yc - h / 2 - bbox[1]), text, font=font, fill=fill)

def chevrons(d, ox, oy, s, color, stroke_w):
    """The header monogram's arrow+dot glyph. (ox,oy)=pixel origin for svg (0,0);
    s=px per svg-unit. Path data lifted straight from #brandLogo's <svg>."""
    def pt(x, y): return (ox + x * s, oy + y * s)
    for pts in ([pt(15, 15), pt(22, 9), pt(29, 15)], [pt(13, 21), pt(22, 14), pt(31, 21)]):
        d.line(pts, fill=color, width=stroke_w, joint="curve")
        r = stroke_w / 2
        for (x, y) in pts:
            d.ellipse([x - r, y - r, x + r, y + r], fill=color)
    cx, cy = pt(22, 5.6)
    rdot = 2 * s
    d.ellipse([cx - rdot, cy - rdot, cx + rdot, cy + rdot], fill=color)

def draw_icon(size):
    corner = size * 0.22
    split = size * 0.50

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size, size], radius=corner, fill=255)
    band = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    bd.rectangle([0, 0, size, split], fill=NAVY)
    bd.rectangle([0, split, size, size], fill=WHITE)
    img = Image.composite(band, Image.new("RGBA", (size, size), (0, 0, 0, 0)), mask)
    d = ImageDraw.Draw(img)

    # monogram: chevrons+dot, then "CR" beneath, filling the top band
    s = size / 44 * 0.66
    ox = size * 0.5 - 22 * s
    chevrons(d, ox, size * 0.035, s, GOLD, max(2, int(size * 0.015)))
    f_cr = serif_font(int(size * 0.185))
    centered_text(d, size / 2, split * 0.80, "CR", f_cr, GOLD)

    # case/item number — bottom band, navy on white (matches .cell-on-num)
    f_num = ImageFont.truetype(MONO, int(size * 0.28))
    centered_text(d, size / 2, split + (size - split) * 0.52, "24", f_num, INK)

    return img

big = draw_icon(512)
big.save("icon-512.png")
big.resize((192, 192), Image.LANCZOS).save("icon-192.png")
big.resize((180, 180), Image.LANCZOS).save("apple-touch-icon.png")
big.resize((32, 32), Image.LANCZOS).save("favicon-32.png")
print("wrote icon-512.png, icon-192.png, apple-touch-icon.png, favicon-32.png")
