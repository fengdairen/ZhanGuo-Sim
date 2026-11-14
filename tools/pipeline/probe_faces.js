// tools/pipeline/probe_faces.js —— 生成"和编辑器一致"的面 + 认领归属，供 Python 探针使用
// 用法：node tools/pipeline/probe_faces.js
'use strict';
const fs = require('fs');
const path = require('path');
const G = require(path.join(__dirname, 'geom.js'));

const ROOT = path.join(__dirname, '..', '..');
const V = path.join(ROOT, 'data', 'map', 'vector');
const load = n => JSON.parse(fs.readFileSync(path.join(V, n), 'utf8'));
const flat = f => { const o = []; for (let i = 0; i + 1 < f.length; i += 2) o.push([f[i], f[i + 1]]); return o; };

const rivers = load('rivers_w.json').map(r => flat(r.slice(1)));
const coasts = load('coast_drawn.json').map(c => flat(c.pts));
const lakes = load('lakes_drawn.json').map(l => flat(l.pts));
const b = JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'map', 'borders.json'), 'utf8'));
const edges = (b.edges || []).map(e => e.pts);

// 1) 面（与编辑器 computeFaces 一致：全部水系 + 边界线，minArea 300）
const res = G.build(edges.concat(rivers, coasts, lakes), { minArea: 300 });
let faces = res.faces.map((f, i) => ({ id: 'F' + (i + 1), ring: f.ring, area: f.area, outer: !!f.outer, holes: [] }));
faces.sort((x, y) => y.area - x.area);
faces.forEach((f, i) => { f.id = 'F' + (i + 1); });

// 2) 洞：从全部内部面里找（和编辑器 rebuildRealms 一致）
const inner = faces.filter(f => !f.outer);
for (const f of inner) {
  for (const g of inner) {
    if (g.area >= f.area) continue;
    if (g.ring === f.ring) continue;
    if (G.pointInRing(g.ring[0][0], g.ring[0][1], f.ring)) f.holes.push(g.ring);
  }
}

// 3) 认领 → 面
const claims = (b.claims || []).map((c, i) => {
  let f = c.face ? faces.find(x => x.id === c.face) : null;
  if (!f) f = G.locate(faces, c.seed[0], c.seed[1]);
  return f ? { idx: i, face: f.id, area: Math.round(f.area), nation: c.nation || '', faction: c.faction || '' } : null;
}).filter(Boolean);

const out = {
  faces: faces.map(f => ({ id: f.id, area: Math.round(f.area), outer: f.outer, ring: f.ring, holes: f.holes })),
  claims
};
fs.writeFileSync(path.join(ROOT, 'tools', '_probe_faces.json'), JSON.stringify(out));
console.log('面', faces.length, '内部', inner.length, '认领', claims.length);
