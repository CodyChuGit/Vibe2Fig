# Vibe2Fig

Reverse-engineer a **SwiftUI or React** codebase into an **editable,
componentized, render-verified Figma file** — tokens, component sets,
per-screen frames, and documentation pages — with the code as the only source
of truth (no screenshot tracing). Works with any SwiftUI or React program.

![Vibe2Fig — your code becomes componentized Figma, and Figma edits become updated code](docs/pipeline.png)

**The method in one sentence:** code supplies the numbers, a seeded running
app (simulator for SwiftUI, browser for React) supplies the rendered truth,
the `state.json` ledger supplies the memory, component sets supply the
consistency, and a screenshot-verify loop closes every write. Full rationale:
[docs/SKILL_ANALYSIS.md](docs/SKILL_ANALYSIS.md).

## Install

One command — clones (or updates) the repo, installs dependencies, registers
the Figma MCP server, and installs the agent skill:

```bash
curl -fsSL https://raw.githubusercontent.com/CodyChuGit/Vibe2Fig/main/install.sh | bash
```

Already cloned? Just run `./install.sh` — it's idempotent.

### Dependencies

Installed or checked by `install.sh`:

| Dependency | Used for | Auto-installed? |
|---|---|---|
| Python 3 + [Pillow](https://pypi.org/project/pillow/) | capture, pixel measurement, asset prep | yes (`pip`) |
| [Claude Code](https://claude.com/claude-code) | runs the agent + skill | no — install first |
| Figma MCP server | all Figma reads/writes | yes (`claude mcp add`) |
| Xcode + simulators | SwiftUI verification loop | no — macOS/App Store |
| A browser / dev server | React verification loop | no |
| UI/UX Pro Max skill | layout quality (recommended) | no — optional |

### Agentic install

Or let your agent do it — paste this into Claude Code:

```text
Install Vibe2Fig: run
`curl -fsSL https://raw.githubusercontent.com/CodyChuGit/Vibe2Fig/main/install.sh | bash`,
then verify the `vibe2fig` skill is available and the Figma MCP server is
connected (add it with
`claude mcp add --transport http figma https://mcp.figma.com/mcp` if not).
If Pillow is missing, `pip install pillow`. Finish by telling me the repo
path and confirming the skill triggers on "turn this app into a Figma file".
```

### Manual install

```bash
git clone https://github.com/CodyChuGit/Vibe2Fig.git && cd Vibe2Fig
pip install pillow
claude mcp add --transport http figma https://mcp.figma.com/mcp
mkdir -p ~/.claude/skills && ln -s "$(pwd)/vibe2fig_skill" ~/.claude/skills/vibe2fig
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

**Recommended companion:** install the **UI/UX Pro Max** skill alongside —
Vibe2Fig supplies correctness (measured geometry, componentization, code
truth); UI/UX Pro Max supplies the layout craft (page composition, type,
color systems). The Vibe2Fig skill invokes it automatically for page-design
decisions when present, and falls back to its built-in page grammar when not.

## Quickstart (first build)

1. `cp projects/example/config.example.json projects/<app>/config.json` and
   fill it in (bundle id, **save path read from the persistence code**,
   device table).
2. Extract tokens — SwiftUI: `python3 adapters/swiftui/extract_tokens.py …`;
   React: tokens from Tailwind config / CSS variables (see
   `adapters/react/README.md`).
3. Write layout digests per [core/spec_schema.md](core/spec_schema.md)
   (LLM pass over source — reviewable, diffable YAML).
4. Ground truth: seed a deterministic app state, then capture it —
   SwiftUI: `python3 tools/capture.py --config projects/<app>/config.json --app <.app> --seed <save> --state home --out projects/<app>/captures/`;
   React: screenshot the seeded routes in a browser at the target viewports.
   Either way, finish with `python3 tools/measure.py projects/<app>/captures/*.png`.
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

- **v1 (now)**: SwiftUI → Figma proven end-to-end; render-verified,
  incremental updates via the ledger.
- **v1.5**: React adapter to parity — tokens from Tailwind/CSS vars, digests
  from JSX, browser captures as ground truth; same spec IR and runtime.
- **v2**: Figma → code sync — diff `get_metadata` against specs, map nodes to
  source via Code Connect anchors, emit minimal source patches. The ledger +
  measured geometry make the diff tractable.

## License

MIT — see [LICENSE](LICENSE).
