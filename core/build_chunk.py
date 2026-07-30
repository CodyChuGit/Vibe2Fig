#!/usr/bin/env python3
"""Assemble a use_figma `code` chunk: runtime + trimmed STATE + N specs + driver.

Usage: build_chunk.py <project_dir> <spec-name> [<spec-name>...] [--page "02 — Screens (46mm)"]
Prints the chunk to stdout (also saved to <project>/build/chunk.js).
Trimms STATE to only the tokens/assets/components the given specs reference,
keeping the chunk well under the 50k use_figma limit.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def collect_refs(node, refs):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "asset" and isinstance(v, str):
                refs["assets"].add(v)
            elif k == "comp" and isinstance(v, str):
                refs["components"].add(v)
            elif k in ("color", "fill", "tint", "border", "bg", "fillToken") and isinstance(v, str):
                refs["variables"].add(v)
            elif k in ("fill", "color", "stroke") and isinstance(v, dict) and "token" in v:
                refs["variables"].add(v["token"])
            else:
                collect_refs(v, refs)
    elif isinstance(node, list):
        for v in node:
            collect_refs(v, refs)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--page")]
    page = "02 — Screens (46mm)"
    for a in sys.argv[1:]:
        if a.startswith("--page="):
            page = a.split("=", 1)[1]
    project = Path(args[0])
    specs = []
    refs = {"assets": set(), "components": set(), "variables": set()}
    for name in args[1:]:
        spec = json.loads((project / "specs" / f"{name}.json").read_text())
        specs.append(spec)
        collect_refs(spec, refs)
    state = json.loads((project / "state.json").read_text())
    # buttons/panels/bars always need the core tokens
    refs["variables"] |= {"bg", "panel", "panelDeep", "border", "borderDim", "text", "textDim", "cursor"}
    trimmed = {
        "variables": {k: v for k, v in state["variables"].items() if k in refs["variables"]},
        "assets": {k: v for k, v in state["assets"].items() if k in refs["assets"]},
        "components": {k: v for k, v in state["components"].items() if k in refs["components"]},
    }
    runtime = (HERE / "runtime.js").read_text()
    driver = f"""
const PAGE_NAME = {json.dumps(page)};
const STATE = {json.dumps(trimmed)};
const SPECS = {json.dumps(specs)};
const page = figma.root.children.find(p => p.name === PAGE_NAME);
await figma.setCurrentPageAsync(page);
const results = [];
for (const S of SPECS) {{
  const r = await run(S, STATE);
  // optional per-spec fill-override pass (e.g. move-tile type colors)
  for (const pp of S.postProcess || []) {{
    const frame = await figma.getNodeByIdAsync(r.frameId);
    const target = frame.findOne(n => n.name === pp.nodeName || (n.type === "INSTANCE" && n.findOne(t => t.type === "TEXT" && t.characters === pp.nodeName)));
    if (target) target.fills = [makePaint(pp.fillToken, STATE)];
  }}
  results.push(r);
}}
for (const r of results) {{
  const f = await figma.getNodeByIdAsync(r.frameId);
  await f.screenshot();
}}
return results;
"""
    chunk = runtime + "\n" + driver
    out = project / "build" / "chunk.js"
    out.write_text(chunk)
    sys.stderr.write(f"chunk: {len(chunk)} chars -> {out}\n")
    print(chunk)


if __name__ == "__main__":
    main()
