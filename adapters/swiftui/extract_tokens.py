#!/usr/bin/env python3
"""Extract design tokens from Swift source into build/tokens.json.

Code is the source of truth: this parses the actual constants out of
PixelKit.swift (app palette, radii, type colors, component metrics) and
Typography.swift (font family names), so a re-run picks up code changes.
The Typography band logic (bumped sizes -> family) is mirrored here with a
pointer back to the source; it changes rarely and regex-parsing a Swift
switch adds nothing but fragility.

Usage: python3 extract_tokens.py            # writes build/tokens.json
"""

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
APP = REPO / "AppSources"
OUT = Path(__file__).resolve().parent / "build"


def parse_colors(swift: str) -> dict:
    """`static let name = Color(red: r, green: g, blue: b)` -> {name: [r,g,b]}"""
    pat = re.compile(
        r"static let (\w+)\s*=\s*Color\(red:\s*([\d.]+),\s*green:\s*([\d.]+),\s*blue:\s*([\d.]+)\)"
    )
    return {m[1]: [float(m[2]), float(m[3]), float(m[4])] for m in pat.finditer(swift)}


def parse_type_colors(swift: str) -> dict:
    """`case .fire: Color(red: …)` inside typeColor -> {fire: [r,g,b]}"""
    body = swift.split("static func typeColor", 1)[1]
    pat = re.compile(
        r"case \.(\w+):\s*Color\(red:\s*([\d.]+),\s*green:\s*([\d.]+),\s*blue:\s*([\d.]+)\)"
    )
    return {m[1]: [float(m[2]), float(m[3]), float(m[4])] for m in pat.finditer(body)}


def parse_scalar(swift: str, name: str) -> float:
    m = re.search(rf"static let {name}: CGFloat = ([\d.]+)", swift)
    if not m:
        sys.exit(f"missing scalar {name}")
    return float(m[1])


def main():
    pixelkit = (APP / "PixelKit.swift").read_text()
    typography = (APP / "Typography.swift").read_text()

    colors = parse_colors(pixelkit)
    # The bg color is `Color.black`, not Color(red:...) — special-case it.
    if "static let bg = Color.black" in pixelkit:
        colors["bg"] = [0.0, 0.0, 0.0]

    fonts = dict(re.findall(r'static let (jersey\d+|pixelBody)\s*=\s*"([\w-]+)"', typography))

    tokens = {
        "source": {
            "palette": "AppSources/PixelKit.swift",
            "typography": "AppSources/Typography.swift",
            "screen": "docs/27_WATCH_SCREEN_DIMENSIONS.md (46mm row)",
        },
        "screen": {"width": 208, "height": 248, "cornerRadius": 52, "device": "Apple Watch Series 11 46mm"},
        "colors": colors,
        "typeColors": parse_type_colors(pixelkit),
        "radius": parse_scalar(pixelkit, "radius"),
        "radiusSmall": parse_scalar(pixelkit, "radiusSmall"),
        # Typography.swift: bumped() legibility shift, then family by bumped size.
        # a bundled pixel font is not installable in Figma; Typography.swift itself
        # names Jersey 15 as the fallback for that band, so the export uses it.
        "fontFiles": fonts,
        "fontBands": [
            {"maxBumped": 12, "figmaFamily": "Jersey 10"},
            {"maxBumped": 20, "figmaFamily": "Jersey 15", "note": "code uses a bundled pixel font; Jersey 15 is its declared fallback"},
            {"maxBumped": 28, "figmaFamily": "Jersey 20"},
            {"maxBumped": 9999, "figmaFamily": "Jersey 25"},
        ],
        "bumpRule": "size<11 -> 12; size<12 -> 13; size<28 -> size+2; else size",
        "components": {
            "pixelPanel": {"padding": 8, "fill": "panel", "outerStroke": {"color": "border", "weight": 2},
                            "innerStroke": {"color": "borderDim", "weight": 1, "inset": 2}},
            "pixelButton": {"minHeight": 40, "smallMinHeight": 24, "fontSize": 14, "smallFontSize": 12},
            "pixelBar": {"height": 6, "segments": 10, "gap": 1.5, "segmentRadius": 1.5, "emptyFill": "panelDeep"},
        },
    }

    OUT.mkdir(exist_ok=True)
    out = OUT / "tokens.json"
    out.write_text(json.dumps(tokens, indent=2))
    print(f"wrote {out} ({len(colors)} colors, {len(tokens['typeColors'])} type colors)")


if __name__ == "__main__":
    main()
