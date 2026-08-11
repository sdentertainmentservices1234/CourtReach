#!/usr/bin/env python3
"""Regenerate CourtReach's PWA app icons — a small grid of court "tiles" echoing
the Supreme Court's own electronic display board (cdb.sci.gov.in): rounded-square
tiles in a grid, most idle/grey, ONE lit warm gold — "the moment your matter is
up", which is exactly what CourtReach itself does. Kept abstract (no text/digits
inside tiles) so it stays legible down to favicon size, per the owner's request
to echo the physical board most advocates already recognise on sight.

Deterministic (Pillow only, no fonts needed — pure shapes). Run: python3 make-icon.py
Writes icon-512.png, icon-192.png, apple-touch-icon.png (180), favicon-32.png.
"""
from PIL import Image, ImageDraw

NAVY   = (20, 26, 34, 255)     # #141a22 — CourtReach's own navy (app.css --navy)
IDLE   = (110, 122, 138, 255)  # muted slate — idle/not-sitting tile
GOLD   = (194, 168, 106, 255)  # #c2a86a — CourtReach's own gold (app.css --gold)

def draw_icon(size):
    img = Image.new("RGBA", (size, size), NAVY)
    d = ImageDraw.Draw(img)

    # Safe-zone grid (maskable icons get cropped to a circle/squircle by the OS,
    # so keep all content inside the centre ~80%).
    margin = size * 0.155
    top, bottom = margin, size - margin
    cols, rows = 3, 2
    gap = size * 0.052
    grid_w = size - 2 * margin
    grid_h = bottom - top
    tile_w = (grid_w - gap * (cols - 1)) / cols
    tile_h = (grid_h - gap * (rows - 1)) / rows
    radius = tile_w * 0.22

    lit = (1, 1)  # (col, row) — the tile that's "reaching now"
    for row in range(rows):
        for col in range(cols):
            x0 = margin + col * (tile_w + gap)
            y0 = top + row * (tile_h + gap)
            x1, y1 = x0 + tile_w, y0 + tile_h
            is_lit = (col, row) == lit
            if is_lit:
                # soft glow behind the lit tile, then a single clean gold fill
                glow_pad = size * 0.028
                d.rounded_rectangle(
                    [x0 - glow_pad, y0 - glow_pad, x1 + glow_pad, y1 + glow_pad],
                    radius=radius + glow_pad, fill=(194, 168, 106, 70))
                d.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=GOLD)
            else:
                d.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=IDLE)

    # thin ticker bar at the very bottom, echoing the marquee strip on the real
    # board — a quiet detail, not legible text (would vanish at small sizes).
    bar_y = bottom + size * 0.052
    bar_h = size * 0.028
    if bar_y + bar_h < size - size * 0.03:
        d.rounded_rectangle([margin, bar_y, size - margin, bar_y + bar_h],
                             radius=bar_h / 2, fill=(255, 255, 255, 40))

    return img

big = draw_icon(512)
big.save("icon-512.png")
big.resize((192, 192), Image.LANCZOS).save("icon-192.png")
big.resize((180, 180), Image.LANCZOS).save("apple-touch-icon.png")
big.resize((32, 32), Image.LANCZOS).save("favicon-32.png")
print("wrote icon-512.png, icon-192.png, apple-touch-icon.png, favicon-32.png")
