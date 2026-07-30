// Figma Plugin API interpreter for FigmaExport screen specs.
// Injected at the top of every generated use_figma chunk by generate_figma.py,
// followed by `const STATE = {...}; const SPEC = {...}; return await run(SPEC, STATE);`
//
// STATE: { variables: {token: variableId}, assets: {key: imageHash},
//          components: {name: componentId}, styles: {px: styleId} }
// SPEC:  { name, w, h, root } — node tree, see node types in build().
//
// Font mapping mirrors AppSources/Typography.swift exactly:
// bumped(raw): <11→12, <12→13, <28→raw+2, else raw. Family by bumped size:
// <20 → a bundled pixel font (unavailable in Figma; its declared fallback Jersey 15
// is used), <28 → Jersey 20, ≥28 → Jersey 25. (Jersey 10 is unreachable: the
// bump floor is 12 and the <12 band never fires.)

function bumped(raw) {
  if (raw < 11) return 12;
  if (raw < 12) return 13;
  if (raw < 28) return raw + 2;
  return raw;
}
function familyFor(size) {
  if (size < 20) return "Jersey 15";
  if (size < 28) return "Jersey 20";
  return "Jersey 25";
}

async function preloadFonts() {
  for (const f of ["Jersey 15", "Jersey 20", "Jersey 25"]) {
    await figma.loadFontAsync({ family: f, style: "Regular" });
  }
}

function solid(rgb, opacity) {
  const p = { type: "SOLID", color: { r: rgb[0], g: rgb[1], b: rgb[2] } };
  if (opacity !== undefined) p.opacity = opacity;
  return p;
}

// A fill spec is a token name ("panel"), {token, opacity}, {rgb:[r,g,b], opacity},
// or {asset: key, scale?: "FILL"|"FIT"} for image fills.
function makePaint(spec, STATE) {
  if (typeof spec === "string") spec = { token: spec };
  if (spec.asset) {
    const hash = STATE.assets[spec.asset];
    if (!hash) throw new Error("unknown asset: " + spec.asset);
    return { type: "IMAGE", imageHash: hash, scaleMode: spec.scale || "FIT" };
  }
  if (spec.token) {
    const id = STATE.variables[spec.token];
    if (!id) throw new Error("unknown color token: " + spec.token);
    let paint = solid([0, 0, 0], spec.opacity);
    paint = figma.variables.setBoundVariableForPaint(paint, "color", { id });
    return paint;
  }
  return solid(spec.rgb, spec.opacity);
}

function applySize(node, spec) {
  // numbers = fixed; "fill" = FILL (needs auto-layout parent, set after append);
  // undefined = hug/auto.
  const w = typeof spec.w === "number" ? spec.w : node.width;
  const h = typeof spec.h === "number" ? spec.h : node.height;
  if (typeof spec.w === "number" || typeof spec.h === "number") node.resize(w, h);
}

function applyCommon(node, spec, STATE) {
  if (spec.name) node.name = spec.name;
  if (spec.fill !== undefined) node.fills = [makePaint(spec.fill, STATE)];
  if (spec.opacity !== undefined) node.opacity = spec.opacity;
  if (spec.radius !== undefined) {
    node.cornerRadius = spec.radius;
    // SwiftUI RoundedRectangle(style: .continuous) — Apple squircle profile
    if ("cornerSmoothing" in node) node.cornerSmoothing = 0.6;
  }
  if (spec.rotation !== undefined) node.rotation = spec.rotation;
  if (spec.blur) node.effects = [{ type: "LAYER_BLUR", radius: spec.blur, visible: true }];
  if (spec.stroke) {
    const s = spec.stroke;
    node.strokes = [makePaint(s.color, STATE)];
    node.strokeWeight = s.weight ?? 1;
    node.strokeAlign = s.align || "INSIDE";
  }
}

// Inner strokes beyond the first (e.g. PixelPanel's dim line inset 2) become
// absolute overlay rects so a single node can carry both.
function addInnerStrokeOverlay(parent, s, STATE) {
  const r = figma.createRectangle();
  r.name = "inner-stroke";
  r.fills = [];
  r.strokes = [makePaint(s.color, STATE)];
  r.strokeWeight = s.weight ?? 1;
  r.strokeAlign = "INSIDE";
  r.cornerRadius = s.radius ?? 6;
    if ("cornerSmoothing" in r) r.cornerSmoothing = 0.6;
  parent.appendChild(r);
  const inset = s.inset ?? 2;
  if ("layoutPositioning" in r && parent.layoutMode && parent.layoutMode !== "NONE") {
    r.layoutPositioning = "ABSOLUTE";
  }
  r.x = inset; r.y = inset;
  r.resize(Math.max(1, parent.width - 2 * inset), Math.max(1, parent.height - 2 * inset));
  r.constraints = { horizontal: "STRETCH", vertical: "STRETCH" };
  return r;
}

