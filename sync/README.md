# Figma → code sync (v2 roadmap)

Goal: designers move things in the generated Figma file; the toolkit turns
those edits into minimal source patches. The spec IR is the pivot — both sides
already speak it.

## Mechanism

1. **Snapshot**: after generation, `state.json` holds frame/node IDs and each
   frame's spec. This is the baseline.
2. **Diff**: `get_metadata` (XML with ids/names/positions/sizes) +
   `use_figma` read scripts re-serialize the live file into spec IR
   (`figma → spec` is mechanical: walk auto-layout frames back into
   stack/text/img nodes, resolve bound variables back to token names).
   Compare against the baseline spec: changed paddings, spacings, sizes,
   colors (variable rebinds), text, added/removed nodes.
3. **Map to source**: each spec node carries a `src` anchor
   (file:line at digest time; Code Connect mappings for components —
   `add_code_connect_map` with label SwiftUI/React ties Figma components to
   `PixelKit.swift` / component files). Diff entries resolve through anchors
   to concrete edit sites.
4. **Patch**: emit the smallest source change per diff class:
   - token value change → edit the constant in PixelKit.swift / tailwind config
   - spacing/padding/size change → edit the literal at the anchor
   - text change → edit the string literal
   - variant/prop change on an instance → edit the call-site arguments
   - structural change (nodes added/reordered) → flagged for human review with
     the spec diff attached (not auto-patched in v2)
5. **Verify**: rebuild code → re-run the code→Figma pipeline into a scratch
   page → assert the round-trip diff is empty.

## Guardrails

- Never auto-patch structural rewrites; only literal-level edits are automated.
- Every patch cites its Figma node ID + spec path + source anchor.
- Round-trip verification is mandatory before the patch is committed.

## Prereqs to build

- [ ] `figma_to_spec.js` (read-back serializer; inverse of runtime.js)
- [ ] spec differ (`core/spec_diff.py`)
- [ ] `src` anchors added to digest/spec contract
- [ ] Code Connect mappings emitted during component generation
