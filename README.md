# Vibe2Fig

Reverse-engineer a real codebase into an **editable, componentized,
simulator-verified Figma file** — tokens, component sets, per-screen frames,
and documentation pages — with the code as the only source of truth (no
screenshot tracing). Proven end-to-end on a shipped watchOS app: 7 pages,
111+ component masters, 45 screen states, 5 device sizes, every exhibit
placed from measured simulator ground truth.

```
┌─────────────┐   adapter    ┌──────────────┐   generator   ┌────────────┐
│  codebase    │ ──────────▶ │  spec IR      │ ────────────▶ │  Figma file │
│ SwiftUI/React│              │ tokens.json   │  runtime.js   │ vars/comps/ │
│              │ ◀────────── │ digests/*.yaml│ ◀──────────── │ frames      │
└─────────────┘  sync (v2)   │ specs/*.json  │  screenshots  └────────────┘
        ▲                     └──────────────┘        │
        └── seeded simulators + tools/measure.py ─────┘   (the referee)
```

**The method in one sentence:** code supplies the numbers, seeded simulators
supply the rendered truth, the `state.json` ledger supplies the memory,
component sets supply the consistency, and a screenshot-verify loop closes
every write. Full rationale: [docs/SKILL_ANALYSIS.md](docs/SKILL_ANALYSIS.md).

## Install

Requirements: macOS (Xcode + simulators for the verification loop),
Python 3 + Pillow (`pip install pillow`), and
[Claude Code](https://claude.com/claude-code) with the Figma MCP server.

```bash
git clone https://github.com/CodyChuGit/Vibe2Fig.git
cd Vibe2Fig

# Figma MCP (once)
claude mcp add --transport http figma https://mcp.figma.com/mcp

# install the agent skill (once) — symlink keeps it updated with the repo
mkdir -p ~/.claude/skills
ln -s "$(pwd)/vibe2fig_skill" ~/.claude/skills/vibe2fig
```

## Agentic usage (the skill)

[`vibe2fig_skill/SKILL.md`](vibe2fig_skill/SKILL.md) turns the workflow into
an invocable Claude Code skill with **phase gates**: Register → Ground truth →
Foundations → Pages → Verify → Ledger/Update. Once installed, prompts like

- *"turn this app into a Figma file"* (first build, phases 0–5)
- *"add the new screens to the Figma"* / *"update the assets"* (update mode —
  diffs code against the ledger, builds only the delta)
- *"show the app at all device sizes in Figma"*

trigger it. The skill enforces the five hard rules (derive from code / place
from pixels; nothing raw on an exhibit; screenshot every write batch; ledger
everything; never touch a live save) and points the agent at
[docs/GOTCHAS.md](docs/GOTCHAS.md) — the session-tested trap list for the
Figma Plugin API, simulators, and pixel measurement.

## Quickstart (first build)

1. `cp projects/example/config.example.json projects/<app>/config.json` and
   fill it in (bundle id, **save path read from the persistence code**,
   device table).
2. Extract tokens: `python3 adapters/swiftui/extract_tokens.py …`
3. Write layout digests per [core/spec_schema.md](core/spec_schema.md)
   (LLM pass over source — reviewable, diffable YAML).
4. Ground truth: seed a deterministic save, then
   `python3 tools/capture.py --config projects/<app>/config.json --app <.app> --seed <save> --state home --out projects/<app>/captures/`
   and `python3 tools/measure.py projects/<app>/captures/*.png`.
5. Let the skill build foundations → pages, verifying each section against
   the captures, and persist everything to `projects/<app>/state.json`.

## Layout

```
vibe2fig_skill/  SKILL.md — the agentic workflow (symlink into ~/.claude/skills)
core/            runtime.js (Plugin-API interpreter), spec_schema.md,
                 upload.py, render_html.py, build_chunk.py
adapters/        swiftui/ (extract_tokens.py, digest contract), react/ (plan)
tools/           capture.py (seeded-sim harness), measure.py (px→pt)
docs/            SKILL_ANALYSIS.md (why this works), GOTCHAS.md (trap list)
projects/        your apps (git-ignored) — ledger, specs, captures. See
                 projects/README.md and projects/example/.
```

## Roadmap

- **v1 (now)**: SwiftUI → Figma, simulator-verified, incremental updates via
  the ledger.
- **v1.5**: React adapter — tokens from Tailwind/CSS vars, digests from JSX,
  same spec IR and runtime.
- **v2**: Figma → code sync — diff `get_metadata` against specs, map nodes to
  source via Code Connect anchors, emit minimal source patches. The ledger +
  measured geometry make the diff tractable.

## License

MIT — see [LICENSE](LICENSE).
