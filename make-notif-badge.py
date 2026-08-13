#!/usr/bin/env python3
"""Generate notif-badge.png — the small icon Android puts in the status bar and in the
corner of a notification.

This is NOT the app icon, and using the app icon for it is why notifications were showing a
grey blob: Android takes the badge, throws away every colour in it, and tints whatever alpha
remains. A full-colour 192px PNG is opaque edge to edge, so all it has to tint is a solid
square. A badge has to be a white silhouette on transparency.

It also has to survive being drawn at about 24dp. The app icon's three stacked chevrons turn
to mush at that size, so this uses the two strongest ones plus the dot — still recognisably
CourtReach's approaching mark, still legible in a status bar.

Drawn at 8x and downsampled, because PIL has no antialiasing and no round line caps; the
caps are circles at each end and the smoothing comes from the resample.

    python3 make-notif-badge.py
"""
from PIL import Image, ImageDraw

OUT = "notif-badge.png"
SIZE = 96          # what Android asks for
SS = 8             # supersample factor
C = SIZE * SS

# Geometry is in the icon's own 512 coordinate space (see icon-source.svg) — but scaled to
# the CONTENT's bounding box, not the 512 canvas. The badge only keeps two of the three
# chevrons, and fitting the full canvas left the kept artwork a speck in an empty frame
# (the first build of this produced exactly that). Bounds cover the kept strokes plus half
# a stroke width, and the dot.
W_SRC = 30.0
X0, X1 = 140 - W_SRC / 2, 372 + W_SRC / 2
Y0, Y1 = 158 - 20 - 4,    314 + W_SRC / 2          # dot top .. lowest chevron's feet
INSET = 0.10
span = max(X1 - X0, Y1 - Y0)
scale = (C * (1 - 2 * INSET)) / span
offx = (C - (X1 - X0) * scale) / 2
offy = (C - (Y1 - Y0) * scale) / 2


def p(x, y):
    return (offx + (x - X0) * scale, offy + (y - Y0) * scale)


def stroke(d, pts, w):
    """A polyline with round caps and joins, faked with circles at every vertex."""
    r = w / 2
    for a, b in zip(pts, pts[1:]):
        d.line([a, b], fill=255, width=int(round(w)))
    for x, y in pts:
        d.ellipse([x - r, y - r, x + r, y + r], fill=255)


img = Image.new("L", (C, C), 0)
d = ImageDraw.Draw(img)

W = W_SRC * scale     # a touch heavier than the app icon's 26, to hold up when shrunk

# the two upper chevrons — the lowest, faintest one is dropped as unreadable at this size
stroke(d, [p(140, 314), p(256, 224), p(372, 314)], W)
stroke(d, [p(154, 244), p(256, 164), p(358, 244)], W)

# the live dot
cx, cy = p(256, 158)
r = 20 * scale
d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)

img = img.resize((SIZE, SIZE), Image.LANCZOS)

# white, with the drawing itself as the alpha channel — that is the shape Android tints
out = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 0))
out.putalpha(img)
out.save(OUT)
print(f"wrote {OUT} ({SIZE}x{SIZE}, alpha-only silhouette)")
