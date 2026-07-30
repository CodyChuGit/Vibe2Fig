#!/usr/bin/env python3
"""Assemble the use_figma extraction script for a project's sync surface.

Reads the project ledger (state.json), builds the reverse maps
(variableId->token, imageHash->asset, componentId->key), prepends them to
figma_to_spec.js, and appends a driver that walks the PRODUCTION SCREENS
section and returns one spec per frame.

usage: extract_chunk.py projects/<app>/state.json [--section "PRODUCTION SCREENS"]
Prints the script to stdout; the agent executes it via use_figma and saves
the returned JSON to projects/<app>/sync/extracted/<frame>.json.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).parent


def build_maps(state):
    tokens = {}
    for name, vid in state.get("variables", {}).items():
        tokens[vid] = name
    # variables may also live under collections in newer ledgers
    for col in state.get("variableCollections", {}).values():
        for name, vid in col.get("vars", {}).items():
            tokens[vid] = name
    assets = {}
    for name, val in state.get("assets", {}).items():
        h = val if isinstance(val, str) else (val.get("hash") if isinstance(val, dict) else None)
        if h:
            assets[h] = name
    for name, val in state.get("assets_display_3x", {}).items():
        if isinstance(val, (list, tuple)) and val:
            assets[val[0]] = name
    comps = {}
    for key, cid in state.get("components", {}).items():
        comps[cid] = key
    return {"tokensById": tokens, "assetsByHash": assets, "compsById": comps}


def main():
    state_path = sys.argv[1]
    section = "PRODUCTION SCREENS"
    if "--section" in sys.argv:
        section = sys.argv[sys.argv.index("--section") + 1]
    state = json.load(open(state_path))
    maps = build_maps(state)
    lib = (HERE / "figma_to_spec.js").read_text()
    page = state.get("pages", {}).get("productionScreens", "")
    driver = f"""
// ---- driver ----
const page = {f"await figma.getNodeByIdAsync('{page}')" if page else "figma.currentPage"};
await figma.setCurrentPageAsync(page);
const sec = page.children.find(n=>n.type==='SECTION' && n.name.toUpperCase().includes({json.dumps(section)}));
if(!sec) throw new Error('no section named {section} on page '+page.name);
const frames = sec.children.filter(n=>n.type==='FRAME');
return frames.map(extractFrame);
"""
    print(f"const MAPS = {json.dumps(maps)};\n{lib}\n{driver}")


if __name__ == "__main__":
    main()
