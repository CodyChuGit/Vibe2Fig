---
name: vibe2fig
description: Reverse-engineer a real codebase into a componentized, simulator-verified Figma file, or incrementally update one. Use when the user wants an app turned into Figma, a Figma clone kept in sync with code, new screens/sizes/assets added to an existing Vibe2Fig project, or code-truth audits of Figma content. Code supplies the numbers, seeded simulators supply rendered truth, the state.json ledger supplies memory.
---

# Vibe2Fig — code → Figma, verified

Workflow with **phase gates**. Each phase ends with an artifact on disk and a
verification step. First build runs 0→5; updates enter at Phase 5's diff.
Repo: `~/code2figma` (github.com/CodyChuGit/Vibe2Fig). Read
`docs/SKILL_ANALYSIS.md` for the rationale, `docs/GOTCHAS.md` before any
`use_figma` or simulator work.

## Hard rules (learned, non-negotiable)

1. **Derive from code, place from pixels.** Constants come from source; final
   exhibit coordinates come from measured captures. Where they disagree,
   pixels win and the delta gets annotated.
2. **Nothing raw on an exhibit.** Every screen frame is composed of component
   instances; new needs extend existing component sets with variants
   (Size/State/Width axes), never fork one-offs.
3. **Screenshot after every write batch.** API success ≠ visual success. Fix
   smallest-first; if instance overrides fight back, delete and rebuild from
   the master.
4. **Ledger everything.** Ids, prop keys, asset hashes, measured geometry,
   decisions → `projects/<app>/state.json`, same commit as the work.
5. **Never touch the owner's live-save device.** Test sims only; recreate
   wedged sims from device-type + runtime and update config.

## Companion skill — layout quality

For every layout-design decision (page composition, doc chrome, typography,
color tones), **invoke the `ui-ux-pro-max` skill when available** — Vibe2Fig
supplies correctness (measured geometry, componentization, code truth);
ui-ux-pro-max supplies the design quality that makes the file worth
presenting. If it is not installed, recommend it to the user and follow the
Phase 3 grammar strictly as the fallback.

## Phase 0 — Register (once)
`projects/<app>/config.json`: fileKey, bundleId, platform, save path (read it
from the persistence code — do not assume), seeder command + modes, device
table (pt size, radius, UDID — treat UDIDs as disposable), permission grants
needed, page grammar constants (e.g. clock font/anchor).

## Phase 1 — Ground truth
1. Token extract (`adapters/<fw>/extract_tokens.py`) + layout digests per
   `core/spec_schema.md` (LLM pass over source; reviewable YAML).
2. Deterministic seeds via the project seeder — one save file, copied to every
   device, so captures are comparable.
3. Capture: boot/create sim per size → install → inject save at the *code's*
   save path → grant permissions (`simctl privacy` + reboot if a prompt is
   already up) → launch → screenshot.
4. Measure: band/bbox/color-predicate extraction to pt (see
   `tools/measure.py`). Beware trimmed art: glyph bbox ≠ element box; anchor
   rows on symmetric glyphs; use color predicates for bars/meters.

## Phase 2 — Foundations (Figma)
Variables first (explicit scopes), bound to every fill — gate: zero raw fills.
Then atoms → molecules → organisms as component sets with prop axes sized for
the future. Pixel art: pre-scale stills 3× with PIL NEAREST (Figma blurs
upscaled fills; animated GIF fills don't render).

## Phase 3 — Pages
**Invoke `ui-ux-pro-max` first** (see Companion skill) for masthead
composition, section rhythm, tone system, and typography before building.

Grammar: dark canvas, masthead (clone an existing one **and copy
`page.backgrounds` + explicit variable modes** to the new page), tone-kickered
transparent sections, exhibits = bezel-accurate frames + instances at measured
coordinates, captions in designer voice citing code facts, 1pt inside strokes
in the section tone.

## Phase 4 — Verify loop
Per section: `get_screenshot` → compare to captures (eyeball + measure the
export) → fix → re-shoot. Budget ±4 pt. Report code-vs-doc discrepancies to
the user instead of silently "fixing" locked project docs.

## Phase 5 — Ledger, commit, update mode
Persist to `state.json`; commit captures + measurements with the work.
**Update mode** (the common case after v1): diff code (asset manifests, DB
tables, new screens/sizes) against the ledger → build only the delta →
classify new content from the code's own tables → verify → ledger → commit.
After any `upload_assets`, sweep **every page** for auto-placed stray frames —
they land on whatever page the user has open.
