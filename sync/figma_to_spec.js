// figma_to_spec.js — Plugin-API walker: Figma frame -> spec IR (v2 sync).
// Embedded by sync/extract_chunk.py, which prepends `const MAPS = {...}`:
//   MAPS.tokensById  { variableId: tokenName }
//   MAPS.assetsByHash{ imageHash:  assetName }
//   MAPS.compsById   { componentId: compKey }  (variant ids AND set ids)
// The driver appended by the assembler calls extractFrame(frame) per frame
// in the PRODUCTION SCREENS section and returns the array.

function r1(v){ return Math.round(v*10)/10; }

function tokenOf(paints){
  if(!paints || !paints.length) return null;
  const p = paints[0];
  if(p.type==='SOLID'){
    const bv = p.boundVariables && p.boundVariables.color;
    if(bv && MAPS.tokensById[bv.id]) {
      return p.opacity!==undefined && p.opacity<1
        ? {token: MAPS.tokensById[bv.id], opacity: r1(p.opacity*100)/100}
        : MAPS.tokensById[bv.id];
    }
    const c=p.color;
    const rgb=[r1(c.r*1000)/100, r1(c.g*1000)/100, r1(c.b*1000)/100]
      .map(v=>Math.round(v*100)/100);
    return p.opacity!==undefined && p.opacity<1 ? {rgb, opacity:r1(p.opacity*100)/100} : {rgb};
  }
  if(p.type==='IMAGE') return {imageHash:p.imageHash};
  return {paint:p.type};
}

function base(n){
  const o={name:n.name, w:r1(n.width), h:r1(n.height)};
  if(n.visible===false) o.hidden=true;
  if(n.opacity!==undefined && n.opacity<1) o.opacity=r1(n.opacity*100)/100;
  return o;
}

function extractNode(n){
  let o;
  if(n.type==='TEXT'){
    o=Object.assign({t:'text', s:n.characters, pt:n.fontSize,
      family:(n.fontName&&n.fontName.family)||'mixed'}, base(n));
    const fill=tokenOf(n.fills); if(fill) o.color=fill;
    if(n.textAlignHorizontal && n.textAlignHorizontal!=='LEFT') o.align=n.textAlignHorizontal.toLowerCase();
  } else if(n.type==='INSTANCE'){
    const mc=n.mainComponent;
    const key=(mc && (MAPS.compsById[mc.id] ||
      (mc.parent && MAPS.compsById[mc.parent.id] && MAPS.compsById[mc.parent.id]+'/'+mc.name))) ||
      (mc && mc.name) || 'unknown';
    o=Object.assign({t:'instance', comp:key}, base(n));
    const texts=n.findAll(k=>k.type==='TEXT');
    if(texts.length){ o.text={}; for(const t of texts) o.text[t.name]=t.characters; }
  } else if(n.type==='RECTANGLE'){
    const fill=tokenOf(n.fills);
    if(fill && fill.imageHash){
      o=Object.assign({t:'img', asset:MAPS.assetsByHash[fill.imageHash]||fill.imageHash}, base(n));
    } else {
      o=Object.assign({t:'rect'}, base(n));
      if(fill) o.fill=fill;
      if(n.cornerRadius) o.radius=r1(n.cornerRadius);
      const st=tokenOf(n.strokes); if(st) o.stroke=st;
    }
  } else if(n.type==='ELLIPSE'){
    o=Object.assign({t:'circle', d:r1(n.width)}, base(n));
    const fill=tokenOf(n.fills); if(fill) o.fill=fill;
  } else if(n.type==='FRAME'||n.type==='GROUP'||n.type==='COMPONENT'){
    if(n.layoutMode && n.layoutMode!=='NONE'){
      o=Object.assign({t:'stack', dir:n.layoutMode==='VERTICAL'?'v':'h',
        spacing:r1(n.itemSpacing)}, base(n));
      const pad=[n.paddingTop,n.paddingRight,n.paddingBottom,n.paddingLeft].map(r1);
      if(pad.some(v=>v)) o.pad=pad;
      if(n.primaryAxisAlignItems && n.primaryAxisAlignItems!=='MIN') o.justify=n.primaryAxisAlignItems.toLowerCase();
      if(n.counterAxisAlignItems && n.counterAxisAlignItems!=='MIN') o.align=n.counterAxisAlignItems.toLowerCase();
      const fill=tokenOf(n.fills); if(fill) o.fill=fill;
      o.children=n.children.map(extractNode);
    } else {
      o=Object.assign({t:'z'}, base(n));
      const fill=tokenOf(n.fills); if(fill) o.fill=fill;
      if(n.clipsContent) o.clip=true;
      o.children=n.children.map(c=>{
        const e=extractNode(c); e.abs={x:r1(c.x), y:r1(c.y)}; return e;
      });
    }
  } else {
    o=Object.assign({t:'node', type:n.type}, base(n));
  }
  return o;
}

function extractFrame(f){
  return {
    name:f.name, w:r1(f.width), h:r1(f.height),
    cornerRadius:r1(f.cornerRadius||0),
    root:{t:'z', name:'root', w:r1(f.width), h:r1(f.height),
      children:f.children.map(c=>{
        const e=extractNode(c); e.abs={x:r1(c.x), y:r1(c.y)}; return e;
      })}
  };
}
