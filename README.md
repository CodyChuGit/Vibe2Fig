# code2figma

Reverse-engineer a real codebase into an **editable, componentized Figma file** —
tokens, components, and per-screen frames — with the code as the only source of
truth (no screenshot tracing). End goal: a bidirectional toolkit where Figma
edits flow back into the codebase.

```
┌─────────────┐   adapter    ┌──────────────┐   generator   ┌────────────┐
│  codebase    │ ──────────▶ │  spec IR      │ ────────────▶ │  Figma file │
│ SwiftUI/React│              │ tokens.json   │  runtime.js   │ vars/comps/ │
│              │ ◀────────── │ digests/*.yaml│ ◀──────────── │ frames      │
└─────────────┘  sync (v2)   │ specs/*.json  │  get_metadata └────────────┘
                              └──────────────┘
```

## Pipeline (v1 — code → Figma)

1. **Adapter** (`adapters/<framework>/`) extracts the design system from source:
   - `extract_tokens.py` regex-parses color/radius/typography constants into
     `tokens.json` (re-runnable; code changes flow through).
   - **Layout digests** (`projects/<app>/digests/*.yaml`): per-screen layout
     trees resolved for a concrete viewport (fonts bumped, GeometryReader math
     evaluated, conditionals pinned to representative states). Produced by an
     LLM reading the source — this is deliberate: real-world SwiftUI/JSX layout
     is Turing-complete, so a static parser can't fully resolve it; an LLM pass
     with the digest contract (see `core/spec_schema.md`) can, and the output
     is reviewable + diffable.
2. **Spec IR** (`projects/<app>/specs/*.json`): declarative node trees
   (stack/z/text/img/instance/button/bar/panel…) referencing tokens by name and
   assets by key. This is the exchange format both directions share.
3. **Generator** (`core/runtime.js`): a Figma Plugin-API interpreter injected
   into each `use_figma` MCP call. It builds auto-layout frames with
   variable-bound fills, the exact font mapping, and component instances.
   `core/upload.py` pushes binary assets (sprites/icons) and records
   `imageHash`es.
4. **Error-correcting loop**: after every frame, `node.screenshot()` /
   `get_screenshot` output is compared against the digest; discrepancies are
   fixed with targeted scripts before moving on. State (variable/component/
   frame IDs) is persisted in `projects/<app>/state.json` so runs are
   resumable and idempotent.

## Layout

```
core/       runtime.js (Plugin-API interpreter), upload.py, spec_schema.md
adapters/   swiftui/ (extract_tokens.py, digest contract), react/ (plan)
sync/       Figma → code roadmap (v2)
projects/   one dir per app: tokens, digests, specs, asset_manifest, state.json
```

## Requirements

- Figma MCP server (`claude mcp add --transport http figma https://mcp.figma.com/mcp`)
- The app's asset files on disk (uploaded via `upload_assets` MCP + `core/upload.py`)

## Prior art / leverage (as of early 2026)

- **Figma official MCP** — `use_figma` (Plugin API execution), `upload_assets`,
  `generate_figma_design` (live-web capture; covers running React apps),
  `get_design_context` + **Code Connect** (design→code direction + node↔component mapping).
- **Tokens Studio / style-dictionary** — token sync formats worth adopting for
  `tokens.json` interop.
- **react-figma** — renders React components into Figma; candidate backend for
  the React adapter's component pass.
- **story.to.design / html.to.design** — commercial capture of rendered HTML;
  validation baseline, not editable-first like this pipeline.

## Roadmap

- **v1 (this repo)**: SwiftUI adapter proven on `projects/pilot_app`
  (watchOS, 25+ frames, 10 component sets, 27 bound variables).
- **v1.5**: React adapter (see `adapters/react/README.md`) — tokens from
  Tailwind/CSS vars, digests from JSX, same spec IR and runtime.
- **v2**: Figma → code sync (see `sync/README.md`) — diff `get_metadata`
  against specs, map nodes to source via Code Connect anchors, emit minimal
  source patches.
