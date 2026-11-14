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

function pip(x, y, ring) {
  let c = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
    if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / ((yj - yi) || 1e-12) + xi)) c = !c;
  }
  return c;
}

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

  // 全部水系参与：种子被河围着、没有边界线时也要能成面
  const res = A.build(edges.concat(water), { minArea: 300 });
  const faces = res.faces;

  const out = [];
  for (const c of claims) {
    if (!c.seed) continue;
    const f = faces.find(fc => !fc.outer && A.contains(fc, c.seed[0], c.seed[1]));
    if (!f) continue;
    out.push({ nation: c.nation || '', faction: c.faction || '', note: c.note || '',
               area: Math.round(f.area), ring: f.ring, holes: (f.holes || []).slice() });
  }

  // 嵌套面补洞：两层半透明叠在一起会更深。凡是完全落在某个已认领面内部的
  // 更小面（不论归属），都作为那个面的洞。
  for (const a of out) {
    for (const b of out) {
      if (a === b) continue;
      if (b.area >= a.area) continue;
      if (!b.ring || b.ring.length < 4) continue;
      if (pip(b.ring[0][0], b.ring[0][1], a.ring)) {
        const k = b.ring.length + ':' + b.ring[0][0].toFixed(1) + ',' + b.ring[0][1].toFixed(1);
        a._k = a._k || new Set();
        if (!a._k.has(k)) { a._k.add(k); a.holes.push(b.ring); }
      }
    }
    delete a._k;
  }

  const dest = path.join(ROOT, 'data', 'map', 'faces.json');
  fs.writeFileSync(dest, JSON.stringify({ updated: new Date().toISOString(), faces: out }));
  console.log(`面 ${faces.length} 个，认领 ${out.length} 块 → ${dest}  用时 ${res.stats.ms}ms`);
}

main();
