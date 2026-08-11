#!/usr/bin/env python3
"""Regenerate CourtReach's PWA app icons — a single court-island tile, exactly
the shape every user already sees inside the app (boardCell's stacked head):
navy top band with "C1" (C white, digit gold, IBM Plex Mono — the app's own
number font), light bottom band with a case/item number in navy. A real
glimpse of what's inside, not an abstract shape.

Deterministic (Pillow + the real IBM Plex Mono Bold TTF). Run: python3 make-icon.py
Writes icon-512.png, icon-192.png, apple-touch-icon.png, favicon-32.png.
"""
import os, urllib.request
from PIL import Image, ImageDraw, ImageFont

NAVY  = (20, 26, 34, 255)    # #141a22 — app.css --navy
GOLD  = (194, 168, 106, 255) # #c2a86a — app.css --gold
INK   = (22, 27, 34, 255)    # #161b22 — app.css --ink
WHITE = (255, 255, 255, 255)
FONT = "/tmp/fonts/IBMPlexMono-Bold.ttf"
FONT_URL = ("https://raw.githubusercontent.com/google/fonts/main/ofl/"
            "ibmplexmono/IBMPlexMono-Bold.ttf")

if not os.path.exists(FONT):
    os.makedirs(os.path.dirname(FONT), exist_ok=True)
    print("downloading IBM Plex Mono…")
    urllib.request.urlretrieve(FONT_URL, FONT)

def centered_text(d, xc, yc, text, font, fill):
    bbox = d.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text((xc - w / 2 - bbox[0], yc - h / 2 - bbox[1]), text, font=font, fill=fill)

def draw_icon(size):
    img = Image.new("RGBA", (size, size), NAVY)
    d = ImageDraw.Draw(img)

    corner = size * 0.22          # app-icon-style rounded square (like the in-app tile)
    split = size * 0.46           # top band (court no.) vs bottom band (item no.)

    # whole-icon rounded-square base, then the two bands drawn inside it
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size, size], radius=corner, fill=255)

    band = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    bd.rectangle([0, 0, size, split], fill=NAVY)
    bd.rectangle([0, split, size, size], fill=WHITE)

    out = Image.composite(band, Image.new("RGBA", (size, size), (0, 0, 0, 0)), mask)
    d = ImageDraw.Draw(out)

    # "C1" — top band, C in white, digit in gold (matches .cell-topbar .cd)
    f_top = ImageFont.truetype(FONT, int(size * 0.30))
    c_w = d.textbbox((0, 0), "C", font=f_top)[2]
    n_w = d.textbbox((0, 0), "1", font=f_top)[2]
    gap = size * 0.006
    total = c_w + gap + n_w
    x0 = size / 2 - total / 2
    yc_top = split * 0.52
    bbox_c = d.textbbox((0, 0), "C", font=f_top)
    y = yc_top - (bbox_c[3] - bbox_c[1]) / 2 - bbox_c[1]
    d.text((x0, y), "C", font=f_top, fill=WHITE)
    d.text((x0 + c_w + gap, y), "1", font=f_top, fill=GOLD)

    # case/item number — bottom band, navy on white (matches .cell-on-num)
    f_bot = ImageFont.truetype(FONT, int(size * 0.32))
    yc_bot = split + (size - split) * 0.52
    centered_text(d, size / 2, yc_bot, "24", f_bot, INK)

    return out

big = draw_icon(512)
big.save("icon-512.png")
big.resize((192, 192), Image.LANCZOS).save("icon-192.png")
big.resize((180, 180), Image.LANCZOS).save("apple-touch-icon.png")
big.resize((32, 32), Image.LANCZOS).save("favicon-32.png")
print("wrote icon-512.png, icon-192.png, apple-touch-icon.png, favicon-32.png")
