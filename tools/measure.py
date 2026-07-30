#!/usr/bin/env python3
"""Pixel-measurement primitives for simulator captures (px -> pt).

Library + CLI. The CLI emits a generic content report per image: pt size,
horizontal content bands, and per-band bbox + column clusters. Project
scripts import the primitives for app-specific bands and color predicates.

Caveats that matter (see docs/GOTCHAS.md):
- glyph bbox != element box (trimmed art); anchor rows on symmetric glyphs
- use color predicates to isolate bars/meters from overlapping text
- a bbox spanning two visual elements is contamination, not data
"""
import json
import sys

from PIL import Image


def lit(p, thr=60):
    r, g, b = p[:3]
    return r + g + b > thr


# color-dominance predicates for bars/meters
def red(p):
    return p[0] > 120 and p[1] < 90 and p[2] < 90


def green(p):
    return p[1] > 120 and p[0] < 110 and p[2] < 110


def cyan(p):
    return p[2] > 140 and p[1] > 100 and p[0] < 120


def bbox(im, y0, y1, x0=0, x1=None, pred=lit, scale=2):
    """Bounding box of pred-true pixels in a band, in pt (right/bottom exclusive)."""
    px = im.load()
    W, H = im.size
    x1 = x1 or W
    mnx, mny, mxx, mxy = 10**9, 10**9, -1, -1
    for y in range(max(0, int(y0)), min(H, int(y1))):
        for x in range(int(x0), int(x1)):
            if pred(px[x, y]):
                mnx = min(mnx, x); mxx = max(mxx, x)
                mny = min(mny, y); mxy = max(mxy, y)
    if mxx < 0:
        return None
    return [mnx / scale, mny / scale, (mxx + 1) / scale, (mxy + 1) / scale]


def row_bands(im, thr=60, min_gap_px=8):
    """Horizontal bands of content: [y0_px, y1_px] runs of lit rows, gaps merged."""
    px = im.load()
    W, H = im.size
    rows = []
    for y in range(H):
        rows.append(any(lit(px[x, y], thr) for x in range(0, W, 2)))
    bands, start = [], None
    for y, on in enumerate(rows):
        if on and start is None:
            start = y
        if not on and start is not None:
            if bands and y - bands[-1][1] < min_gap_px:
                bands[-1][1] = y
            else:
                bands.append([start, y])
            start = None
    if start is not None:
        bands.append([start, H])
    return bands


def col_clusters(im, y0, y1, min_gap_px=10, scale=2, pred=lit):
    """x-ranges (pt) of content clusters within a band — e.g. icons in a row."""
    px = im.load()
    W, H = im.size
    cols = [any(pred(px[x, y]) for y in range(int(y0), min(int(y1), H)))
            for x in range(W)]
    runs, s = [], None
    for x, on in enumerate(cols):
        if on and s is None:
            s = x
        if not on and s is not None:
            if runs and x - runs[-1][1] < min_gap_px:
                runs[-1][1] = x
            else:
                runs.append([s, x])
            s = None
    if s is not None:
        runs.append([s, len(cols)])
    return [[a / scale, b / scale] for a, b in runs]


def report(path, scale=2):
    im = Image.open(path).convert("RGB")
    W, H = im.size
    out = {"pt": [W / scale, H / scale], "bands": []}
    for y0, y1 in row_bands(im):
        out["bands"].append({
            "y_pt": [y0 / scale, y1 / scale],
            "bbox": bbox(im, y0, y1, scale=scale),
            "clusters": col_clusters(im, y0, y1, scale=scale),
        })
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    scale = 2
    for a in sys.argv[1:]:
        if a.startswith("--scale="):
            scale = float(a.split("=")[1])
    if not args:
        sys.exit("usage: measure.py <image.png> [...] [--scale=2]")
    print(json.dumps({p: report(p, scale) for p in args}, indent=1))
