# React adapter (v1.5 plan)

Same pipeline, different front end. Everything downstream of the spec IR
(runtime.js, upload.py, state ledger, error-correcting loop) is shared.

## Token extraction

| source | approach |
|---|---|
| Tailwind config | read `theme.colors/spacing/borderRadius/fontFamily` → tokens.json |
| CSS custom properties | parse `:root {--*}` from the built CSS |
| styled-components/emotion themes | evaluate the theme module in Node |
| Tokens Studio file | consume directly (already the interop format) |

`extract_tokens.py` gains a `--framework react` mode; output schema unchanged.

## Layout digests

Two complementary paths:

1. **LLM digest of JSX** (same contract as SwiftUI, `core/spec_schema.md`):
   resolve component trees, Tailwind classes → concrete px values at a chosen
   breakpoint, pin representative props/state. Works without running the app.
2. **Live capture cross-check**: for running apps, Figma's
   `generate_figma_design` captures the rendered page pixel-perfectly; use it
   as the verification baseline for the digest-built editable frames (capture
   as reference, delete after comparison — the editable spec-built frames are
   the deliverable).

## Components

React components map 1:1 to Figma component sets: props with finite unions
(variant/size/state) become variant axes; `children`/text props become text
overrides; icon props become INSTANCE_SWAP. `react-figma` (OSS) can render
Storybook stories straight into Figma and is a candidate backend where a
Storybook already exists — otherwise the spec IR path builds them.

## Why not pure static analysis

JSX + CSS-in-JS + runtime breakpoints make full static resolution undecidable
in general. The digest contract embraces that: an LLM (or a human) resolves a
*specific viewport + state* into a reviewable YAML file, and the generator is
deterministic from there. Diffable, correctable, versioned.
