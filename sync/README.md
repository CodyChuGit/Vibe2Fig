# sync/ — v2: Figma → code

The reverse direction. **The canonical screen gallery page itself is the sync
surface** — no separate "production" page. Every frame there is a pure
`Screen/*` organism instance (+ system chrome), so layout edits happen on the
organism and molecule **masters** and propagate everywhere; the extractor
reads *through* instances (organism-transparent) into the full layout tree.
The extracted spec is diffed against a canonical snapshot; the diff becomes a
source-anchored change order the agent applies to code, then verifies against
a live render.

Proven round trip (SwiftUI pilot): a 4 pt HUD nudge in Figma → change order →
one-line code patch → rebuild → seeded-simulator capture measured the shift at
**exactly** +4.0 pt → code reverted → frame restored from canonical → clean
fixpoint (0 diff ops). The pilot surface carries the app's **entire screen
inventory** (21 frames, every screen family), each with a canonical snapshot
and a source-anchor map.

## Tools

| file | role |
|---|---|
| `figma_to_spec.js` | Plugin-API walker: frame → spec IR (stacks/z/text/rect/img/instance, variable→token, hash→asset, component→key reverse maps) |
| `extract_chunk.py` | assembles the runnable extraction script from a project's `state.json` ledger |
| `spec_diff.py` | structural diff (set/add/remove ops, ±0.5 pt tolerance) + markdown change order with source anchors |

## Flow

```
extract_chunk.py state.json  →  use_figma  →  extracted/*.json
spec_diff.py canonical/X.json extracted/X.json --anchors anchors/X.json --md
        →  ops + change order  →  agent patches source at the anchors
        →  rebuild + seeded capture + measure  →  pixels confirm
        →  update canonical snapshot (or restore Figma from it)
```

Per-project files live in `projects/<app>/sync/`:
`canonical/` (snapshots — the contract), `extracted/` (latest pull),
`anchors/` (node-path → source file/symbol maps).

## Rules

- The **canonical snapshot** is the arbitration point: Figma differs → change
  order for code; code changed → rebuild the frame and re-snapshot. Never edit
  a snapshot by hand.
- Extraction dialect stores **rendered pt** (not raw call-site sizes) — both
  sides of every diff come from the same extractor, so no font reverse-mapping
  is needed.
- A change order is not "applied" until a live render (simulator/browser)
  measures the change at the expected value.
- Anchors are substring matches on node paths, first match wins — keep them
  specific and keep the locked-value notes in `note`.
