# Vibe2Fig — Skill Analysis: reproducing the pilot outcome

*Written 2026-07-30, immediately after the pilot build (a watchOS SwiftUI
app) reached its "portfolio-grade" state. This is the postmortem that turns a one-off great
session into a repeatable skill.*

---

## 1. What the outcome actually was

The pilot Figma file ended as:

- **7 pages** with a consistent editorial grammar (Cover, Foundations &
  Components, Screens, User Flow, Doc Kit, Asset Library, Screen Sizes).
- **A real design system**: 2 variable collections (app palette + Doc
  chrome), 111+ component masters in atomic tiers, advanced component sets
  with variants (PixelButton ×7, StatBar with Style/Width axes, ActionRing
  with per-watch Size variants, Watch/Bezel ×5, StatusCluster regular/tiny).
- **45 screen states**, every screen a composition of component instances —
  zero raw rectangles on exhibit frames.
- **Five watch sizes** rendered from *measured* simulator ground truth, not
  scaled artwork — including a spec discovery (a device rendering the compact
  tier) that the project's own locked docs had missed.
- **A live-updatable asset library**: when the app's content tables gained 26
  new entries, the update was a 20-minute mechanical diff, not a rebuild.
- Copy that matches app-code logic exactly, then rewritten in designer voice.

The quality came from a *loop*, not from any single generation step. That loop
is what the skill has to encode.

## 2. The six load-bearing practices (with evidence)

### 2.1 Code is the gold standard — but the simulator is the referee
Every number traced to source (the app's metrics, content-database, and
screen-dimension files), yet source alone was never trusted for *rendered*
geometry. The winning pattern:

> constants from code → build → **seeded simulator capture** → **programmatic
> pixel measurement** → build *from the measurements* → verify again.

Evidence: the five-size page. Deriving ring padding from code produced wrong
positions (SwiftUI's SPACE_BETWEEN/padding interplay); measuring icon cluster
centers from screenshots produced exact ones. The measurement pass also caught
a real spec error in the repo's locked docs (a device sitting in the compact
tier, not the large one).
**Rule: derive from code, place from pixels, annotate the difference.**

### 2.2 Seeded saves make ground truth cheap
`swift run seeder <dir> <mode>` produced identical save files for every
simulator, so all five sizes showed the *same* app state and screenshots were
directly comparable. Without deterministic saves, per-size captures would have
been apples-to-oranges. The seeder is ~30 lines because it drives the real
app store/state object — the skill should demand a seeder per project, not
screenshots of whatever state the app happens to be in.

### 2.3 The ledger (`state.json`) is the skill's memory
Every page, section, component, variant, variable, prop key, and asset hash is
recorded. This is what made "update the assets with the new content entries"
a *diff* operation: manifest ∪ content tables vs ledger → 26 new assets →
targeted patch. No re-inventory, no re-reading the whole file. A session
without the ledger re-pays discovery cost every time; a session with it is
incremental forever.

### 2.4 Componentize before composing — and extend sets, never fork
When a new need appeared (five watch sizes), the answer was new *variants on
existing sets* (ActionRing Size=40/42/44/49, StatusCluster Size=tiny, StatBar
Width=70) plus one new atom set (Watch/Bezel). Exhibits then became pure
instance compositions. This kept the 45-state gallery and the sizes page in
lockstep automatically. The anti-pattern (one-off groups per exhibit) is what
makes Figma files rot.

### 2.5 A documentation design system for the documentation
The Doc kit (Doc variables, SectionHeader/Label/StepChip/AnnotationCard/
TierCard with text props, tone-kickered transparent sections, masthead
grammar) meant every new page inherited "award-winning" layout for free. The
sizes page and the asset-library update both reused it wholesale — masthead
cloned, props set, done. Chrome consistency is a *system*, not taste applied
per page.

### 2.6 Verify visually after every write batch
`get_screenshot` after each section build caught: invisible white-on-white
masthead (page background/mode mismatch), transparent bezel fills, clipped
card copy, under-sized sprites (wrong naturalScale), wrong bar dot density.
None of these produce API errors — only eyes catch them. The loop was
screenshot → diagnose → *smallest* fix → re-screenshot, and when instance
internals fought back (locked child y), the correct move was delete-and-
rebuild from the master, not fight the override system.

## 3. Gap analysis — where the intelligence currently lives

| Capability | In the repo today | Where it actually lived this session |
|---|---|---|
| Token extraction | `adapters/swiftui/extract_tokens.py` | repo ✅ |
| Layout digests | contract in `spec_schema.md` | LLM session (by design) |
| Spec → Figma build | `core/runtime.js` | repo ✅ |
| Seeded sim capture | — | ad-hoc bash in session |
| Pixel measurement | — | ad-hoc `measure_sizes.py` in scratchpad |
| Figma API survival patterns | — | session memory (hard-won) |
| Asset pipeline (still + 3× NEAREST + upload + sweep) | partial (`upload.py`) | mostly session |
| Ledger schema & update-mode playbook | implicit in `state.json` | session convention |
| Page grammar (masthead/kicker/section) | — | session convention |

**The core risk: everything in the right-hand column dies with the session.**
The skill's job is to move it left.

## 4. Skill design — how to make the skill match the outcome

