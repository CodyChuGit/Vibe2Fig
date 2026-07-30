# Spec IR schema

A screen spec is `{ name, w, h, cornerRadius?, bg?, x?, y?, rootY?, root }`.
Defaults come from the project config (`projects/<app>/config.json`): device
viewport `w`×`h`, `cornerRadius`, bg token `bg`, root centered.

Node types (interpreted by `core/runtime.js`):

| t | purpose | keys |
|---|---|---|
| `stack` | auto-layout row/column | `dir` "v"/"h", `spacing`, `pad` n or [t,r,b,l], `align` start/center/end (cross-axis), `justify` start/center/end/between, `children`, `fill`, `radius`, `stroke`, `w`/`h` (number/"fill") |
| `z` | fixed frame, absolute children | `w`, `h`, `children` (each child: `abs:{x,y}` or centered with `dx`/`dy`), `clip` |
| `text` | text node | `s`, `px` (RAW SwiftUI size — runtime applies the bump+family mapping), `color` token or `{rgb,opacity}`, `align`, `maxW`, `family` (override) |
| `rect` / `circle` | shapes | `w`,`h`/`d`, `fill`, `radius`, `stroke`, `opacity`, `blur`, `rotation` |
| `img` | image fill rect | `asset` key from state.assets, `w`, `h`, `scale` FILL/FIT, `opacity` |
| `spacer` | layoutGrow filler | — |
| `instance` | component instance | `comp` key from state.components, `overrides` {textNodeName: chars}, `w`/`h` |
| `panel` | project panel chrome | `pad`, `spacing`, `dir`, `children` (fill + outer/inner stroke pattern per project) |
| `button` | project button style | `label`, `tint`, `prominent`, `minH`, `w`, `cursor` (selection glyph), `border` |
| `bar` | segmented meter | `tint`, `filled`, `segments`, `segW` |

Color spec: token name (bound to a Figma variable), `{token, opacity}`, or
`{rgb:[r,g,b], opacity}` for system colors the token set doesn't cover
(.secondary = white@0.6; Apple dark system palette red #FF453A green #30D158
cyan #64D2FF yellow #FFD60A indigo #5E5CE6 purple #BF5AF2 mint #66D4CF).

Sprite idiom (an animated-sprite view of box size S — outer S×S box, art
bottom-aligned at S×naturalScale):

```json
{"t":"z","w":118,"h":118,"children":[
  {"t":"img","asset":"sprite_hero_front","w":59,"h":59,"abs":{"x":29.5,"y":59}}]}
```

## Digest contract (adapter output, YAML)

Per screen: resolved container tree with spacing/padding/alignment, every text
node (string, RAW font call, color token), shapes with token fills/strokes,
buttons with style params, image/sprite refs + sizes, viewport-resolved
GeometryReader math, and a list of state variants worth separate frames.
Conditionals are pinned to a representative default and annotated. Fonts are
annotated as `px(raw) -> rendered pt + family` so both raw and rendered values
survive review.

## System chrome
If the project config's `grammar` defines system chrome (e.g. a status clock:
font, size, anchor), the runtime driver appends it to every screen frame so
exhibits match what the device or browser actually renders in captures.
