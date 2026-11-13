# -*- coding: utf-8 -*-
"""人口编辑器 v2：点选放宽、框选修正、新增「涂色选区」。"""
import csv
import json
from pathlib import Path

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
OUT = ROOT / "data" / "map" / "review" / "pop_editor.html"
W, H = 9101, 8509

items = []
for r in csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")):
    items.append({"id": r["id"], "name": r["name"], "kind": r["kind"],
                  "x": float(r["x"]), "y": float(r["y"]), "pop": float(r["pop"])})
for r in csv.DictReader((ROOT / "data" / "map" / "regions.csv").open(encoding="utf-8-sig")):
    items.append({"id": r["id"], "name": r["name"], "kind": "部族",
                  "x": float(r["x"]), "y": float(r["y"]), "pop": float(r["pop"])})

TPL = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>战国演义 · 人口编辑</title>
<style>
  *{box-sizing:border-box}
  html,body{margin:0;height:100%;overflow:hidden;font-family:"Microsoft YaHei UI",sans-serif;
    background:#141517;color:#e8e8e8}
  #wrap{display:flex;height:100%}
  #left{position:relative;flex:1;min-width:0;background:#000}
  #vp{position:absolute;inset:0;overflow:hidden}
  #world{position:absolute;left:0;top:0;width:W_PXpx;height:H_PXpx;transform-origin:0 0}
  #world img{position:absolute;left:0;top:0;width:W_PXpx;height:H_PXpx;user-select:none;-webkit-user-drag:none}
  #paint{position:absolute;inset:0;pointer-events:none;z-index:8}
  body.painting #paint{pointer-events:auto;cursor:crosshair}
  .mk{position:absolute;border-radius:50%;box-sizing:border-box;transform:translate(-50%,-50%);
    pointer-events:none}
  .mk.邑{border:2px solid #1f9d3a} .mk.城{border:3px solid #d98200}
  .mk.都{border:3px solid #d02020} .mk.部族{border:2px dashed #8e5bd0}
  .mk.sel{box-shadow:0 0 0 3px #ffe066,0 0 12px #ffe066}
  .lb{position:absolute;transform:translate(-50%,0);font-size:13px;line-height:1;
    padding:2px 4px;border-radius:3px;background:rgba(255,255,255,.88);color:#1b1b1b;
    white-space:nowrap;pointer-events:none;font-variant-numeric:tabular-nums;
    box-shadow:0 0 0 1px rgba(0,0,0,.12)}
  .lb.big{color:#b00000;font-weight:700}
  body.hide-lb .lb{display:none}
  #bar{position:absolute;left:12px;top:12px;z-index:20;background:rgba(20,21,23,.93);
    border:1px solid #333;padding:8px 12px;border-radius:6px;font-size:12px;line-height:2;color:#bbb}
  #bar b{color:#7dd3a0}
  #bar button{padding:4px 10px;font-size:12px;border-radius:5px;border:1px solid #3a3d44;
    background:#2a2d33;color:#dfe;cursor:pointer;font-family:inherit;margin-right:6px}
  #bar button.on{background:#1f4fd8;border-color:#2f63ff;color:#fff}
  #brush{width:110px;vertical-align:middle}
  #right{width:360px;flex:none;background:#1c1e22;border-left:1px solid #333;padding:14px;
    display:flex;flex-direction:column;gap:10px;overflow:auto}
  h1{font-size:15px;margin:0;color:#fff}
  .box{background:#24262b;border:1px solid #333;border-radius:6px;padding:10px}
  .k{color:#8a8d91;font-size:12px}
  .v{font-size:20px;font-weight:700;color:#fff;font-variant-numeric:tabular-nums}
  .row{display:flex;gap:6px;margin-top:6px}
  button{padding:8px 4px;border-radius:6px;border:1px solid #3a3d44;background:#2a2d33;
    color:#e8e8e8;cursor:pointer;font-family:inherit;font-size:13px;flex:1}
  button:hover{background:#343841}
  button.up{border-color:#2f6f45;color:#9ee6b8} button.dn{border-color:#7a3b3b;color:#f0a8a8}
  button.pri{background:#1f4fd8;border-color:#2f63ff}
  #input{width:100%;font-size:18px;padding:8px;border-radius:6px;border:2px solid #3d6cff;
    background:#0f1115;color:#fff;font-family:inherit;outline:none}
  #list{flex:1;overflow:auto;border-top:1px solid #333;margin-top:4px;padding-top:6px}
  .it{display:flex;justify-content:space-between;padding:3px 4px;font-size:12px;color:#bbb;
    border-radius:3px;cursor:pointer}
  .it:hover{background:#26282d} .it.sel{background:#3a3320;color:#ffe066}
</style></head>
<body>
<div id="wrap">
  <div id="left">
    <div id="vp">
      <div id="world"><img src="../../../ditu.png" alt="map"><div id="mks"></div></div>
    </div>
    <canvas id="paint"></canvas>
    <div id="bar">
      <button id="mSel" class="on" onclick="setMode('sel')">选择</button>
      <button id="mPaint" onclick="setMode('paint')">涂色</button>
      笔刷 <input type="range" id="brush" min="10" max="140" value="46">
      <span id="bs">46</span>
      <button onclick="detectPaint()">检测涂色</button>
      <button onclick="clearPaint()">清除涂色</button><br>
      <b>左键</b>选择/框选 · <b>右键/中键拖</b>平移 · <b>滚轮</b>缩放 · <b>空格</b>复位<br>
      总计 <b id="tot"></b> 万　<label><input type="checkbox" id="clb" checked> 标签</label>
    </div>
  </div>
  <div id="right">
    <h1>人口编辑</h1>
    <div class="box">
      <div class="k">已选 <span id="cnt">0</span> 个，合计</div>
      <div class="v"><span id="sel">0</span> 万</div>
    </div>
    <div class="row"><button class="up" onclick="adj(1.1)">+10%</button>
      <button class="up" onclick="adj(1.2)">+20%</button>
      <button class="up" onclick="adj(1.5)">+50%</button></div>
    <div class="row"><button class="dn" onclick="adj(0.9)">−10%</button>
      <button class="dn" onclick="adj(0.8)">−20%</button>
      <button class="dn" onclick="adj(0.5)">−50%</button></div>
    <div class="box">
      <div class="k">直接设定（仅选中一个时）</div>
      <input id="input" placeholder="输入人口（万），回车">
    </div>
    <div class="row"><button onclick="undo()">撤销</button>
      <button onclick="selNone()">取消选择</button></div>
    <div class="row"><button class="pri" onclick="exportCSV()">导出 CSV</button>
      <button onclick="resetAll()">恢复初始</button></div>
    <div id="list"></div>
  </div>
</div>
<script>
const DATA = __DATA__;
const KEY = "zg_pop_v2";
const init = JSON.parse(JSON.stringify(DATA));
let items = DATA;
try { const s = localStorage.getItem(KEY); if (s) items = JSON.parse(s); } catch(e) {}
const sel = new Set();
let hist = [];
let z = 1.2, tx = 0, ty = 0, mode = "sel";

const vp = document.getElementById("vp"), world = document.getElementById("world");
const mks = document.getElementById("mks"), inp = document.getElementById("input");
const cv = document.getElementById("paint"), ctx = cv.getContext("2d");
const RAD = { "都": 9, "城": 6, "邑": 4.5, "部族": 7 };
const byId = {};
items.forEach(it => byId[it.id] = it);

function fmtPop(p) { return p >= 10 ? p.toFixed(0) : (p < 1 ? p.toFixed(2) : p.toFixed(1)); }
function apply() {
  world.style.transform = `translate(${tx}px,${ty}px) scale(${z})`;
  document.body.classList.toggle("hide-lb", z < 0.55 || !document.getElementById("clb").checked);
}
function center(x, y, zz) { if (zz) z = zz; tx = vp.clientWidth/2 - x*z; ty = vp.clientHeight/2 - y*z; apply(); }
function toScreen(x, y) { return [x*z + tx, y*z + ty]; }

function build() {
  mks.innerHTML = "";
  const frag = document.createDocumentFragment();
  for (const it of items) {
    const r = RAD[it.kind] || 4.5;
    const d = document.createElement("div");
    d.className = "mk " + it.kind;
    d.style.left = it.x + "px"; d.style.top = it.y + "px";
    d.style.width = (r*2) + "px"; d.style.height = (r*2) + "px";
    frag.appendChild(d);
    const l = document.createElement("div");
    l.className = "lb";
    l.style.left = it.x + "px"; l.style.top = (it.y + r + 2) + "px";
    frag.appendChild(l);
    it._mk = d; it._lb = l;
  }
  mks.appendChild(frag);
  paintState();
}

function paintState() {
  let tot = 0, s = 0;
  for (const it of items) {
    tot += it.pop;
    if (sel.has(it.id)) s += it.pop;
    it._mk.classList.toggle("sel", sel.has(it.id));
    it._lb.textContent = fmtPop(it.pop);
    it._lb.classList.toggle("big", it.pop >= 25);
  }
  document.getElementById("tot").textContent = tot.toFixed(0);
  document.getElementById("sel").textContent = s.toFixed(1);
  document.getElementById("cnt").textContent = sel.size;
  const box = document.getElementById("list");
  const arr = [...sel].map(id => byId[id]).filter(Boolean).slice(0, 300);
  box.innerHTML = arr.map(it =>
    `<div class="it sel"><span>${it.name} <span class="k">${it.kind}</span></span><span>${fmtPop(it.pop)}</span></div>`
  ).join("") || '<div class="k" style="padding:6px">未选中</div>';
}

function snapshot() { hist.push(items.map(i => i.pop)); if (hist.length > 50) hist.shift(); }
function undo() { if (!hist.length) return; const p = hist.pop(); items.forEach((it,i)=>it.pop=p[i]); save(); paintState(); }
function adj(k) { if (!sel.size) return; snapshot();
  for (const id of sel) { const it = byId[id]; it.pop = Math.max(0, Math.round(it.pop*k*100)/100); }
  save(); paintState(); }
function selNone() { sel.clear(); paintState(); }

inp.addEventListener("keydown", e => {
  if (e.key !== "Enter") return;
  const v = parseFloat(inp.value);
  if (isNaN(v) || v < 0) return;
  if (sel.size !== 1) { alert("请只选中一个"); return; }
  snapshot(); byId[[...sel][0]].pop = Math.round(v*100)/100;
  inp.value = ""; save(); paintState();
});

function save() { try { localStorage.setItem(KEY, JSON.stringify(items.map(({_mk,_lb,...r})=>r))); } catch(e) {} }
function resetAll() { if (!confirm("恢复到打开时？")) return; snapshot();
  items.forEach((it,i)=>it.pop=init[i].pop); save(); paintState(); }

function exportCSV() {
  const rows = [["id","name","kind","x","y","pop"]];
  items.forEach(it => rows.push([it.id, it.name, it.kind, it.x, it.y, it.pop.toFixed(2)]));
  const csv = "\ufeff" + rows.map(r=>r.join(",")).join("\r\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"}));
  a.download = "pop_filled.csv"; a.click(); URL.revokeObjectURL(a.href);
}

/* ---------- 最近点命中 ---------- */
function nearest(px, py) {
  let best = null, bd = 24*24;
  for (const it of items) {
    const s = toScreen(it.x, it.y);
    const d = (s[0]-px)*(s[0]-px) + (s[1]-py)*(s[1]-py);
    if (d < bd) { bd = d; best = it; }
  }
  return best;
}

/* ---------- 模式 & 画布 ---------- */
function setMode(m) {
  mode = m;
  document.body.classList.toggle("painting", m === "paint");
  document.getElementById("mSel").classList.toggle("on", m === "sel");
  document.getElementById("mPaint").classList.toggle("on", m === "paint");
}
document.getElementById("brush").oninput = e => document.getElementById("bs").textContent = e.target.value;

function fitCanvas() { cv.width = vp.clientWidth; cv.height = vp.clientHeight; }
window.addEventListener("resize", fitCanvas);
function clearPaint() { ctx.clearRect(0,0,cv.width,cv.height); }

function detectPaint() {
  const w = cv.width, h = cv.height;
  const d = ctx.getImageData(0,0,w,h).data;
  sel.clear();
  let hit = 0;
  for (const it of items) {
    const s = toScreen(it.x, it.y);
    const x = Math.round(s[0]), y = Math.round(s[1]);
    if (x < 0 || y < 0 || x >= w || y >= h) continue;
    if (d[(y*w + x)*4 + 3] > 8) { sel.add(it.id); hit++; }
  }
  paintState();
  return hit;
}

/* ---------- 交互 ---------- */
let dragging = false, panning = false, painting = false, sx = 0, sy = 0, boxEl = null, base = null, lastPt = null;

vp.addEventListener("mousedown", e => {
  if (e.button === 1 || e.button === 2 || e.altKey) {
    panning = true; sx = e.clientX; sy = e.clientY; e.preventDefault(); return;
  }
  const r = vp.getBoundingClientRect();
  const px = e.clientX - r.left, py = e.clientY - r.top;
  const it = nearest(px, py);
  if (it) {
    if (!e.shiftKey) sel.clear();
    if (sel.has(it.id) && e.shiftKey) sel.delete(it.id); else sel.add(it.id);
    paintState(); return;
  }
  dragging = true; base = new Set(sel); sx = px; sy = py;
  boxEl = document.createElement("div");
  boxEl.style.cssText = "position:absolute;border:1px solid #ffe066;background:rgba(255,224,102,.15);pointer-events:none;z-index:12";
  boxEl.style.left = px+"px"; boxEl.style.top = py+"px";
  vp.appendChild(boxEl);
  if (!e.shiftKey) { sel.clear(); base.clear(); paintState(); }
});

window.addEventListener("mousemove", e => {
  if (panning) { tx += e.clientX - sx; ty += e.clientY - sy; sx = e.clientX; sy = e.clientY; apply(); return; }
  if (!dragging || !boxEl) return;
  const r = vp.getBoundingClientRect();
  const px = e.clientX - r.left, py = e.clientY - r.top;
  const x0 = Math.min(sx,px), y0 = Math.min(sy,py), w = Math.abs(px-sx), h = Math.abs(py-sy);
  boxEl.style.left = x0+"px"; boxEl.style.top = y0+"px";
  boxEl.style.width = w+"px"; boxEl.style.height = h+"px";
  const wx0=(x0-tx)/z, wy0=(y0-ty)/z, wx1=(x0+w-tx)/z, wy1=(y0+h-ty)/z;
  sel.clear(); for (const id of base) sel.add(id);
  for (const it of items)
    if (it.x>=wx0 && it.x<=wx1 && it.y>=wy0 && it.y<=wy1) sel.add(it.id);
  paintState();
});

window.addEventListener("mouseup", () => {
  if (painting) { painting = false; detectPaint(); }
  panning = false;
  if (boxEl) { boxEl.remove(); boxEl = null; }
  dragging = false;
});

cv.addEventListener("mousedown", e => {
  if (e.button !== 0) return;
  e.preventDefault(); e.stopPropagation();
  painting = true; lastPt = null;
  const r = cv.getBoundingClientRect();
  paintTo(e.clientX - r.left, e.clientY - r.top);
});
function paintTo(x, y) {
  const b = +document.getElementById("brush").value;
  ctx.strokeStyle = "rgba(255,190,40,0.45)";
  ctx.fillStyle = "rgba(255,190,40,0.45)";
  ctx.lineWidth = b; ctx.lineCap = "round"; ctx.lineJoin = "round";
  if (lastPt) {
    ctx.beginPath(); ctx.moveTo(lastPt[0], lastPt[1]); ctx.lineTo(x, y); ctx.stroke();
  } else {
    ctx.beginPath(); ctx.arc(x, y, b/2, 0, Math.PI*2); ctx.fill();
  }
  lastPt = [x, y];
}
cv.addEventListener("mousemove", e => {
  if (!painting) return;
  const r = cv.getBoundingClientRect();
  paintTo(e.clientX - r.left, e.clientY - r.top);
});
cv.addEventListener("mouseup", () => { if (painting) { painting = false; detectPaint(); } });

vp.addEventListener("contextmenu", e => e.preventDefault());
vp.addEventListener("wheel", e => {
  e.preventDefault();
  const r = vp.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top;
  const nz = Math.min(6, Math.max(0.12, z * (e.deltaY < 0 ? 1.15 : 1/1.15)));
  tx = mx - (mx-tx)*(nz/z); ty = my - (my-ty)*(nz/z); z = nz; apply();
}, { passive: false });

document.getElementById("clb").onchange = e => document.body.classList.toggle("hide-lb", !e.target.checked);
window.addEventListener("keydown", e => {
  if (document.activeElement === inp) return;
  if ((e.ctrlKey||e.metaKey) && e.key.toLowerCase()==="z") { e.preventDefault(); undo(); }
  if (e.key === " ") { e.preventDefault(); center(5000,3700,1.2); }
  if (e.key === "Escape") selNone();
});

fitCanvas(); build(); center(5000,3700,1.2); paintState();
</script></body></html>"""

html = TPL.replace("__DATA__", json.dumps(items, ensure_ascii=False)) \
          .replace("W_PX", str(W)).replace("H_PX", str(H))
OUT.write_text(html, encoding="utf-8")
print("items", len(items), "->", OUT, round(OUT.stat().st_size / 1024), "KB")