The skill is a *workflow with phase gates*, not a generator. Each phase ends
with an artifact on disk and a verification step; no phase may be skipped on a
first build, and update-mode enters at Phase 5.

### Phase 0 — Register (once per project)
Write `projects/<app>/config.json`:
```json
{
  "platform": "watchos | ios | web",
  "fileKey": "…", "bundleId": "…",
  "savePath": "Library/Application Support/<file>",
  "seeder": "path + modes",
  "devices": {"40mm": {"pt": [162,197], "radius": 28, "udid": "…"}, "...": {}},
  "grammar": {"clock": "Inter Semi Bold 20, right-edge W-16"},
  "permissions": ["location"]
}
```
The session lost 30+ minutes to three findable facts (save path, permission
prompt, dead UDIDs). Config makes them one-time costs. UDIDs are *cattle*: the
skill must recreate sims from device-type + runtime when boot fails, and write
the new UDIDs back.

### Phase 1 — Ground truth
1. Run token extractor + write/refresh digests (LLM pass, per contract).
2. Generate seeds for the canonical states (idle hub, primary flow, detail
   states).
3. `tools/capture.py --sizes all --states <state list>` → boots/creates sims,
   installs, injects save at `savePath`, grants `permissions`, launches,
   screenshots. (This session's exact bash flow, made idempotent.)
4. `tools/measure.py captures/ --out measurements.json` — band/bbox/color-
   predicate extraction to pt. Trimmed-art caveats documented: glyph bbox ≠
   box bounds; use symmetric-glyph anchors for row geometry; color predicates
   for bars; never trust a bbox that spans two visual elements.

### Phase 2 — Foundations
Variables (scoped!), then atoms → molecules → organisms as *component sets
with forward-looking prop axes* (State, Size, Width, Style). Bind every fill;
audit zero raw fills before proceeding (the 141-fill audit was a whole
corrective session that a phase gate would have prevented).

### Phase 3 — Pages
Each page: dark canvas + masthead + tone-kickered transparent sections; every
exhibit = bezel-accurate frame + instances placed at **measured** coordinates;
captions in designer voice citing code facts. New page = clone masthead from
an existing page **and copy `page.backgrounds` + explicit variable modes** —
the invisible-title bug is guaranteed otherwise.

### Phase 4 — Verify (the error-correcting loop)
For every built section: `get_screenshot` → compare against capture (eyeball
+ measure.py on the export for exhibits) → fix → re-shoot. Budget: ±4 pt.
Escalation rule learned the hard way: if an instance override fights back
(locked position, un-overridable property), **delete and rebuild from the
master** — never iterate on a mangled override state.

### Phase 5 — Ledger & update mode
Persist everything created (ids, prop keys, hashes, measured geometry,
decisions with "why") to `state.json`; commit captures + measurements to the
project dir. **Update mode**: diff code (manifests, database tables, new
screens) against the ledger → build only the delta → verify → ledger → commit.
Today's 26-asset update is the template: enumerate, classify from code tables,
generate 3× NEAREST stills, upload, flow into sections, update totals, sweep
strays, ledger, push.

### The gotcha file (`docs/GOTCHAS.md`) — non-negotiable content
Figma: atomic failed scripts (fix, don't retry); `COMPONENT_SET` needs
`defaultVariant.createInstance()`; `createComponentFromNode` invalidates the
node ref; instance children have locked positions; reparenting into a SECTION
re-interprets x/y as section-relative; sections auto-grow; `upload_assets`
auto-places frames on the **user's active page** — sweep every page for
`f_*`/`item_*` strays after upload; rescale() moves children; new pages don't
inherit backgrounds or variable modes; animated GIF fills don't render — use
stills; Figma blurs upscaled fills — pre-scale pixel art with PIL NEAREST.
Simulators: save location from code not assumption; `simctl privacy grant` +
reboot for permission prompts; recreate wedged/deleted sims; never touch the
owner's live-save device.

## 5. Prioritized backlog

| # | Item | Why | Effort |
|---|---|---|---|
| 1 | `skill/SKILL.md` (shipped alongside this doc) | phases + gates, invocable | done |
| 2 | Promote `measure.py` + `capture.py` into `tools/` | kills the largest ad-hoc block | S |
| 3 | `docs/GOTCHAS.md` from §4 | prevents relearning tax | S |
| 4 | `config.json` schema + loader in tools | one-time facts stay one-time | S |
| 5 | Ledger schema doc + validator (`tools/ledger.py check`) | update-mode depends on ledger integrity | M |
| 6 | `runtime.js` helpers: set-safe `mk()`, section flow layout, page-look copier, stray sweep | proven JS patterns, reused 10+ times | M |
| 7 | Update-mode playbook as a runnable checklist | today's asset run, templated | S |
| 8 | v2 sync (Figma → code): `figma_to_spec.js` + spec differ | the original end goal; ledger + measured geometry now make diffing tractable | L |

## 6. The one-sentence version

**Vibe2Fig works when code supplies the numbers, seeded simulators supply the
truth, the ledger supplies the memory, components supply the consistency, and
a screenshot-verify loop closes every write** — the skill's job is to make
each of those a phase gate instead of a heroic session habit.
