# SwiftUI adapter

## Tokens

`extract_tokens.py <app_src_dir> <profile.json> [out.json]` parses the
design-system constants out of Swift source (Color(red:green:blue:) statics,
radius scalars, semantic color switches, font family names) into `tokens.json`.
The parse patterns are generic — each project supplies its own profile
(`tokens.profile.example.json`) pointing at its design-system / typography
files and declaring the font band table, screen, and component metrics a
parser cannot infer.

## Font mapping caveat

SwiftUI apps often bundle fonts Figma doesn't have. Encode the app's *own*
fallback chain: if the typography file declares a fallback family for a
custom font, the Figma file uses that fallback — a decision the code itself
documents. Always replicate any size transformation the app applies (bump
functions, dynamic type mapping) before family selection; the raw call-site
size is not what renders.

## Layout digests

Produced by an LLM pass over the screen source files with the digest contract
(`core/spec_schema.md`). Rules that make digests accurate:

- Resolve for ONE concrete device/viewport (from the project config) —
  evaluate GeometryReader math and any per-device tier/scale helpers down to
  numbers.
- Apply font-size transforms before family selection; record both raw + rendered.
- Pin conditionals to a representative default state; list the other states at
  the end as "variants worth frames".
- Record literal strings, or representative runtime values.
- Flag code-vs-docs conflicts and resolve them in favor of code.
- SwiftUI idioms → IR idioms: Spacer → spacer node, ZStack → z node with
  offsets, overlay strokes → stroke + inner-stroke overlay, safe-area behavior
  → rootY placement, animated sprite views → z+img bottom-aligned box.
