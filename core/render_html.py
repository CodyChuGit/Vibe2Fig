#!/usr/bin/env python3
"""Render spec IR to pixel-exact HTML (one page per screen).

Mirrors core/runtime.js semantics: stacks -> flexbox, z -> absolute, text ->
bumped font mapping, component instances -> expanded templates. Output is
consumed by Figma's generate_figma_design capture (rate-limit-exempt) or by a
browser for visual verification. Fonts load from the app repo's own TTFs;
images use image-rendering: pixelated to honor SwiftUI .interpolation(.none).

Usage: render_html.py <project_dir> <assets_src_dir> <out_dir> [spec ...]
"""
import json
import shutil
import sys
from pathlib import Path


def bumped(raw):
    if raw < 11: return 12
    if raw < 12: return 13
    if raw < 28: return raw + 2
    return raw


def family_for(size):
    if size < 20: return "Jersey 15"
    if size < 28: return "Jersey 20"
    return "Jersey 25"


class Renderer:
    def __init__(self, tokens, asset_files):
        self.colors = {**{k: v for k, v in tokens["colors"].items()},
                       **{f"type_{k}": v for k, v in tokens["typeColors"].items()}}
        self.asset_files = asset_files  # key -> relative file path in out dir

    def css_color(self, spec, default="text"):
        if spec is None:
            spec = default
        if isinstance(spec, str):
            spec = {"token": spec}
        if "token" in spec:
            r, g, b = self.colors[spec["token"]]
        else:
            r, g, b = spec["rgb"]
        a = spec.get("opacity", 1)
        return f"rgba({round(r*255)},{round(g*255)},{round(b*255)},{a})"

    def text(self, spec):
        size = bumped(spec["px"])
        fam = spec.get("family") or family_for(size)
        style = (f"font-family:'{fam}';font-size:{size}px;line-height:1.1;"
                 f"color:{self.css_color(spec.get('color'))};"
                 f"text-align:{spec.get('align','center')};white-space:pre-wrap;")
        if spec.get("maxW"):
            style += f"width:{spec['maxW']}px;"
        else:
            style += "white-space:nowrap;"
        if "opacity" in spec:
            style += f"opacity:{spec['opacity']};"
        return f'<div style="{style}">{spec["s"]}</div>'

    def stroke_css(self, node):
        css = ""
        if node.get("stroke"):
            s = node["stroke"]
            css += f"border:{s.get('weight',1)}px solid {self.css_color(s['color'])};box-sizing:border-box;"
        return css

    def inner_line(self, color="borderDim", opacity=None, radius=6, inset=2):
        c = self.css_color({"token": color, "opacity": opacity} if opacity else color)
        return (f'<div style="position:absolute;left:{inset}px;top:{inset}px;right:{inset}px;'
                f'bottom:{inset}px;border:1px solid {c};border-radius:{radius}px;pointer-events:none;"></div>')

    def img(self, spec):
        path = self.asset_files[spec["asset"]]
        op = f"opacity:{spec['opacity']};" if "opacity" in spec else ""
        if spec.get("tint"):
            # template-image tinting (PixelIconView): CSS mask + tint background
            c = self.css_color(spec["tint"])
            return (f'<div style="width:{spec["w"]}px;height:{spec["h"]}px;background:{c};'
                    f'-webkit-mask:url({path}) center/contain no-repeat;'
                    f'mask:url({path}) center/contain no-repeat;{op}"></div>')
        return (f'<img src="{path}" style="width:{spec["w"]}px;height:{spec["h"]}px;'
                f'object-fit:contain;image-rendering:pixelated;{op}">')

    def button(self, spec):
        min_h = spec.get("minH", 40)
        tint = spec.get("tint", "text")
        prom = spec.get("prominent", False)
        bg = self.css_color(tint if prom else "panel")
        border = self.css_color(spec.get("border") or (tint if prom else "border"))
        label_color = self.css_color("panelDeep" if prom else tint)
        w = f"width:{spec['w']}px;" if spec.get("w") else ""
        fs = bumped(12 if min_h < 34 else 14)
        cursor = (f'<span style="font-family:\'Jersey 15\';font-size:12px;'
                  f'color:{self.css_color("cursor")};margin-right:4px;">▶</span>') if spec.get("cursor") else ""
        inner = self.inner_line("panelDeep" if prom else "borderDim", 0.4 if prom else None)
        return (f'<div style="position:relative;{w}min-height:{min_h}px;display:flex;align-items:center;'
                f'justify-content:center;background:{bg};border:2px solid {border};border-radius:8px;'
                f'box-sizing:border-box;">{cursor}<span style="font-family:\'Jersey 15\';font-size:{fs}px;'
                f'color:{label_color};">{spec["label"]}</span>{inner}</div>')

    def bar(self, tint, filled, segs, seg_w):
        cells = "".join(
            f'<div style="width:{seg_w}px;height:6px;border-radius:1.5px;'
            f'background:{self.css_color(tint if i < filled else "panelDeep")};"></div>'
            for i in range(segs))
        return f'<div style="display:flex;gap:1.5px;">{cells}</div>'

    def instance(self, spec):
        comp = spec["comp"]
        o = spec.get("overrides", {})
        w = spec.get("w")
        if comp.startswith("FoodRow"):
            hl = "highlighted" in comp
            stroke = self.css_color("cursor" if hl else "border")
            name_c = self.css_color("cursor" if hl else "text")
            return (f'<div style="width:{w or 200}px;height:50px;display:flex;align-items:center;gap:6px;'
                    f'padding:5px;background:{self.css_color("panel")};border:2px solid {stroke};'
                    f'border-radius:8px;box-sizing:border-box;justify-content:space-between;">'
                    f'<div style="display:flex;align-items:center;gap:6px;">'
                    f'<img src="{self.asset_files["item_icon"]}" style="width:24px;height:24px;object-fit:contain;image-rendering:pixelated;">'
                    f'<div style="display:flex;flex-direction:column;gap:1px;align-items:flex-start;">'
                    f'<span style="font-family:\'Jersey 15\';font-size:17px;color:{name_c};">{o.get("name","Item")}</span>'
                    f'<span style="font-family:\'Jersey 15\';font-size:14px;color:{self.css_color("textDim")};">{o.get("effect","HP+8")}</span>'
                    f'</div></div>'
                    f'<span style="font-family:\'Jersey 15\';font-size:15px;color:{self.css_color("cursor")};">{o.get("count","×1")}</span></div>')
        if comp.startswith("ToggleRow"):
            on = comp.endswith("/on")
            knob_x = 16 if on else 2
            track = self.css_color("cursor") if on else "rgb(56,56,61)"
            return (f'<div style="width:{w or 200}px;height:40px;display:flex;align-items:center;'
                    f'justify-content:space-between;padding:0 8px;background:{self.css_color("panel")};'
                    f'border:2px solid {self.css_color("border")};border-radius:8px;box-sizing:border-box;">'
                    f'<span style="font-family:\'Jersey 15\';font-size:16px;color:{self.css_color("text")};">{o.get("label","Toggle")}</span>'
                    f'<div style="position:relative;width:34px;height:20px;border-radius:10px;background:{track};">'
                    f'<div style="position:absolute;top:2px;left:{knob_x}px;width:16px;height:16px;border-radius:8px;background:#fff;"></div>'
                    f'</div></div>')
        if comp.startswith("StatBar"):
            icon = comp.split("/")[1]
            tint = {"health": "hp", "pp": "pp", "adventure": "adventure"}[icon]
            filled = int(o.get("filled", 9))
            return (f'<div style="display:flex;align-items:center;gap:4px;">'
                    f'<img src="{self.asset_files["icon_" + icon]}" style="width:10px;height:10px;'
                    f'object-fit:contain;image-rendering:pixelated;margin:0 1px;">'
                    f'{self.bar(tint, filled, 12, 5.96)}</div>')
        if comp.startswith("PixelBar"):
            tint = comp.split("/")[1]
            filled = int(o.get("filled", 7))
            return self.bar(tint, filled, 10, 5.05)
        if comp.startswith("RunChip"):
            sel = comp.endswith("selected")
            stroke = f'2.5px solid {self.css_color("cursor")}' if sel else f'1px solid {self.css_color("border")}'
            color = self.css_color("cursor" if sel else "textDim")
            return (f'<div style="display:inline-block;padding:5px 8px;background:{self.css_color({"token":"panel","opacity":0.85})};'
                    f'border:{stroke};border-radius:5px;box-sizing:border-box;">'
                    f'<span style="font-family:\'Jersey 15\';font-size:14px;color:{color};">RUN</span></div>')
        if comp.startswith("MoveTile"):
            sel = comp.endswith("selected")
            unaff = comp.endswith("unaffordable")
            fill = self.css_color(spec.get("fill", "type_electric"))
            stroke = f'2.5px solid {self.css_color("cursor")}' if sel else "1.5px solid rgba(255,255,255,0.35)"
            op = "opacity:0.35;" if unaff else ""
            return (f'<div style="width:{w or 81.5}px;height:26px;display:flex;flex-direction:column;'
                    f'align-items:center;justify-content:center;background:{fill};border:{stroke};'
                    f'border-radius:5px;box-sizing:border-box;{op}line-height:0.85;">'
                    f'<span style="font-family:\'Jersey 15\';font-size:15px;color:#fff;">{o.get("name","ACTION")}</span>'
                    f'<span style="font-family:\'Jersey 15\';font-size:12px;color:rgba(255,255,255,0.75);">{o.get("power","40")}</span></div>')
        if comp == "DialogPanel":
            return (f'<div style="position:relative;width:{w or 184}px;padding:8px;background:{self.css_color("panel")};'
                    f'border:2px solid {self.css_color("border")};border-radius:8px;box-sizing:border-box;">'
                    f'<div style="font-family:\'Jersey 15\';font-size:15px;color:{self.css_color("text")};'
                    f'text-align:left;">{o.get("message","...")}</div>{self.inner_line()}'
                    f'<div style="position:absolute;right:4px;bottom:2px;width:0;height:0;'
                    f'border-left:4px solid transparent;border-right:4px solid transparent;'
                    f'border-top:6px solid {self.css_color("cursor")};"></div></div>')
        if comp == "PixelCursor":
            return f'<span style="font-family:\'Jersey 15\';font-size:12px;color:{self.css_color("cursor")};">▶</span>'
        raise KeyError(f"no HTML template for component {comp}")

    def node(self, spec):
        t = spec["t"]
        if t == "text": return self.text(spec)
        if t == "img": return self.img(spec)
        if t == "button": return self.button(spec)
        if t == "instance": return self.instance(spec)
        if t == "spacer": return '<div style="flex:1;"></div>'
        if t == "bar": return self.bar(spec["tint"], spec["filled"], spec.get("segments", 10), spec.get("segW", 10))
        if t in ("rect", "circle"):
            d = spec.get("d")
            w, h = (d, d) if d else (spec.get("w", 10), spec.get("h", 10))
            radius = "50%" if t == "circle" else f"{spec.get('radius', 0)}px"
            css = (f"width:{w}px;height:{h}px;border-radius:{radius};"
                   f"background:{self.css_color(spec['fill']) if spec.get('fill') else 'transparent'};")
            if spec.get("blur"): css += f"filter:blur({spec['blur']}px);"
            if "opacity" in spec: css += f"opacity:{spec['opacity']};"
            css += self.stroke_css(spec)
            return f'<div style="{css}"></div>'
        if t == "z":
            kids = []
            for c in spec.get("children", []):
                inner = self.node(c)
                if c.get("abs"):
                    a = c["abs"]
                    pos = (f'right:{a["right"]}px;' if "right" in a else f'left:{a["x"]}px;')
                    pos += f'top:{a["y"]}px;'
                else:
                    dx, dy = c.get("dx", 0), c.get("dy", 0)
                    pos = (f'left:calc(50% + {dx}px);top:calc(50% + {dy}px);'
                           f'transform:translate(-50%,-50%);')
                kids.append(f'<div style="position:absolute;{pos}">{inner}</div>')
            css = (f'position:relative;width:{spec.get("w",100)}px;height:{spec.get("h",100)}px;'
                   f'overflow:{"visible" if spec.get("clip") is False else "hidden"};')
            if spec.get("fill"): css += f"background:{self.css_color(spec['fill'])};"
            if spec.get("radius"): css += f"border-radius:{spec['radius']}px;"
            return f'<div style="{css}">{"".join(kids)}</div>'
        if t in ("stack", "panel"):
            is_panel = t == "panel"
            direction = "row" if spec.get("dir") == "h" else "column"
            gap = spec.get("spacing", 4 if is_panel else 0)
            pad = spec.get("pad", 8 if is_panel else 0)
            pa = pad if isinstance(pad, list) else [pad] * 4
            align = {"start": "flex-start", "center": "center", "end": "flex-end"}[spec.get("align", "center")]
            justify = {"start": "flex-start", "center": "center", "end": "flex-end",
                       "between": "space-between"}[spec.get("justify", "start")]
            css = (f'display:flex;flex-direction:{direction};gap:{gap}px;'
                   f'padding:{pa[0]}px {pa[1]}px {pa[2]}px {pa[3]}px;'
                   f'align-items:{align};justify-content:{justify};box-sizing:border-box;')
            if is_panel:
                css += (f'position:relative;background:{self.css_color(spec.get("fill","panel"))};'
                        f'border:2px solid {self.css_color("border")};border-radius:8px;')
            else:
                if spec.get("fill"): css += f"background:{self.css_color(spec['fill'])};"
                if spec.get("radius"): css += f"border-radius:{spec['radius']}px;"
                css += self.stroke_css(spec)
            if isinstance(spec.get("w"), (int, float)): css += f'width:{spec["w"]}px;'
            if isinstance(spec.get("h"), (int, float)): css += f'height:{spec["h"]}px;'
            body = "".join(self.node(c) for c in spec.get("children", []))
            if is_panel:
                body += self.inner_line()
            return f'<div style="{css}">{body}</div>'
        raise KeyError(f"unknown node type {t}")

    def screen(self, spec):
        root_html = self.node(spec["root"])
        w, h = spec.get("w", 208), spec.get("h", 248)
        if spec.get("rootLayout") == "manual":
            # manual: children of root are already absolutely positioned via z
            placement = "position:absolute;left:0;top:0;"
        elif spec.get("rootY") is not None:
            placement = f'position:absolute;top:{spec["rootY"]}px;left:50%;transform:translateX(-50%);'
        else:
            placement = ('position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);')
        return (f'<div id="screen" style="position:relative;width:{w}px;height:{h}px;'
                f'border-radius:{spec.get("cornerRadius",52)}px;overflow:hidden;'
                f'background:{self.css_color(spec.get("bg","bg"))};">'
                f'<div style="{placement}">{root_html}</div></div>')


