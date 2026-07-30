#!/usr/bin/env python3
"""Diff two spec IR trees (v2 sync): canonical snapshot vs fresh extraction.

usage: spec_diff.py old.json new.json [--anchors anchors.json] [--md]
Output: JSON ops on stdout (and a markdown change order with --md).

Ops: {op:set, path, key, old, new} | {op:add|remove, path, node}
Numeric changes under TOL pt are ignored (render noise).
Children pair by (t, name) when names are unique, else by index.
Anchors file: [{"match": "substring of path", "file": "...", "symbol": "...",
               "note": "..."}] — first match wins, attached to each op.
"""
import json
import sys

TOL = 0.5
SCALARS = ["x", "y", "w", "h", "d", "spacing", "pt", "s", "radius", "opacity",
           "dir", "align", "justify", "family", "comp", "asset", "clip", "hidden"]


def num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def same(a, b):
    if num(a) and num(b):
        return abs(a - b) <= TOL
    return a == b


def flat(node):
    """Scalar attrs incl. abs position and pad/fill/color/text serialized."""
    out = {}
    for k in SCALARS:
        if k in node:
            out[k] = node[k]
    if "abs" in node:
        out["x"] = node["abs"].get("x")
        out["y"] = node["abs"].get("y")
    if "pad" in node:
        out["pad"] = json.dumps(node["pad"])
    for k in ("fill", "color", "stroke"):
        if k in node:
            out[k] = json.dumps(node[k], sort_keys=True)
    if "text" in node:  # instance text overrides
        for tn, chars in node["text"].items():
            out[f"text:{tn}"] = chars
    return out


def label(node):
    return node.get("name") or node.get("s") or node.get("comp") or node.get("t", "?")


def pair(old_kids, new_kids):
    """Pair children by (t,name) when unique on both sides, else by index."""
    def key(n):
        return (n.get("t"), n.get("name"))
    ok = {}
    for i, n in enumerate(old_kids):
        ok.setdefault(key(n), []).append(i)
    nk = {}
    for i, n in enumerate(new_kids):
        nk.setdefault(key(n), []).append(i)
    pairs, used_o, used_n = [], set(), set()
    for k, ois in ok.items():
        nis = nk.get(k, [])
        if len(ois) == 1 and len(nis) == 1:
            pairs.append((ois[0], nis[0]))
            used_o.add(ois[0]); used_n.add(nis[0])
    ro = [i for i in range(len(old_kids)) if i not in used_o]
    rn = [i for i in range(len(new_kids)) if i not in used_n]
    for oi, ni in zip(ro, rn):
        if key(old_kids[oi]) == key(new_kids[ni]) or True:
            pairs.append((oi, ni)); used_o.add(oi); used_n.add(ni)
    removed = [i for i in range(len(old_kids)) if i not in used_o]
    added = [i for i in range(len(new_kids)) if i not in used_n]
    pairs.sort()
    return pairs, removed, added


def diff(old, new, path, ops):
    fo, fn = flat(old), flat(new)
    for k in sorted(set(fo) | set(fn)):
        a, b = fo.get(k), fn.get(k)
        if not same(a, b):
            ops.append({"op": "set", "path": path, "key": k, "old": a, "new": b})
    oc, nc = old.get("children", []), new.get("children", [])
    pairs, removed, added = pair(oc, nc)
    for oi, ni in pairs:
        diff(oc[oi], nc[ni], f"{path}/{label(nc[ni])}", ops)
    for i in removed:
        ops.append({"op": "remove", "path": f"{path}/{label(oc[i])}",
                    "node": {"t": oc[i].get("t"), "name": oc[i].get("name")}})
    for i in added:
        ops.append({"op": "add", "path": f"{path}/{label(nc[i])}",
                    "node": {k: v for k, v in nc[i].items() if k != "children"}})


def attach_anchors(ops, anchors):
    for op in ops:
        for a in anchors:
            if a["match"].lower() in op["path"].lower():
                op["anchor"] = {k: a[k] for k in ("file", "symbol", "note") if k in a}
                break


def markdown(name, ops):
    lines = [f"## Change order — {name}", ""]
    if not ops:
        lines.append("No differences — Figma and canonical spec are in sync.")
    for op in ops:
        if op["op"] == "set":
            lines.append(f"- `{op['path']}` · **{op['key']}**: {op['old']} → {op['new']}")
        else:
            lines.append(f"- **{op['op'].upper()}** `{op['path']}`")
        if "anchor" in op:
            an = op["anchor"]
            lines.append(f"  - source: `{an.get('file')}` — {an.get('symbol')}"
                         + (f" ({an['note']})" if an.get("note") else ""))
    return "\n".join(lines)


def main():
    old = json.load(open(sys.argv[1]))
    new = json.load(open(sys.argv[2]))
    anchors = []
    if "--anchors" in sys.argv:
        anchors = json.load(open(sys.argv[sys.argv.index("--anchors") + 1]))
    ops = []
    for k in ("w", "h", "cornerRadius"):
        if not same(old.get(k), new.get(k)):
            ops.append({"op": "set", "path": old.get("name", "frame"), "key": k,
                        "old": old.get(k), "new": new.get(k)})
    diff(old["root"], new["root"], old.get("name", "frame"), ops)
    attach_anchors(ops, anchors)
    if "--md" in sys.argv:
        print(markdown(old.get("name", "frame"), ops), file=sys.stderr)
    print(json.dumps(ops, indent=1))


if __name__ == "__main__":
    main()