async function build(spec, parent, STATE) {
  const t = spec.t;
  let node;

  if (t === "stack") {
    node = figma.createAutoLayout(spec.dir === "h" ? "HORIZONTAL" : "VERTICAL");
    if (spec.spacing !== undefined) node.itemSpacing = spec.spacing;
    if (spec.pad !== undefined) {
      const p = Array.isArray(spec.pad) ? spec.pad : [spec.pad, spec.pad, spec.pad, spec.pad];
      node.paddingTop = p[0]; node.paddingRight = p[1];
      node.paddingBottom = p[2]; node.paddingLeft = p[3];
    }
    // cross-axis alignment: counterAxisAlignItems MIN/CENTER/MAX
    node.counterAxisAlignItems = { start: "MIN", center: "CENTER", end: "MAX" }[spec.align || "center"];
    node.primaryAxisAlignItems = { start: "MIN", center: "CENTER", end: "MAX", between: "SPACE_BETWEEN" }[spec.justify || "start"];
    node.fills = [];
    applyCommon(node, spec, STATE);
    parent.appendChild(node);
    for (const c of spec.children || []) await build(c, node, STATE);
  } else if (t === "z") {
    node = figma.createFrame();
    node.fills = [];
    node.resize(spec.w || 100, spec.h || 100);
    applyCommon(node, spec, STATE);
    node.clipsContent = spec.clip !== false;
    parent.appendChild(node);
    for (const c of spec.children || []) {
      const child = await build(c, node, STATE);
      // position: abs {x,y} top-left, or centered by default
      if (c.abs) { child.x = c.abs.x; child.y = c.abs.y; }
      else {
        child.x = Math.round((node.width - child.width) / 2 + (c.dx || 0));
        child.y = Math.round((node.height - child.height) / 2 + (c.dy || 0));
      }
    }
  } else if (t === "text") {
    node = figma.createText();
    const size = bumped(spec.px);
    const family = spec.family || familyFor(size);
    await figma.loadFontAsync({ family, style: "Regular" });
    node.fontName = { family, style: "Regular" };
    node.fontSize = size;
    node.characters = spec.s;
    node.textAlignHorizontal = (spec.align || "center").toUpperCase();
    node.fills = [makePaint(spec.color || "text", STATE)];
    if (spec.maxW) { node.textAutoResize = "HEIGHT"; node.resize(spec.maxW, node.height); }
    if (spec.name) node.name = spec.name; else node.name = spec.s.slice(0, 40);
    if (spec.opacity !== undefined) node.opacity = spec.opacity;
    parent.appendChild(node);
  } else if (t === "rect") {
    node = figma.createRectangle();
    node.resize(spec.w || 10, spec.h || 10);
    node.fills = [];
    applyCommon(node, spec, STATE);
    parent.appendChild(node);
  } else if (t === "circle") {
    node = figma.createEllipse();
    node.resize(spec.d || 10, spec.d || 10);
    node.fills = [];
    applyCommon(node, spec, STATE);
    parent.appendChild(node);
  } else if (t === "img") {
    node = figma.createRectangle();
    node.resize(spec.w, spec.h);
    node.fills = [makePaint({ asset: spec.asset, scale: spec.scale }, STATE)];
    node.name = spec.name || spec.asset;
    if (spec.opacity !== undefined) node.opacity = spec.opacity;
    parent.appendChild(node);
  } else if (t === "spacer") {
    node = figma.createFrame();
    node.fills = [];
    node.resize(1, 1);
    node.name = "Spacer";
    parent.appendChild(node);
    node.layoutGrow = 1;
  } else if (t === "instance") {
    const compId = STATE.components[spec.comp];
    if (!compId) throw new Error("unknown component: " + spec.comp);
    const comp = await figma.getNodeByIdAsync(compId);
    node = comp.createInstance();
    parent.appendChild(node);
    if (spec.overrides) {
      for (const [childName, chars] of Object.entries(spec.overrides)) {
        const txt = node.findOne(n => n.type === "TEXT" && n.name === childName);
        if (txt) {
          await figma.loadFontAsync(txt.fontName);
          txt.characters = chars;
        }
      }
    }
    if (spec.name) node.name = spec.name;
  } else if (t === "panel") {
    // PixelPanel: rounded panel fill, cream outer stroke 2, dim inner line inset 2
    node = figma.createAutoLayout(spec.dir === "h" ? "HORIZONTAL" : "VERTICAL");
    node.itemSpacing = spec.spacing ?? 4;
    const p = spec.pad ?? 8;
    const pa = Array.isArray(p) ? p : [p, p, p, p];
    node.paddingTop = pa[0]; node.paddingRight = pa[1]; node.paddingBottom = pa[2]; node.paddingLeft = pa[3];
    node.counterAxisAlignItems = "CENTER";
    node.cornerRadius = 8;
    if ("cornerSmoothing" in node) node.cornerSmoothing = 0.6;
    node.fills = [makePaint(spec.fill || "panel", STATE)];
    node.strokes = [makePaint("border", STATE)];
    node.strokeWeight = 2;
    node.strokeAlign = "INSIDE";
    node.name = spec.name || "PixelPanel";
    parent.appendChild(node);
    for (const c of spec.children || []) await build(c, node, STATE);
    addInnerStrokeOverlay(node, { color: "borderDim", weight: 1, inset: 2, radius: 6 }, STATE);
  } else if (t === "button") {
    // PixelButtonStyle: panel (or tint if prominent) fill, tint/cream 2pt outer
    // stroke, dim 1pt inner line, label centered, minHeight 40 (24 small)
    const minH = spec.minH ?? 40;
    node = figma.createAutoLayout("HORIZONTAL");
    node.itemSpacing = 4;
    node.counterAxisAlignItems = "CENTER";
    node.primaryAxisAlignItems = "CENTER";
    node.cornerRadius = 8;
    if ("cornerSmoothing" in node) node.cornerSmoothing = 0.6;
    const tint = spec.tint || "text";
    node.fills = [makePaint(spec.prominent ? tint : "panel", STATE)];
    node.strokes = [makePaint(spec.border || (spec.prominent ? tint : "border"), STATE)];
    node.strokeWeight = 2;
    node.strokeAlign = "INSIDE";
    node.name = spec.name || ("Button/" + spec.label);
    parent.appendChild(node);
    if (spec.cursor) {
      await build({ t: "text", s: "▶", px: 8, color: "cursor", name: "cursor" }, node, STATE);
    }
    const labelColor = spec.prominent ? "panelDeep" : tint;
    await build({ t: "text", s: spec.label, px: minH < 34 ? 12 : 14, color: labelColor, name: "label" }, node, STATE);
    addInnerStrokeOverlay(node, {
      color: spec.prominent ? { token: spec.tint || "text", opacity: 0.4 } : "borderDim",
      weight: 1, inset: 2, radius: 6,
    }, STATE);
    // sizing: buttons stretch to fill their column and honor minHeight
    if (spec.w) node.resize(spec.w, Math.max(minH, node.height));
    else { node.minHeight = minH; }
  } else if (t === "bar") {
    // PixelBar: N segments, 6pt tall, 1.5 gap, radius 1.5, empty = panelDeep
    const segs = spec.segments ?? 10;
    node = figma.createAutoLayout("HORIZONTAL");
    node.itemSpacing = 1.5;
    node.fills = [];
    node.name = spec.name || ("PixelBar/" + spec.tint);
    parent.appendChild(node);
    for (let i = 0; i < segs; i++) {
      const seg = figma.createRectangle();
      seg.resize(spec.segW || 10, 6);
      seg.cornerRadius = 1.5;
      seg.fills = [makePaint(i < spec.filled ? spec.tint : "panelDeep", STATE)];
      seg.name = "seg" + i;
      node.appendChild(seg);
    }
  } else {
    throw new Error("unknown node type: " + t);
  }

  // FILL sizing must run after the node is parented into an auto-layout frame
  if (parent.layoutMode && parent.layoutMode !== "NONE") {
    if (spec.w === "fill") node.layoutSizingHorizontal = "FILL";
    if (spec.h === "fill") node.layoutSizingVertical = "FILL";
  }
  if (typeof spec.w === "number" || typeof spec.h === "number") applySize(node, spec);
  return node;
}

// Builds one screen frame (208×248, bg fill, corner radius 52) from SPEC.
async function run(SPEC, STATE) {
  await preloadFonts();
  const frame = figma.createFrame();
  frame.name = SPEC.name;
  frame.resize(SPEC.w || 208, SPEC.h || 248);
  frame.cornerRadius = SPEC.cornerRadius ?? 52;
  frame.cornerSmoothing = 0.6; // watch display corners are continuous, not circular
  frame.clipsContent = true;
  frame.fills = [makePaint(SPEC.bg || "bg", STATE)];
  figma.currentPage.appendChild(frame);
  if (SPEC.x !== undefined) frame.x = SPEC.x;
  if (SPEC.y !== undefined) frame.y = SPEC.y;

  const root = await build(SPEC.root, frame, STATE);
  // screen roots default to filling the frame, centered
  if (SPEC.rootLayout !== "manual") {
    root.x = Math.round((frame.width - root.width) / 2);
    root.y = SPEC.rootY !== undefined ? SPEC.rootY : Math.round((frame.height - root.height) / 2);
    if (SPEC.dy) root.y += SPEC.dy; // measured safe-area correction (sim ground truth)
  }
  return { frameId: frame.id, name: SPEC.name };
}
