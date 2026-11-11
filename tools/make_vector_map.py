# -*- coding: utf-8 -*-
"""由矢量化结果生成独立的矢量地图 HTML（不依赖任何位图、不依赖服务器）。

输入 data/map/vector/*.json + data/map/nodes.csv + regions.csv
输出 dist/map-vector/map.html

关于「边界线」：底图里的棕/深色线经实测是河道描边（与红线零重叠、
100% 落在红线 2px 内），不是独立的国界层，因此不单独成层，
改为绘制河流时套一层描边，还原参考图的观感。
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
coast = load("coast.json")

cities = []
for r in csv.DictReader(open(ROOT / "data" / "map" / "nodes.csv", encoding="utf-8-sig")):
    cities.append([r["id"], r["name"], r["kind"], round(float(r["x"]), 1), round(float(r["y"]), 1),
                   round(float(r["pop"] or 0), 2)])

regions = []
for r in csv.DictReader(open(ROOT / "data" / "map" / "regions.csv", encoding="utf-8-sig")):
    regions.append([r["id"], r["name"], round(float(r["x"]), 1), round(float(r["y"]), 1),
                    round(float(r["pop"] or 0), 2)])

def flat(poly):
    """[[x,y],...] -> [x1,y1,x2,y2,...]；前端 pathOf 只认扁平数组。"""
    out = []
    for p in poly:
        out.append(round(float(p[0]), 1))
        out.append(round(float(p[1]), 1))
    return out


data = {
    "meta": {"canvas": [9101, 8509], "source": "底图河道湖泊.png / 底图海岸线.png"},
    "sea": [flat(p) for p in coast["sea"]],
    "islands": [flat(p) for p in coast["islands"]],
    "coast": [flat(p) for p in coast["lines"]],
    "lakes": [flat(p) for p in lakes],
    "rivers": rivers,
    "cities": cities,
    "regions": regions,
}

payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)

HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>战国演义 · 矢量舆图 BC 390</title>
<style>
  :root{
    --paper:#f2e7cb; --ink:#33241a;
    --sea:#b8c6cc; --sea-edge:#8ca0aa;
    --river:#3e7ca6; --river-case:#8a6a48; --lake:#7fb0c9;
  }
  *{box-sizing:border-box}
  html,body{margin:0;height:100%;overflow:hidden;background:var(--paper);
    font-family:"Songti SC","STSong","SimSun","Noto Serif CJK SC",serif;color:var(--ink)}
  #cv{display:block;width:100%;height:100%;cursor:grab;touch-action:none}
  #cv.drag{cursor:grabbing}
  .panel{position:fixed;background:rgba(250,244,229,.94);border:1px solid rgba(120,90,56,.35);
    border-radius:10px;box-shadow:0 6px 22px rgba(80,55,30,.14);backdrop-filter:blur(6px)}
  #hud{top:14px;left:14px;width:236px;padding:12px 13px 11px;font-size:13px}
  #hud h1{margin:0 0 2px;font-size:16px;letter-spacing:2px;font-weight:600}
  #hud .sub{font-size:11px;color:#7a6a55;margin-bottom:9px;letter-spacing:.5px}
  .row{display:flex;align-items:center;gap:7px;margin:5px 0;cursor:pointer;user-select:none}
  .row input{accent-color:#8b6a3f;margin:0}
  .sw{display:inline-block;width:13px;height:3px;border-radius:2px;flex:none}
  .sw.sea{background:var(--sea)}
  .sw.lake{background:var(--lake)}
  .sw.river{background:var(--river)}
  .sw.city{background:#8b2e1e;height:7px;width:7px;border-radius:50%}
  .sw.region{background:#a2543a;height:7px;width:7px;border-radius:50%;opacity:.75}
  .legend{display:flex;gap:14px;margin:9px 0 2px;font-size:12px;color:#5b4a37;align-items:center}
  .legend i.m{display:inline-block;border-radius:50%;margin-right:4px;vertical-align:middle}
  .legend i.du{width:9px;height:9px;background:#8b2e1e;box-shadow:0 0 0 2px rgba(139,46,30,.25)}
  .legend i.cheng{width:6px;height:6px;background:#6b4a2f}
  .legend i.yi{width:4px;height:4px;background:#7a6248}
  #q{width:100%;padding:5px 7px;margin-top:8px;border:1px solid rgba(120,90,56,.35);
    border-radius:6px;background:#fffdf6;font:inherit;font-size:12px;color:inherit}
  #q:focus{outline:2px solid rgba(139,46,30,.25);outline-offset:1px}
  #hits{font-size:11px;color:#7a6a55;margin-top:5px;min-height:14px;line-height:1.5}
  #foot{bottom:14px;left:14px;padding:8px 11px;font-size:11.5px;color:#6d5c47;letter-spacing:.3px}
  #zoom{bottom:14px;right:14px;padding:7px 10px;font-size:11.5px;color:#6d5c47;font-variant-numeric:tabular-nums}
  #tip{position:fixed;pointer-events:none;padding:5px 9px;font-size:12px;background:rgba(48,33,20,.92);
    color:#f6eeda;border-radius:6px;transform:translate(-50%,-165%);opacity:0;transition:opacity .12s;
    white-space:nowrap;z-index:9}
  .btn{position:fixed;right:14px;top:14px;display:flex;gap:6px;z-index:5}
  .btn button{padding:6px 11px;font:inherit;font-size:12px;color:#4a3524;cursor:pointer;
    background:rgba(250,244,229,.94);border:1px solid rgba(120,90,56,.35);border-radius:8px}
  .btn button:hover{background:#fffdf6}
</style>
</head>
<body>
<canvas id="cv"></canvas>

<div id="hud" class="panel">
  <h1>战国演义 · 舆图</h1>
  <div class="sub">BC 390 · 矢量版（无底图）</div>
  <label class="row"><input type="checkbox" id="lSea" checked><span class="sw sea"></span>海岸与海域</label>
  <label class="row"><input type="checkbox" id="lLake" checked><span class="sw lake"></span>湖泊</label>
  <label class="row"><input type="checkbox" id="lRiver" checked><span class="sw river"></span>河流</label>
  <label class="row"><input type="checkbox" id="lCity" checked><span class="sw city"></span>城邑</label>
  <label class="row"><input type="checkbox" id="lLabel" checked>地名标注</label>
  <label class="row"><input type="checkbox" id="lRegion"><span class="sw region"></span>部族</label>
  <div class="legend"><span><i class="m du"></i>都</span><span><i class="m cheng"></i>城</span><span><i class="m yi"></i>邑</span></div>
  <input id="q" placeholder="搜地名，回车定位">
  <div id="hits"></div>
</div>

<div class="btn">
  <button id="bFit">全图</button>
  <button id="bIn">＋</button>
  <button id="bOut">－</button>
</div>
<div id="foot" class="panel"></div>
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
  sea:'#b8c6cc', seaEdge:'#8ca0aa', coast:'#6d7f8c',
  river:'#3e7ca6', riverCase:'rgba(122,90,58,.55)',
  lake:'#7fb0c9', lakeEdge:'#3e7ca6',
  du:'#8b2e1e', cheng:'#6b4a2f', yi:'#7a6248',
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
  V.scale = s; V.tx = (cw - CW*s)/2; V.ty = (ch - CH*s)/2;
  draw();
}
const w2s = (x,y) => [x*V.scale + V.tx, y*V.scale + V.ty];

function pathOf(poly, close){
  const p = new Path2D();
  for (let i=0;i<poly.length;i+=2){
    if (i===0) p.moveTo(poly[i], poly[i+1]); else p.lineTo(poly[i], poly[i+1]);
  }
  if (close) p.closePath();
  return p;
}

const G = { sea:new Path2D(), islands:new Path2D(), lakes:new Path2D(),
            coast:new Path2D(), riverBuckets:[] };
for (const poly of DATA.sea) G.sea.addPath(pathOf(poly, true));
for (const poly of DATA.islands) G.islands.addPath(pathOf(poly, true));
for (const poly of DATA.lakes) G.lakes.addPath(pathOf(poly, true));
for (const line of DATA.coast) G.coast.addPath(pathOf(line, false));

(function(){
  const buckets = new Map();
  for (const e of DATA.rivers){
    const key = Math.round(e[0]*2)/2;
    if (!buckets.has(key)) buckets.set(key, new Path2D());
    const p = buckets.get(key);
    p.moveTo(e[1], e[2]);
    for (let i=3;i<e.length;i+=2) p.lineTo(e[i], e[i+1]);
  }
  G.riverBuckets = [...buckets.entries()].sort((a,b)=>a[0]-b[0]);
})();

const CITIES = DATA.cities.map(c => ({id:c[0], name:c[1], kind:c[2], x:c[3], y:c[4], pop:c[5]}));
const REGIONS = DATA.regions.map(r => ({id:r[0], name:r[1], x:r[2], y:r[3], pop:r[4]}));

const el = id => document.getElementById(id);
const state = () => ({
  sea: el('lSea').checked, lake: el('lLake').checked, river: el('lRiver').checked,
  city: el('lCity').checked, label: el('lLabel').checked, region: el('lRegion').checked
});
let hoverCity = null, flash = null;

function draw(){
  const L = state();
  ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.clearRect(0,0,cw,ch);

  const g = ctx.createRadialGradient(cw*0.5, ch*0.42, Math.min(cw,ch)*0.12,
                                     cw*0.5, ch*0.55, Math.max(cw,ch)*0.8);
  g.addColorStop(0, '#f7efd8'); g.addColorStop(1, '#e5d5ae');
  ctx.fillStyle = g; ctx.fillRect(0,0,cw,ch);

  ctx.setTransform(dpr*V.scale,0,0,dpr*V.scale,dpr*V.tx,dpr*V.ty);

  if (L.sea){
    ctx.fillStyle = COL.sea; ctx.fill(G.sea, 'evenodd');
    ctx.strokeStyle = COL.seaEdge; ctx.lineWidth = 1.2/V.scale; ctx.stroke(G.sea);
    if (DATA.islands.length){
      ctx.fillStyle = '#efe2c2'; ctx.fill(G.islands, 'evenodd');
      ctx.strokeStyle = COL.coast; ctx.lineWidth = Math.max(0.7/V.scale, 1); ctx.stroke(G.islands);
    }
  }
  if (L.lake){
    ctx.fillStyle = COL.lake; ctx.fill(G.lakes, 'evenodd');
    ctx.strokeStyle = COL.lakeEdge; ctx.lineWidth = Math.max(0.6, 1.0/V.scale); ctx.stroke(G.lakes);
  }
  if (L.river){
    ctx.lineJoin = 'round'; ctx.lineCap = 'round';
    // 先描边（深），再压主色，还原参考图的「深色裹边」观感
    ctx.strokeStyle = COL.riverCase;
    for (const [w, p] of G.riverBuckets){
      ctx.lineWidth = Math.max(1.0/V.scale, w + 1.5);
      ctx.stroke(p);
    }
    ctx.strokeStyle = COL.river;
    for (const [w, p] of G.riverBuckets){
      ctx.lineWidth = Math.max(0.8/V.scale, w);
      ctx.stroke(p);
    }
  }
  if (L.sea){
    ctx.strokeStyle = COL.coast; ctx.lineWidth = Math.max(0.7/V.scale, 1.1);
    ctx.stroke(G.coast);
  }

  ctx.setTransform(dpr,0,0,dpr,0,0);

  if (L.region){
    ctx.font = '12px "Songti SC","SimSun",serif';
    ctx.textBaseline = 'middle';
    for (const r of REGIONS){
      const [sx,sy] = w2s(r.x, r.y);
      if (sx < -60 || sy < -20 || sx > cw+60 || sy > ch+20) continue;
      ctx.globalAlpha = .75;
      ctx.beginPath(); ctx.arc(sx, sy, 3.0, 0, 6.283);
      ctx.fillStyle = COL.region; ctx.fill();
      ctx.globalAlpha = 1;
      ctx.fillStyle = 'rgba(120,66,44,.85)';
      ctx.fillText(r.name, sx+7, sy+1);
    }
  }

  if (L.city){
    for (const c of CITIES){
      const [sx,sy] = w2s(c.x, c.y);
      if (sx < -10 || sy < -10 || sx > cw+10 || sy > ch+10) continue;
      if (c.kind === '都'){
        ctx.beginPath(); ctx.arc(sx, sy, 4.4, 0, 6.283);
        ctx.fillStyle = COL.du; ctx.fill();
        ctx.beginPath(); ctx.arc(sx, sy, 6.8, 0, 6.283);
        ctx.strokeStyle = 'rgba(139,46,30,.55)'; ctx.lineWidth = 1.1; ctx.stroke();
      } else if (c.kind === '城'){
        ctx.beginPath(); ctx.arc(sx, sy, 2.9, 0, 6.283);
        ctx.fillStyle = COL.cheng; ctx.fill();
        ctx.strokeStyle = 'rgba(246,238,216,.85)'; ctx.lineWidth = .7; ctx.stroke();
      } else {
        ctx.beginPath(); ctx.arc(sx, sy, 1.5, 0, 6.283);
        ctx.fillStyle = COL.yi; ctx.globalAlpha = .92; ctx.fill(); ctx.globalAlpha = 1;
      }
    }
  }

  if (L.label) drawLabels(L);

  if (hoverCity){
    const [sx,sy] = w2s(hoverCity.x, hoverCity.y);
    ctx.beginPath(); ctx.arc(sx, sy, 8.5, 0, 6.283);
    ctx.strokeStyle = 'rgba(139,46,30,.8)'; ctx.lineWidth = 1.6; ctx.stroke();
  }
  if (flash){
    const [sx,sy] = w2s(flash.x, flash.y);
    const t = (performance.now() - flash.t) / 1000;
    if (t < 1){
      ctx.beginPath(); ctx.arc(sx, sy, 10 + 30*t, 0, 6.283);
      ctx.strokeStyle = 'rgba(139,46,30,' + (0.8*(1-t)).toFixed(3) + ')';
      ctx.lineWidth = 2; ctx.stroke();
      requestAnimationFrame(draw);
    } else flash = null;
  }
  zoomEl.textContent = '缩放 ' + (V.scale*100).toFixed(0) + '%';
}

function drawLabels(L){
  const showYi = V.scale > 0.30;
  const fs = V.scale > 0.62 ? 13 : 12;
  ctx.font = fs + 'px "Songti SC","SimSun",serif';
  ctx.textBaseline = 'middle';
  const CELL = 96, grid = new Map();
  const overlap = (x,y,w,h) => {
    const gx = Math.floor(x/CELL), gy = Math.floor(y/CELL);
    for (let i=gx-1;i<=gx+1;i++) for (let j=gy-1;j<=gy+1;j++){
      const arr = grid.get(i+'|'+j); if (!arr) continue;
      for (const b of arr) if (x < b[0]+b[2] && x+w > b[0] && y < b[1]+b[3] && y+h > b[1]) return true;
    }
    return false;
  };
  const push = (x,y,w,h) => {
    const k = Math.floor(x/CELL)+'|'+Math.floor(y/CELL);
    if (!grid.has(k)) grid.set(k, []);
    grid.get(k).push([x,y,w,h]);
  };
  const rank = {'都':0, '城':1, '邑':2};
  const list = CITIES.slice().sort((a,b)=> (rank[a.kind]-rank[b.kind]) || (b.pop-a.pop));
  for (const c of list){
    if (c.kind === '邑' && !showYi) continue;
    const [sx,sy] = w2s(c.x, c.y);
    if (sx < -70 || sy < -24 || sx > cw+10 || sy > ch+24) continue;
    const pad = c.kind === '邑' ? 5 : 7;
    const w = ctx.measureText(c.name).width;
    const h = fs + 2;
    const x = sx + pad, y = sy - h/2;
    if (overlap(x, y, w, h)) continue;
    push(x, y, w, h);
    ctx.lineWidth = 3.2;
    ctx.strokeStyle = COL.halo;
    ctx.strokeText(c.name, x, sy);
    ctx.fillStyle = c.kind === '都' ? '#571c12' : (c.kind === '城' ? '#3b2918' : '#5c4934');
    ctx.fillText(c.name, x, sy);
  }
}

// ---------- 交互 ----------
let dragging = false, last = null;
cv.addEventListener('pointerdown', e => {
  dragging = true; last = [e.clientX, e.clientY];
  cv.classList.add('drag');
  try { cv.setPointerCapture(e.pointerId); } catch(_){}
});
cv.addEventListener('pointerup', () => { dragging = false; cv.classList.remove('drag'); last = null; });
cv.addEventListener('pointerleave', () => { tip.style.opacity = 0; hoverCity = null; draw(); });

cv.addEventListener('pointermove', e => {
  if (dragging && last){
    V.tx += e.clientX - last[0]; V.ty += e.clientY - last[1];
    last = [e.clientX, e.clientY];
    draw(); return;
  }
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
    const [sx,sy] = w2s(best.x, best.y);
    tip.style.opacity = 1;
    tip.style.left = (r.left + sx) + 'px';
    tip.style.top = (r.top + sy) + 'px';
    tip.textContent = best.name + ' · ' + best.kind + ' · ' + best.pop + ' 万';
  } else tip.style.opacity = 0;
});

cv.addEventListener('wheel', e => {
  e.preventDefault();
  const r = cv.getBoundingClientRect();
  const mx = e.clientX - r.left, my = e.clientY - r.top;
  zoomAt(mx, my, Math.exp(-e.deltaY * 0.0016));
}, {passive:false});

cv.addEventListener('dblclick', e => {
  const r = cv.getBoundingClientRect();
  zoomAt(e.clientX - r.left, e.clientY - r.top, 1.7);
});

function zoomAt(mx, my, k){
  const wx = (mx - V.tx)/V.scale, wy = (my - V.ty)/V.scale;
  V.scale = Math.max(0.05, Math.min(9, V.scale * k));
  V.tx = mx - wx*V.scale; V.ty = my - wy*V.scale;
  draw();
}

function flyTo(c){
  V.scale = Math.max(V.scale, 0.6);
  V.tx = cw/2 - c.x*V.scale; V.ty = ch/2 - c.y*V.scale;
  flash = {x:c.x, y:c.y, t:performance.now()};
  draw();
}

el('bFit').onclick = fit;
el('bIn').onclick = () => zoomAt(cw/2, ch/2, 1.35);
el('bOut').onclick = () => zoomAt(cw/2, ch/2, 1/1.35);
for (const id of ['lSea','lLake','lRiver','lCity','lLabel','lRegion'])
  el(id).addEventListener('change', draw);

const q = el('q'), hits = el('hits');
q.addEventListener('keydown', e => {
  if (e.key !== 'Enter') return;
  const kw = q.value.trim();
  if (!kw){ hits.textContent = ''; return; }
  const fc = CITIES.filter(c => c.name.indexOf(kw) >= 0);
  const fr = REGIONS.filter(r => r.name.indexOf(kw) >= 0);
  const all = fc.concat(fr);
  if (!all.length){ hits.textContent = '无匹配'; return; }
  hits.textContent = '命中 ' + all.length + '：' + all.slice(0,6).map(c=>c.name).join('、');
  flyTo(all[0]);
});

window.addEventListener('keydown', e => {
  if (e.target === q) return;
  if (e.key === '+' || e.key === '=') zoomAt(cw/2, ch/2, 1.35);
  if (e.key === '-') zoomAt(cw/2, ch/2, 1/1.35);
  if (e.key === '0') fit();
});
window.addEventListener('resize', resize);

resize(); fit();
el('foot').textContent =
  '河 ' + DATA.rivers.length + ' 段 · 湖 ' + DATA.lakes.length + ' 处 · 城邑 ' + CITIES.length +
  ' 座 · 部族 ' + REGIONS.length + '　｜　滚轮缩放 · 拖拽平移 · 双击放大';
</script>
</body>
</html>
"""

OUTDIR.mkdir(parents=True, exist_ok=True)
OUT.write_text(HTML.replace("__DATA__", payload), encoding="utf-8")
print(f"written {OUT}  {OUT.stat().st_size/1024:.0f} KB")
