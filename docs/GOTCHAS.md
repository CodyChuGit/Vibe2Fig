# Gotchas — hard-won, session-tested

Read before any `use_figma` or simulator work. Every entry cost real time.

## Figma Plugin API (via use_figma)

- **Failed scripts are atomic.** An error means nothing ran — fix the script,
  don't "clean up" phantom state, don't retry verbatim.
- `COMPONENT_SET` has no `createInstance` — use
  `set.defaultVariant.createInstance()`; write a `mk()` helper that handles
  both node types.
- `createComponentFromNode` **invalidates the node reference** — capture
  name/props before converting.
- **Instance children have locked positions** (`set_y: cannot be overridden`).
  Text width resizes inside instances are risky too. If overrides fight back,
  delete the instance and rebuild from the master with fresh props.
- **Reparenting into a SECTION re-interprets x/y as section-relative.** Set
  coordinates *after* `appendChild`, not before. Sections auto-grow to fit
  children; resize explicitly after layout.
- **New pages inherit nothing**: copy `page.backgrounds` and explicit variable
  modes from a sibling page, or dark-canvas designs render white-on-white.
- `upload_assets` auto-places uploaded frames **on whatever page the user has
  open** (response `nodeId` may be null). After uploads, sweep every page for
  stray frames named after the files and remove them.
- `rescale()` scales children's positions too; auto-layout SPACE_BETWEEN and
  padding interact unpredictably after child rescales — for exact geometry,
  switch the container to `layoutMode='NONE'` and place children at measured
  coordinates.
- **Animated GIF image fills don't render** in frames — convert to still PNG.
- **Figma blurs upscaled image fills** — pre-scale pixel art 3× with PIL
  `Image.NEAREST` and place at natural size.
- Variant prop hygiene: when adding an axis (e.g. `Width=70`) to some members
  of a set, add the default value to the existing members' names too, or the
  set shows property warnings.
- Fonts: load before *any* text mutation (`getStyledTextSegments(['fontName'])`
  for existing text). "Inter Semi Bold", not "SemiBold".

## Apple simulators (iOS / watchOS / tvOS)

- **Find the save path in the persistence code** — never assume. (Apps
  commonly write `Library/Application Support/…`, not `Documents/`; seeding
  the wrong dir fails silently and the app resumes its old save.)
- **Permission prompts block fresh sims** (e.g. location). `simctl privacy
  <udid> grant <service> <bundleId>` does not dismiss an already-showing
  prompt — grant, then **shutdown + boot**, then relaunch.
- **Sims are cattle.** They lose disk data ("cannot be located on disk") and
  wedge on boot. Recreate via `simctl create <name> <device-type> <runtime>`,
  write the new UDID back to config/docs. Doc'd UDID tables rot.
- First boot of a fresh sim is slow — `simctl bootstatus` before installing;
  a screenshot during boot returns the spinner, not your app.
- Deterministic seeds: generate the save **once** on the host (driving the
  real app-state code), copy the identical file to every sim — captures stay
  comparable across sizes.
- Never touch the owner's live-save simulator; test devices only.

## Measurement (pixel → pt)

- Screenshots are @2× — halve to pt. Verify the px size against the device
  table before trusting anything.
- **Glyph bbox ≠ element box**: sprite art is trimmed inside its canvas, thin
  glyphs (swords, slashes) have off-center bboxes. Anchor row geometry on
  symmetric glyphs (first/last icons), model the rest as evenly spaced cells.
- Use **color predicates** (red/green/cyan dominance) to isolate bars from
  overlapping text; plain luminance bands bleed between neighbors.
- A bbox spanning two visual elements is contamination, not data — tighten
  the band (e.g. `[barTop-16, barTop-1]` for the label above a bar).
- Natural sprite scale comes from the **trimmed animated GIF**, not the still
  canvas (a trimmed frame can measure ≈0.75 of the box where the still reads
  0.5). Back it out from a verified frame: `art / box`.

## Process

- zsh: unquoted `$VAR` does not word-split — use `${=VAR}`. `===` at the start
  of a word triggers `=cmd` expansion — quote it.
- Verify visually after every write batch; API success ≠ visual success.
- When measured reality contradicts locked project docs, **report it, don't
  edit the locked doc** (e.g. a device the docs list in the large tier actually
  renders the compact layout).
