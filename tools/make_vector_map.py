# -*- coding: utf-8 -*-
"""由矢量化结果生成独立的矢量地图 HTML（不依赖任何位图、不依赖服务器）。

输入 data/map/vector/*.json + data/map/nodes.csv + regions.csv
输出 dist/map-vector/map.html
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VEC = ROOT / "data" / "map" / "vector"
OUTDIR = ROOT / "dist" / "map-vector"
OUT = OUTDIR / "map.html"


def load(name):
    return json.loads((VEC / name).read_text(encoding="utf-8"))


rivers = load("rivers_w.json")
lakes = load("lakes.json")
borders = load("borders.json")
coast = load("coast.json")

cities = []
for r in csv.DictReader(open(ROOT / "data" / "map" / "nodes.csv", encoding="utf-8-sig")):
    cities.append([r["id"], r["name"], r["kind"], round(float(r["x"]), 1), round(float(r["y"]), 1),
                   round(float(r["pop"] or 0), 2)])

regions = []
for r in csv.DictReader(open(ROOT / "data" / "map" / "regions.csv", encoding="utf-8-sig")):
    regions.append([r["id"], r["name"], round(float(r["x"]), 1), round(float(r["y"]), 1),
                    round(float(r["pop"] or 0), 2)])

data = {
    "meta": {"canvas": [9101, 8509], "source": "底图河道湖泊.png / 底图海岸线.png"},
    "sea": coast["sea"],
    "islands": coast["islands"],
    "coast": coast["lines"],
    "lakes": lakes,
    "rivers": rivers,
    "borders": borders,
    "cities": cities,
    "regions": regions,
}

payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)

HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>战国演义 · 矢量地图</title>
<style>
  :root{
    --paper:#f2e7cb; --ink:#33241a; --sea:#b9c7cc; --sea-edge:#8ca0aa;
    --river:#3e7ca6; --lake:#7fb0c9; --border:#a8703c; --accent:#8b2e1e;
  }
  *{box-sizing:border-box}
  html,body{margin:0;height:100%;overflow:hidden;background:var(--paper);
    font-family:"Songti SC","STSong","SimSun","Noto Serif CJK SC",serif;color:var(--ink)}
  #cv{display:block;width:100%;height:100%;cursor:grab;touch-action:none}
  #cv.drag{cursor:grabbing}
  .panel{position:fixed;background:rgba(250,244,229,.93);border:1px solid rgba(120,90,56,.35);
    border-radius:10px;box-shadow:0 6px 22px rgba(80,55,30,.14);backdrop-filter:blur(6px)}
  #hud{top:14px;left:14px;width:232px;padding:12px 13px 11px;font-size:13px}
  #hud h1{margin:0 0 2px;font-size:16px;letter-spacing:2px;font-weight:600}
  #hud .sub{font-size:11px;color:#7a6a55;margin-bottom:9px;letter-spacing:.5px}
  .row{display:flex;align-items:center;gap:7px;margin:5px 0;cursor:pointer;user-select:none}
  .row input{accent-color:#8b6a3f;margin:0}
  .sw{display:inline-block;width:12px;height:3px;border-radius:2px;flex:none}
  .sw.sea{background:var(--sea)}
  .sw.river{background:var(--river)}
  .sw.border{background:var(--border)}
  .sw.city{background:var(--accent);height:7px;width:7px;border-radius:50%}
  #q{width:100%;padding:5px 7px;margin-top:8px;border:1px solid rgba(120,90,56,.35);
    border-radius:6px;background:#fffdf6;font:inherit;font-size:12px;color:inherit}
  #q:focus{outline:2px solid rgba(139,46,30,.25);outline-offset:1px}
  #hits{font-size:11px;color:#7a6a55;margin-top:5px;min-height:14px}
  #foot{bottom:14px;left:14px;padding:8px 11px;font-size:11.5px;color:#6d5c47;letter-spacing:.3px}
  #zoom{bottom:14px;right:14px;padding:7px 10px;font-size:11.5px;color:#6d5c47;font-variant-numeric:tabular-nums}
  #tip{position:fixed;pointer-events:none;padding:5px 9px;font-size:12px;background:rgba(48,33,20,.9);
    color:#f6eeda;border-radius:6px;transform:translate(-50%,-160%);opacity:0;transition:opacity .12s;
    white-space:nowrap;z-index:9}
  .btn{position:fixed;right:14px;top:14px;display:flex;gap:6px;z-index:5}
  .btn button{padding:6px 11px;font:inherit;font-size:12px;color:#4a3524;cursor:pointer;
    background:rgba(250,244,229,.93);border:1px solid rgba(120,90,56,.35);border-radius:8px}
  .btn button:hover{background:#fffdf6}
</style>
</head>
<body>
<canvas id="cv"></canvas>

<div id="hud" class="panel">
  <h1>战国演义 · 舆图</h1>
  <div class="sub">BC 400 · 矢量版（无底图）</div>
  <label class="row"><input type="checkbox" id="lSea" checked><span class="sw sea"></span>海岸与海域</label>
  <label class="row"><input type="checkbox" id="lLake" checked><span class="sw sea"></span>湖泊</label>
  <label class="row"><input type="checkbox" id="lRiver" checked><span class="sw river"></span>河流</label>
  <label class="row"><input type="checkbox" id="lBorder" checked><span class="sw border"></span>国界</label>
  <label class="row"><input type="checkbox" id="lCity" checked><span class="sw city"></span>城邑</label>
  <label class="row"><input type="checkbox" id="lLabel" checked>地名标注</label>
  <label class="row"><input type="checkbox" id="lRegion">部族</label>
  <input id="q" placeholder="搜地名，回车定位">
  <div id="hits"></div>
</div>

<div class="btn">
  <button id="bFit">全图</button>
  <button id="bIn">＋</button>
  <button id="bOut">－</button>
</div>
<div id="foot" class="panel">滚轮缩放 · 拖拽平移 · 双击放大</div>
<div id="zoom" class="panel">—</div>
<div id="tip"></div>

<script>
const DATA = __DATA__;

const CW = 9101, CH = 8509;
const cv = document.getElementById('cv');
const ctx = cv.getContext('2d');
const tip = document.getElementById('tip');
const zoomEl = document.getElementById('zoom');

const COL = {
  paper:'#f2e7cb', paper2:'#e9dbb8', ink:'#33241a',
  sea:'#b9c7cc', seaEdge:'#8ca0aa', seaDeep:'#aabcc2',
  river:'#3e7ca6', lake:'#7fb0c9', lakeEdge:'#3e7ca6',
  border:'#a8703c', coast:'#6d7f8c',
  du:'#8b2e1e', cheng:'#6b4a2f', yi:'#7a6248', label:'#33241a',
  halo:'rgba(246,238,216,.92)', region:'#a2543a'
};

let dpr = Math.min(2.5, window.devicePixelRatio || 1);
let cw = 0, ch = 0;
const V = { scale: 0.15, tx: 0, ty: 0 };

function resize(){
  cw = cv.clientWidth; ch = cv.clientHeight;
  cv.width = Math.round(cw*dpr); cv.height = Math.round(ch*dpr);
  draw();
}

function fit(){
  const s = Math.min(cw/CW, ch/CH) * 0.98;
  V.scale = s;
  V.tx = (cw - CW*s)/2;
  V.ty = (ch - CH*s)/2;
  draw();
}

function w2s(x,y){ return [x*V.scale + V.tx, y*V.scale + V.ty]; }

// ---------- 静态几何 ----------
function pathOf(poly, close){
  const p = new Path2D();
  for (let i=0;i<poly.length;i+=2){
    const x = poly[i], y = poly[i+1];
    if (i===0) p.moveTo(x,y); else p.lineTo(x,y);
  }
  if (close) p.closePath();
  return p;
}

const G = { sea:new Path2D(), islands:new Path2D(), lakes:new Path2D(), lakesEdge:new Path2D(),
            coast:new Path2D(), borders:new Path2D(), riverBuckets:[] };

for (const poly of DATA.sea) G.sea.addPath(pathOf(poly, true));
for (const poly of DATA.islands){ G.islands.addPath(pathOf(poly, true)); }
for (const poly of DATA.lakes){
  G.lakes.addPath(pathOf(poly, true));
  G.lakesEdge.addPath(pathOf(poly, true));
}
for (const line of DATA.coast) G.coast.addPath(pathOf(line, false));
for (const line of DATA.borders) G.borders.addPath(pathOf(line, false));

// 河流按线宽分桶（每桶一次 stroke，避免上千次状态切换）
(function(){
  const buckets = new Map();
  for (const e of DATA.rivers){
    const w = e[0];
    const key = Math.round(w*2)/2;
    if (!buckets.has(key)) buckets.set(key, new Path2D());
    const p = buckets.get(key);
    p.moveTo(e[1], e[2]);
    for (let i=3;i<e.length;i+=2) p.lineTo(e[i], e[i+1]);
  }
  G.riverBuckets = [...buckets.entries()].sort((a,b)=>a[0]-b[0]);
})();

const CITIES = DATA.cities.map(c => ({id:c[0], name:c[1], kind:c[2], x:c[3], y:c[4], pop:c[5]}));
const REGIONS = DATA.regions.map(r => ({id:r[0], name:r[1], x:r[2], y:r[3], pop:r[4]}));

// ---------- 绘制 ----------
const el = id => document.getElementById(id);
const layer = () => ({
  sea: el('lSea').checked, lake: el('lLake').checked, river: el('lRiver').checked,
  border: el('lBorder').checked, city: el('lCity').checked,
  label: el('lLabel').checked, region: el('lRegion').checked
});

let hoverCity = null, flash = null;

function draw(){
  const L = layer();
  ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.clearRect(0,0,cw,ch);

  // 纸底
  const g = ctx.createRadialGradient(cw*0.5, ch*0.42, Math.min(cw,ch)*0.15, cw*0.5, ch*0.5, Math.max(cw,ch)*0.78);
  g.addColorStop(0, '#f6eed6');
  g.addColorStop(1, '#e6d6b0');
  ctx.fillStyle = g; ctx.fillRect(0,0,cw,ch);

  // 世界坐标
  ctx.setTransform(dpr*V.scale,0,0,dpr*V.scale,dpr*V.tx,dpr*V.ty);

  if (L.sea){
    ctx.fillStyle = COL.sea; ctx.fill(G.sea, 'evenodd');
    ctx.strokeStyle = COL.seaEdge; ctx.lineWidth = 1.1/V.scale; ctx.stroke(G.sea);
  }
  if (L.lake){
    ctx.fillStyle = COL.lake; ctx.fill(G.lakes, 'evenodd');
    ctx.strokeStyle = COL.lakeEdge; ctx.lineWidth = Math.max(0.6, 0.9/V.scale); ctx.stroke(G.lakesEdge);
  }
  if (L.river){
    ctx.strokeStyle = COL.river; ctx.lineJoin='round'; ctx.lineCap='round';
    for (const [w, p] of G.riverBuckets){
      ctx.lineWidth = Math.max(0.7/V.scale, w);
      ctx.stroke(p);
    }
  }
  if (L.border){
    ctx.save();
    ctx.strokeStyle = COL.border; ctx.lineWidth = Math.max(0.7/V.scale, 1.15);
    ctx.setLineDash([9/V.scale, 6/V.scale]); ctx.globalAlpha = .85;
    ctx.stroke(G.borders);
    ctx.restore();
  }
  if (L.sea){
    ctx.strokeStyle = COL.coast; ctx.lineWidth = Math.max(0.6/V.scale, 1.0); ctx.stroke(G.coast);
  }

  // 屏幕坐标：城邑与标注
  ctx.setTransform(dpr,0,0,dpr,0,0);

  if (L.region){
    ctx.font = '12px "Songti SC","SimSun",serif';
    for (const r of REGIONS){
      const [sx,sy] = w2s(r.x, r.y);
      if (sx < -40 || sy < -40 || sx > cw+40 || sy > ch+40) continue;
      ctx.beginPath(); ctx.arc(sx, sy, 3.2, 0, 6.283);
      ctx.fillStyle = COL.region; ctx.globalAlpha = .8; ctx.fill(); ctx.globalAlpha = 1;
      ctx.fillStyle = 'rgba(120,66,44,.9)';
      ctx.fillText(r.name, sx+7, sy+4);
    }
  }

  if (L.city){
    for (const c of CITIES){
      const [sx,sy] = w2s(c.x, c.y);
      if (sx < -8 || sy < -8 || sx > cw+8 || sy > ch+8) continue;
      if (c.kind === '都'){
        ctx.beginPath(); ctx.arc(sx, sy, 4.6, 0, 6.283);
        ctx.fillStyle = COL.du; ctx.fill();
        ctx.beginPath(); ctx.arc(sx, sy, 7.2, 0, 6.283);
        ctx.strokeStyle = COL.du; ctx.lineWidth = 1.1; ctx.globalAlpha=.75; ctx.stroke(); ctx.globalAlpha=1;
      } else if (c.kind === '城'){
        ctx.beginPath(); ctx.arc(sx, sy, 3.1, 0, 6.283);
        ctx.fillStyle = COL.cheng; ctx.fill();
        ctx.strokeStyle = 'rgba(246,238,216,.8)'; ctx.lineWidth = .8; ctx.stroke();
      } else {
        ctx.beginPath(); ctx.arc(sx, sy, 1.6, 0, 6.283);
        ctx.fillStyle = COL.yi; ctx.globalAlpha = .9; ctx.fill(); ctx.globalAlpha = 1;
      }
    }
  }

  if (L.label) drawLabels();

  if (hoverCity){
    const [sx,sy] = w2s(hoverCity.x, hoverCity.y);
    ctx.beginPath(); ctx.arc(sx, sy, 8.5, 0, 6.283);
    ctx.strokeStyle = 'rgba(139,46,30,.75)'; ctx.lineWidth = 1.6; ctx.stroke();
  }
  if (flash){
    const [sx,sy] = w2s(flash.x, flash.y);
    const t = (performance.now() - flash.t) / 900;
    if (t < 1){
      ctx.beginPath(); ctx.arc(sx, sy, 10 + 26*t, 0, 6.283);
      ctx.strokeStyle = `rgba(139,46,30,${0.75*(1-t)})`; ctx.lineWidth = 2; ctx.stroke();
      requestAnimationFrame(draw);
    } else flash = null;
  }
  zoomEl.textContent = '缩放 ' + (V.scale*100).toFixed(0) + '%';
}

function drawLabels(){
  const showYi = V.scale > 0.30;
  const fs = V.scale > 0.6 ? 13 : 12;
  ctx.font = `${fs}px "Songti SC","SimSun",serif`;
  ctx.textBaseline = 'middle';
  const boxes = [];
  const grid = new Map();
  const CELL = 90;
  const overlap = (x,y,w,h) => {
    const gx = Math.floor(x/CELL), gy = Math.floor(y/CELL);
    for (let i=gx-1;i<=gx+1;i++) for (let j=gy-1;j<=gy+1;j++){
      const arr = grid.get(i+','+j); if (!arr) continue;
      for (const b of arr) if (x < b[0]+b[2] && x+w > b[0] && y < b[1]+b[3] && y+h > b[1]) return true;
    }
    return false;
  };
  const push = (x,y,w,h) => {
    const k = Math.floor(x/CELL)+','+Math.floor(y/CELL);
    if (!grid.has(k)) grid.set(k, []);
    grid.get(k).push([x,y,w,h]);
  };
  // 都 > 城 > 邑
  const order = { '都':0, '城':1, '邑':2 };
  const list = CITIES.slice().sort((a,b)=> (order[a.kind]-order[b.kind]) || (b.pop-a.pop));
  for (const c of list){
    if (c.kind === '邑' && !showYi) continue;
    const [sx,sy] = w2s(c.x, c.y);
    if (sx < -60 || sy < -20 || sx > cw+60 || sy > ch+20) continue;
    const pad = c.kind === '邑' ? 5 : 7;
    const w = ctx.measureText(c.name).width;
    const h = fs + 2;
    const x = sx + pad, y = sy - h/2;
    if (overlap(x, y, w, h)) continue;
    push(x, y, w, h);
    ctx.lineWidth = 3;
    ctx.strokeStyle = COL.halo;
    ctx.strokeText(c.name, x, sy);
    ctx.fillStyle = c.kind === '都' ? '#5c1f14' : (c.kind === '城' ? '#3d2a1a' : '#5d4a35');
    ctx.fillText(c.name, x, sy);
  }
}

// ---------- 交互 ----------
let dragging = false, last = null;

cv.addEventListener('pointerdown', e => {
  dragging = true; last = [e.clientX, e.clientY];
  cv.classList.add('drag'); cv.setPointerCapture(e.pointerId);
});
cv.addEventListener('pointerup', e => {
  dragging = false; cv.classList.remove('drag');
});
cv.addEventListener('pointermove', e => {
  if (dragging && last){
    V.tx += e.clientX - last[0];
    V.ty += e.clientY - last[1];
    last = [e.clientX, e.clientY];
    draw();
    return;
  }
  // hover
  const r = cv.getBoundingClientRect();
  const mx = e.clientX - r.left, my = e.clientY - r.top;
  let best = null, bd = 9;
  for (const c of CITIES){
    const [sx,sy] = w2s(c.x,c.y);
    const d = Math.hypot(sx-mx, sy-my);
    if (d < bd){ bd = d; best = c; }
  }
  if (best !== hoverCity){ hoverCity = best; draw(); }
  if (best){
    tip.style.opacity = 1;
    tip.style.left = (r.left + w2s(best.x,best.y)[0]) + 'px';
    tip.style.top = (r.top + w2s(best.x,best.y)[1]) + 'px';
    tip.textContent = `${best.name} · ${best.kind} · ${best.pop} 万`;
  } else tip.style.opacity = 0;
});

cv.addEventListener('wheel', e => {
  e.preventDefault();
  const r = cv.getBoundingClientRect();
  const mx = e.clientX - r.left, my = e.clientY - r.top;
  const wx = (mx - V.tx)/V.scale, wy = (my - V.ty)/V.scale;
  const k = Math.exp(-e.deltaY * 0.0016);
  V.scale = Math.max(0.05, Math.min(9, V.scale * k));
  V.tx = mx - wx*V.scale; V.ty = my - wy*V.scale;
  draw();
}, {passive:false});

cv.addEventListener('dblclick', e => {
  const r = cv.getBoundingClientRect();
  const mx = e.clientX - r.left, my = e.clientY - r.top;
  const wx = (mx - V.tx)/V.scale, wy = (my - V.ty)/V.scale;
  V.scale = Math.min(9, V.scale*1.7);
  V.tx = mx - wx*V.scale; V.ty = my - wy*V.scale;
  draw();
});

function flyTo(c){
  V.scale = Math.max(V.scale, 0.62);
  V.tx = cw/2 - c.x*V.scale;
  V.ty = ch/2 - c.y*V.scale;
  flash = {x:c.x, y:c.y, t:performance.now()};
  draw();
}

el('bFit').onclick = fit;
el('bIn').onclick = () => { V.scale = Math.min(9, V.scale*1.35);
  const wx=(cw/2-V.tx)/V.scale, wy=(ch/2-V.ty)/V.scale;
  V.tx = cw/2-wx*V.scale; V.ty = ch/2-wy*V.scale; draw(); };
el('bOut').onclick = () => { V.scale = Math.max(0.05, V.scale/1.35);
  const wx=(cw/2-V.tx)/V.scale, wy=(ch/2-V.ty)/V.scale;
  V.tx = cw/2-wx*V.scale; V.ty = ch/2-wy*V.scale; draw(); };

for (const id of ['lSea','lLake','lRiver','lBorder','lCity','lLabel','lRegion'])
  el(id).addEventListener('change', draw);

const q = el('q'), hits = el('hits');
q.addEventListener('keydown', e => {
  if (e.key !== 'Enter') return;
  const kw = q.value.trim();
  if (!kw){ hits.textContent=''; return; }
  const found = CITIES.filter(c => c.name.includes(kw));
  const foundR = REGIONS.filter(r => r.name.includes(kw));
  if (found.length + foundR.length === 0){ hits.textContent = '无匹配'; return; }
  hits.textContent = `命中 ${found.length + foundR.length}：` + found.concat(foundR).slice(0,6).map(c=>c.name).join('、');
  const t = found[0] || foundR[0];
  flyTo(t);
});

window.addEventListener('keydown', e => {
  if (e.target === q) return;
  if (e.key === '+' || e.key === '=') el('bIn').click();
  if (e.key === '-') el('bOut').click();
  if (e.key === '0') fit();
});
window.addEventListener('resize', resize);

resize(); fit();
document.getElementById('foot').textContent =
  `河 ${DATA.rivers.length} 段 · 湖 ${DATA.lakes.length} 处 · 国界 ${DATA.borders.length} 段 · 城邑 ${CITIES.length} 座`;
</script>
</body>
</html>
"""

OUTDIR.mkdir(parents=True, exist_ok=True)
OUT.write_text(HTML.replace("__DATA__", payload), encoding="utf-8")
print(f"written {OUT}  {OUT.stat().st_size/1024:.0f} KB")
