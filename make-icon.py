#!/usr/bin/env python3
"""Regenerate CourtReach's PWA app icons — v4: logo/monogram ONLY, nothing else
(owner: "keep our logo and monogram in the app icon and nothing else"), in the
app's own GOLD (owner tried a sapphire app-wide sweep, then reverted: "Lets
revert to the gold scheme. Dont like this one. Use the Gold scheme for app
logo also").

Just the brand mark — chevron+dot + "CR" — centered on a deep-navy gradient
ground, with a soft glow behind it for a premium finish, no court-tile/C1/24
content.

Deterministic (Pillow + real TTFs, no base64). Run: python3 make-icon.py
Writes icon-512.png, icon-192.png, apple-touch-icon.png, favicon-32.png.
"""
import os, urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageFilter

GOLD = (203, 182, 130, 255)   # #cbb682 — the header monogram's own gold
GRAD_TOP    = (13, 17, 23, 255)
GRAD_BOTTOM = (22, 29, 39, 255)

SERIF = "/tmp/fonts/Fraunces.ttf"  # the app's REAL brand serif — same font as
                                   # "CourtReach"/"Court N"/case titles everywhere
                                   # else in the app (owner: didn't like the old
                                   # Georgia/Iowan-Old-Style stand-in's font)
SERIF_URL = ("https://raw.githubusercontent.com/google/fonts/main/ofl/fraunces/"
             "Fraunces%5BSOFT%2CWONK%2Copsz%2Cwght%5D.ttf")
if not os.path.exists(SERIF):
    os.makedirs(os.path.dirname(SERIF), exist_ok=True)
    print("downloading Fraunces…")
    urllib.request.urlretrieve(SERIF_URL, SERIF)

def serif_font(px):
    f = ImageFont.truetype(SERIF, px)
    try: f.set_variation_by_axes([0.0, 0.0, 72.0, 600.0])  # SOFT,WONK,opsz,wght
    except Exception: pass
    return f

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

    s = size / 44 * 0.90
    ox = size * 0.5 - 22 * s
    chev_oy = size * 0.055
    f_cr = serif_font(int(size * 0.31))
    cr_yc = size * 0.745

    # soft gold glow behind the whole mark
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    chevrons(gd, ox, chev_oy, s, GOLD[:3] + (200,), max(2, int(size * 0.021)))
    centered_text(gd, size / 2, cr_yc, "CR", f_cr, GOLD[:3] + (200,))
    glow = glow.filter(ImageFilter.GaussianBlur(size * 0.020))
    img.alpha_composite(Image.composite(glow, Image.new("RGBA", (size, size), (0, 0, 0, 0)), mask))

    d = ImageDraw.Draw(img)
    chevrons(d, ox, chev_oy, s, GOLD, max(2, int(size * 0.017)))
    centered_text(d, size / 2, cr_yc, "CR", f_cr, GOLD)

    return img

big = draw_icon(512)
big.save("icon-512.png")
big.resize((192, 192), Image.LANCZOS).save("icon-192.png")
big.resize((180, 180), Image.LANCZOS).save("apple-touch-icon.png")
big.resize((32, 32), Image.LANCZOS).save("favicon-32.png")
print("wrote icon-512.png, icon-192.png, apple-touch-icon.png, favicon-32.png")