FONT_CSS = """
@font-face { font-family: 'Jersey 15'; src: url('fonts/Jersey15-Regular.ttf'); }
@font-face { font-family: 'Jersey 20'; src: url('fonts/Jersey20-Regular.ttf'); }
@font-face { font-family: 'Jersey 25'; src: url('fonts/Jersey25-Regular.ttf'); }
* { margin: 0; }
body { background: #1a1a1a; display: grid; place-items: start; padding: 16px; }
"""


def main():
    project, assets_src, out_dir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    names = sys.argv[4:]
    tokens = json.loads((project / "tokens.json").read_text())
    manifest = json.loads((project / "asset_manifest.json").read_text())
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "assets").mkdir(exist_ok=True)
    (out_dir / "fonts").mkdir(exist_ok=True)
    asset_files = {}
    for key, src in manifest.items():
        # key-based filename: front/back sprites share basenames upstream
        dst = out_dir / "assets" / f"{key}{Path(src).suffix}"
        if not dst.exists():
            shutil.copy(src, dst)
        asset_files[key] = f"assets/{dst.name}"
    for ttf in ["Jersey15-Regular.ttf", "Jersey20-Regular.ttf", "Jersey25-Regular.ttf"]:
        src = assets_src / "Fonts" / ttf
        dst = out_dir / "fonts" / ttf
        if not dst.exists():
            shutil.copy(src, dst)
    r = Renderer(tokens, asset_files)
    for name in names:
        spec = json.loads((project / "specs" / f"{name}.json").read_text())
        html = (f"<meta charset=\"utf-8\"><title>{spec['name']}</title>"
                f"<style>{FONT_CSS}</style>\n{r.screen(spec)}")
        (out_dir / f"{name}.html").write_text(html)
        print(f"rendered {name}.html")


if __name__ == "__main__":
    main()
