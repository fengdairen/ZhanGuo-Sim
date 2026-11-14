// tools/smoke/arrangement_real.js —— 用真实数据跑一遍平面划分，看规模与耗时
const fs = require('fs');
const path = require('path');
global.window = global;
const A = require(path.join(__dirname, '..', 'pipeline', 'arrangement.js'));

const ROOT = path.join(__dirname, '..', '..');
const V = path.join(ROOT, 'data', 'map', 'vector');
const load = n => JSON.parse(fs.readFileSync(path.join(V, n), 'utf8'));

const rivers = load('rivers_w.json').map(r => {
  const pts = [];
  for (let i = 1; i < r.length; i += 2) pts.push([r[i], r[i + 1]]);
  return pts;
});
const coasts = load('coast_drawn.json').map(c => {
  const pts = [];
  for (let i = 0; i < c.pts.length; i += 2) pts.push([c.pts[i], c.pts[i + 1]]);
  return pts;
});
const lakes = load('lakes_drawn.json').map(l => {
  const pts = [];
  for (let i = 0; i < l.pts.length; i += 2) pts.push([l.pts[i], l.pts[i + 1]]);
  return pts;
});
const borders = JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'map', 'borders.json'), 'utf8'));
const edges = (borders.edges || []).map(e => e.pts);

const water = rivers.concat(coasts, lakes);
function run(name, lines) {
  const t = Date.now();
  const r = A.build(lines, { minArea: 400, snapTo: process.argv.includes('--water') ? water : null });
  const ms = Date.now() - t;
  const faces = r.faces;
  const total = faces.reduce((s, f) => s + f.area, 0);
  console.log(`${name}: 线 ${lines.length} 段 ${r.stats.segs} 节点 ${r.stats.nodes} 交点 ${r.stats.hits} → 面 ${faces.length}  用时 ${ms}ms`);
  return r;
}

const only = run('仅边界线', edges);

// 只用"边界线碰到的那几条水系"来闭合
const bpts = [];
for (const e of edges) for (const p of e) bpts.push(p);
function nearBorder(line){
  for (const p of line) for (const q of bpts){
    if (Math.hypot(p[0]-q[0], p[1]-q[1]) < 30) return true;
  }
  return false;
}
const nearWater = water.filter(nearBorder);
const mixed = run('边界 + 相关水系', edges.concat(nearWater));
const withWater = process.argv.includes('--water') ? run('边界+河湖海', edges.concat(rivers, coasts, lakes)) : null;

// 面大小分布
function hist(r, label) {
  const areas = r.faces.map(f => Math.round(f.area)).sort((a, b) => a - b);
  const pick = p => areas[Math.floor((areas.length - 1) * p)] || 0;
  console.log(`  ${label} 面面积 中位 ${pick(0.5)}  90% ${pick(0.9)}  最大 ${areas[areas.length - 1] || 0}`);
}
hist(only, '仅边界');
if (withWater) hist(withWater, '含水系');
