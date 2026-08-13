#!/usr/bin/env python3
"""Strip JS comments from the single <script type="module"> block in a CourtReach HTML file.

Deliberately NOT a regex over the JavaScript. This session has already been bitten once by
hand-rolled regex matching on escape sequences, and a comment-stripper that misjudges a
string or a regex literal doesn't fail loudly — it silently ships a broken app. So the
actual stripping is done by Terser, which parses the JavaScript properly. This script only
does the part regex is safe for: finding the <script type="module"> ... </script> boundaries
in the surrounding HTML, which contains no such block inside a string.

Everything outside that one block — markup, CSS, the inline non-module scripts if any ever
appear — is copied through byte for byte.

Usage: strip-comments.py <in.html> <out.html>
"""
import re
import subprocess
import sys
import tempfile
import os

OPEN = '<script type="module">'
CLOSE = '</script>'


def main():
    src, dst = sys.argv[1], sys.argv[2]
    html = open(src, encoding="utf-8").read()

    start = html.find(OPEN)
    if start == -1:
        raise SystemExit(f"{src}: no <script type=\"module\"> block found")
    if html.find(OPEN, start + 1) != -1:
        raise SystemExit(f"{src}: more than one module script — this script assumes exactly one")
    body_start = start + len(OPEN)
    end = html.find(CLOSE, body_start)
    if end == -1:
        raise SystemExit(f"{src}: module script is not closed")

    js = html[body_start:end]

    with tempfile.TemporaryDirectory() as tmp:
        js_in = os.path.join(tmp, "in.mjs")
        js_out = os.path.join(tmp, "out.mjs")
        open(js_in, "w", encoding="utf-8").write(js)
        # comments=false and nothing else. No mangle, no compress: the only thing being
        # removed is prose, so the emitted program is the same program.
        subprocess.run(
            ["npx", "terser", js_in, "--module", "--format", "comments=false", "-o", js_out],
            check=True,
        )
        stripped = open(js_out, encoding="utf-8").read()

    if not stripped.strip():
        raise SystemExit("terser produced an empty program — refusing to publish")

    out = html[:body_start] + "\n" + stripped + "\n" + html[end:]
    open(dst, "w", encoding="utf-8").write(out)

    saved = len(html) - len(out)
    print(f"{src} -> {dst}: {len(html):,} -> {len(out):,} bytes ({saved:,} of comments removed)")


if __name__ == "__main__":
    main()
