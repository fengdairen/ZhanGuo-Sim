/* faces.js —— 生成舆图用的"面 + 归属"数据
 *
 * 输入：data/map/borders.json（边界线 + 国家 + 认领种子点）
 *       data/map/vector/*.json（河网、海岸、湖泊）
 * 输出：data/map/faces.json   [{nation, faction, note, ring, area}]
 *
 * 只把"边界线端点碰到的水系"纳入划分，否则会被整张河网切成几百个河间盆地。
 *
 * 用法：node tools/pipeline/faces.js
 */
'use strict';
const fs = require('fs');
const path = require('path');
global.window = global;
const A = require(path.join(__dirname, 'arrangement.js'));

const ROOT = path.join(__dirname, '..', '..');
const V = path.join(ROOT, 'data', 'map', 'vector');
const load = n => JSON.parse(fs.readFileSync(path.join(V, n), 'utf8'));

function flatToPts(f) {
  const out = [];
  for (let i = 0; i + 1 < f.length; i += 2) out.push([f[i], f[i + 1]]);
  return out;
}

function main() {
  const bp = path.join(ROOT, 'data', 'map', 'borders.json');
  if (!fs.existsSync(bp)) { console.log('没有 borders.json'); return; }
  const b = JSON.parse(fs.readFileSync(bp, 'utf8'));
  const edges = (b.edges || []).map(e => e.pts);
  const claims = b.claims || [];

  const water = []
    .concat(load('rivers_w.json').map(r => flatToPts(r.slice(1))))
    .concat(load('coast_drawn.json').map(c => flatToPts(c.pts)))
    .concat(load('lakes_drawn.json').map(l => flatToPts(l.pts)));

  const bp2 = [];
  for (const e of edges) { if (e.length) { bp2.push(e[0]); bp2.push(e[e.length - 1]); } }
  const near = line => line.some(q => bp2.some(p => Math.hypot(p[0] - q[0], p[1] - q[1]) < 30));
  const used = water.filter(near);

  const res = A.build(edges.concat(used), { minArea: 300 });
  const faces = res.faces;

  const out = [];
  for (const c of claims) {
    if (!c.seed) continue;
    const f = faces.find(fc => A.contains(fc, c.seed[0], c.seed[1]));
    if (!f) continue;
    out.push({ nation: c.nation || '', faction: c.faction || '', note: c.note || '',
               area: Math.round(f.area), ring: f.ring });
  }

  const dest = path.join(ROOT, 'data', 'map', 'faces.json');
  fs.writeFileSync(dest, JSON.stringify({ updated: new Date().toISOString(), faces: out }));
  console.log(`面 ${faces.length} 个，认领 ${out.length} 块 → ${dest}  用时 ${res.stats.ms}ms`);
}

main();
