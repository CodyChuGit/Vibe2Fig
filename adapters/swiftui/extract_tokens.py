#!/usr/bin/env python3
"""Extract design tokens from Swift source into tokens.json.

Code is the source of truth: this parses the actual constants out of the app's
design-system file (color statics, radii, semantic color switches) and its
typography file (font family names), so a re-run picks up code changes.

The bits a parser cannot know — which files to read, the target screen, and the
font band table (size -> Figma family, after the app's own size transform) —
come from a profile JSON. Copy `tokens.profile.example.json` and fill it in.

Usage: extract_tokens.py <app_src_dir> <profile.json> [out.json]
"""

import json
import re
import sys
from pathlib import Path


def parse_colors(swift: str) -> dict:
    """`static let name = Color(red: r, green: g, blue: b)` -> {name: [r,g,b]}"""
    pat = re.compile(
        r"static let (\w+)\s*=\s*Color\(red:\s*([\d.]+),\s*green:\s*([\d.]+),\s*blue:\s*([\d.]+)\)"
    )
    return {m[1]: [float(m[2]), float(m[3]), float(m[4])] for m in pat.finditer(swift)}


def parse_case_colors(swift: str, func: str) -> dict:
    """`case .name: Color(red: …)` inside a semantic color switch -> {name: [r,g,b]}"""
    if f"static func {func}" not in swift:
        return {}
    body = swift.split(f"static func {func}", 1)[1]
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
    if len(sys.argv) < 3:
        sys.exit(__doc__.strip().splitlines()[-1])
    app = Path(sys.argv[1])
    profile = json.loads(Path(sys.argv[2]).read_text())
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("tokens.json")

    palette = (app / profile["paletteFile"]).read_text()
    typography = (app / profile["typographyFile"]).read_text()

    colors = parse_colors(palette)
    # Color statics written as `Color.black` / `Color.white` skip the regex.
    for name, rgb in profile.get("literalColors", {}).items():
        if f"static let {name} = Color." in palette:
            colors[name] = rgb

    fonts = dict(re.findall(profile["fontFilePattern"], typography))

    tokens = {
        "source": {
            "palette": f'{app.name}/{profile["paletteFile"]}',
            "typography": f'{app.name}/{profile["typographyFile"]}',
            "screen": profile.get("screenSource", ""),
        },
        "screen": profile["screen"],
        "colors": colors,
        "typeColors": parse_case_colors(palette, profile.get("caseColorFunc", "")),
        "fontFiles": fonts,
        # Size transform (legibility bump, dynamic type, …) applies BEFORE family
        # selection; both live in the app's typography file, mirrored in profile.
        "fontBands": profile["fontBands"],
        "bumpRule": profile["bumpRule"],
        "components": profile.get("components", {}),
    }
    for name in profile.get("scalars", []):
        tokens[name] = parse_scalar(palette, name)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(tokens, indent=2))
    print(f"wrote {out} ({len(colors)} colors, {len(tokens['typeColors'])} case colors)")


if __name__ == "__main__":
    main()
