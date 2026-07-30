# SwiftUI adapter

## Tokens

`extract_tokens.py <repo>` parses the design-system constants out of Swift
source (Color(red:green:blue:) statics, radius scalars, type-color switches,
font family names) into `tokens.json`. Currently pointed at the app's
`PixelKit.swift`/`Typography.swift`; the parse patterns are generic — new
projects supply their own file map.

## Font mapping caveat

SwiftUI apps often bundle fonts Figma doesn't have. Encode the app's *own*
fallback chain: the app's Typography.swift declares Jersey 15 as the
fallback for its a bundled pixel font band, so the Figma file uses Jersey 15
there — a decision the code itself documents. Always replicate any size
transformation (here: `bumped()`) before family selection; the raw call site
size is not what renders.

## Layout digests

Produced by an LLM pass over the screen source files with the digest contract
(`core/spec_schema.md`). Rules that made the the app digests accurate:

- Resolve for ONE concrete device/viewport (46mm, 208×248) — evaluate
  GeometryReader math, WatchMetrics tiers, heroScale multipliers to numbers.
- Apply font-size transforms before family selection; record both raw + rendered.
- Pin conditionals to a representative default state; list the other states at
  the end as "variants worth frames".
- Record literal strings, or representative runtime values ("Lv 1 · Hero").
- Flag code-vs-docs conflicts and resolve them in favor of code.
- SwiftUI idioms → IR idioms: Spacer → spacer node, ZStack → z node with
  offsets, overlay strokes → stroke + inner-stroke overlay, safe-area behavior
  → rootY placement, `SpriteAnimationView` → z+img bottom-aligned box.
