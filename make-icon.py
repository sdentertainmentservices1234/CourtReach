#!/usr/bin/env python3
"""Regenerate CourtReach's PWA app icons — v3, a single unified composition
(owner: "not liking this, come do better... elegant... pleasing to eye").

Replaces the earlier stacked navy/white "two band" tile with one continuous
deep-navy gradient ground (echoes the real Supreme Court display board's
near-black background), the brand chevron+dot mark as a small refined crown,
"C1" as the glowing hero in TEAL — the actual colour the live board lights an
active court in, not just our navy/gold, so the icon calls back to the real
board's specific look, not only its layout. A thin gold hairline rule (matches
the short-rule motif already used elsewhere in the brand, e.g. the login
screen) separates it from a quieter case/item number below.

Owner's call: "take whatever colour code you want" — teal is new, not in
app.css, deliberately, to carry that board-recognition moment; gold/navy stay
from the existing brand so the mark is still unmistakably CourtReach.

The "CR" wordmark from the header monogram is deliberately left OUT of the
icon itself: multi-letter text doesn't hold up at small icon/favicon sizes
(same reason Slack, Notion, etc. ship symbol-only icons — the app name is
already labelled by the OS under the icon). The chevron+dot mark carries the
brand identity instead. Flag to the owner; add "CR" back in if they want it
regardless of the legibility trade-off.

Deterministic (Pillow + IBM Plex Mono Bold, no base64). Run: python3 make-icon.py
Writes icon-512.png, icon-192.png, apple-touch-icon.png, favicon-32.png.
"""
import os, urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageFilter

GOLD  = (203, 182, 130, 255)  # #cbb682 — the header monogram's own gold
TEAL  = (99, 220, 208, 255)   # new for this icon — the board's "active tile" glow
CREAM = (238, 232, 219, 255)
GRAD_TOP    = (13, 17, 23, 255)
GRAD_BOTTOM = (22, 29, 39, 255)

MONO = "/tmp/fonts/IBMPlexMono-Bold.ttf"
MONO_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/ibmplexmono/IBMPlexMono-Bold.ttf"
if not os.path.exists(MONO):
    os.makedirs(os.path.dirname(MONO), exist_ok=True)
    print("downloading IBM Plex Mono…")
    urllib.request.urlretrieve(MONO_URL, MONO)

def vgrad(size, top, bottom):
    img = Image.new("RGBA", (size, size), top)
    px = img.load()
    for y in range(size):
        t = y / size
        row = (int(top[0] + (bottom[0] - top[0]) * t),
               int(top[1] + (bottom[1] - top[1]) * t),
               int(top[2] + (bottom[2] - top[2]) * t), 255)
        for x in range(size):
            px[x, y] = row
    return img

def centered_text(d, xc, yc, text, font, fill):
    bbox = d.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text((xc - w / 2 - bbox[0], yc - h / 2 - bbox[1]), text, font=font, fill=fill)

def chevrons(d, ox, oy, s, color, stroke_w):
    """The header monogram's arrow+dot glyph — path data lifted from #brandLogo's <svg>."""
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
    corner = size * 0.223
    base = vgrad(size, GRAD_TOP, GRAD_BOTTOM)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size, size], radius=corner, fill=255)
    img = Image.composite(base, Image.new("RGBA", (size, size), (0, 0, 0, 0)), mask)

    f_hero = ImageFont.truetype(MONO, int(size * 0.30))
    hero_yc = size * 0.475

    # soft teal glow behind "C1" (its own blurred layer, clipped to the icon shape)
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    centered_text(ImageDraw.Draw(glow), size / 2, hero_yc, "C1", f_hero, TEAL[:3] + (235,))
    glow = glow.filter(ImageFilter.GaussianBlur(size * 0.022))
    img.alpha_composite(Image.composite(glow, Image.new("RGBA", (size, size), (0, 0, 0, 0)), mask))

    d = ImageDraw.Draw(img)

    # crown: chevron+dot, small and refined
    s = size / 44 * 0.30
    chevrons(d, size * 0.5 - 22 * s, size * 0.085, s, GOLD, max(2, int(size * 0.011)))

    # hero "C1" — sharp teal on top of its own glow
    centered_text(d, size / 2, hero_yc, "C1", f_hero, TEAL)

    # thin gold rule
    rule_y = size * 0.635
    rule_w = size * 0.16
    d.line([(size / 2 - rule_w / 2, rule_y), (size / 2 + rule_w / 2, rule_y)],
           fill=GOLD, width=max(2, int(size * 0.0075)))

    # case number — quiet, smaller, cream
    f_case = ImageFont.truetype(MONO, int(size * 0.155))
    centered_text(d, size / 2, size * 0.79, "24", f_case, CREAM)

    return img

big = draw_icon(512)
big.save("icon-512.png")
big.resize((192, 192), Image.LANCZOS).save("icon-192.png")
big.resize((180, 180), Image.LANCZOS).save("apple-touch-icon.png")
big.resize((32, 32), Image.LANCZOS).save("favicon-32.png")
print("wrote icon-512.png, icon-192.png, apple-touch-icon.png, favicon-32.png")
