# -*- coding: utf-8 -*-
"""全量地名勘误器：1040 个城邑逐个过，回车即确认。"""
import csv
import json
from pathlib import Path

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
OUT = ROOT / "data" / "map" / "review" / "names.html"
W, H = 9101, 8509

items = []
for r in csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")):
    items.append({"id": r["id"], "name": r["name"], "kind": r["kind"],
                  "x": float(r["x"]), "y": float(r["y"])})

TPL = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>地名勘误（全量）</title>
<style>
  *{box-sizing:border-box}
  html,body{margin:0;height:100%;overflow:hidden;font-family:"Microsoft YaHei UI",sans-serif;
    background:#141517;color:#e8e8e8}
  #wrap{display:flex;height:100%}
  #left{position:relative;flex:1;min-width:0;background:#000}
  #vp{position:absolute;inset:0;overflow:hidden;cursor:grab}
  #vp.drag{cursor:grabbing}
  #world{position:absolute;left:0;top:0;width:W_PXpx;height:H_PXpx;transform-origin:0 0}
  #world img{position:absolute;left:0;top:0;width:W_PXpx;height:H_PXpx;user-select:none;-webkit-user-drag:none}
  #ring{position:absolute;border:3px solid #ff2d2d;border-radius:50%;
    box-shadow:0 0 0 4px rgba(255,45,45,.22);pointer-events:none}
  #hint{position:absolute;left:12px;bottom:10px;font-size:12px;color:#aaa;
    background:rgba(0,0,0,.55);padding:4px 8px;border-radius:4px}
  #right{width:380px;flex:none;background:#1c1e22;border-left:1px solid #333;padding:14px;
    display:flex;flex-direction:column;gap:10px;overflow:auto}
  h1{font-size:15px;margin:0;color:#fff}
  #prog{font-size:13px;color:#7dd3a0}
  #bar{height:6px;background:#2a2d33;border-radius:3px;overflow:hidden}
  #barin{height:100%;width:0;background:#2f63ff;transition:width .2s}
  #meta{font-size:13px;color:#cfcfcf;background:#26282d;padding:10px;border-radius:6px;line-height:1.8}
  #meta b{color:#fff;font-size:18px}
  #ans{width:100%;font-size:26px;padding:10px;border-radius:6px;border:2px solid #3d6cff;
    background:#0f1115;color:#fff;font-family:inherit;outline:none;text-align:center}
  #ans:focus{border-color:#68a0ff;box-shadow:0 0 0 3px rgba(61,108,255,.25)}
  .row{display:flex;gap:8px}
  button{flex:1;padding:9px 4px;border-radius:6px;border:1px solid #3a3d44;background:#2a2d33;
    color:#e8e8e8;cursor:pointer;font-family:inherit;font-size:13px}
  button:hover{background:#343841}
  button.pri{background:#1f4fd8;border-color:#2f63ff}
  #list{flex:1;overflow:auto;border-top:1px solid #333;margin-top:4px;padding-top:6px}
  .it{display:flex;justify-content:space-between;padding:3px 5px;font-size:12px;color:#bbb;
    border-radius:3px;cursor:pointer}
  .it:hover{background:#26282d} .it.cur{background:#2b3b6b;color:#fff}
  .it.done{color:#7dd3a0}
</style></head>
<body>
<div id="wrap">
  <div id="left">
    <div id="vp"><div id="world"><img src="../../../ditu.png" alt="map"><div id="ring"></div></div></div>
    <div id="hint">滚轮缩放 · 拖动平移 · 空格复位 · Esc 取消选择</div>
  </div>
  <div id="right">
    <h1>地名勘误（全量）</h1>
    <div id="prog"></div>
    <div id="bar"><div id="barin"></div></div>
    <div id="meta"></div>
    <input id="ans" autocomplete="off">
    <div class="row">
      <button class="pri" onclick="confirmAns()">确认 (Enter)</button>
      <button onclick="skip()">跳过 (→)</button>
    </div>
    <div class="row">
      <button onclick="prev()">← 上一题</button>
      <button onclick="jumpFix()">跳到下一处未确认</button>
    </div>
    <div class="row">
      <button onclick="exportCSV()">导出 CSV</button>
      <button onclick="resetAll()">重置进度</button>
    </div>
    <div id="list"></div>
  </div>
</div>
<script>
const DATA = __DATA__;
const KEY = "zg_names_v1";
let answers = {};   // id -> 名字
let done = {};      // id -> true 表示确认过
try {
  const a = localStorage.getItem(KEY); if (a) answers = JSON.parse(a);
  const d = localStorage.getItem(KEY + "_d"); if (d) done = JSON.parse(d);
} catch(e) {}
let idx = parseInt(localStorage.getItem(KEY + "_i") || "0");
if (isNaN(idx) || idx < 0 || idx >= DATA.length) idx = 0;

const vp = document.getElementById("vp"), world = document.getElementById("world");
const ring = document.getElementById("ring"), ansEl = document.getElementById("ans");
let z = 2.4, tx = 0, ty = 0, dragging = false, lx = 0, ly = 0;

function apply() { world.style.transform = `translate(${tx}px,${ty}px) scale(${z})`; }
function center(x, y, zz) { if (zz) z = zz; tx = vp.clientWidth/2 - x*z; ty = vp.clientHeight/2 - y*z; apply(); }

function cur() { return DATA[idx]; }
function val(it) { return answers[it.id] !== undefined ? answers[it.id] : it.name; }

function render() {
  const d = cur();
  ring.style.left = (d.x - 26) + "px"; ring.style.top = (d.y - 26) + "px";
  ring.style.width = "52px"; ring.style.height = "52px";
  center(d.x, d.y, z);
  const n = Object.keys(done).length;
  document.getElementById("prog").textContent = `第 ${idx+1} / ${DATA.length} · 已确认 ${n}`;
  document.getElementById("barin").style.width = (n / DATA.length * 100) + "%";
  document.getElementById("meta").innerHTML =
    `<b>${d.id}</b> · ${d.kind}` + (done[d.id] ? ' · <span style="color:#7dd3a0">已确认</span>' : '') +
    `<br>图上原字请看红圈处`;
  ansEl.value = val(d);
  ansEl.focus(); ansEl.select();
  renderList();
}

function renderList() {
  const box = document.getElementById("list");
  const start = Math.max(0, idx - 5);
  const part = DATA.slice(start, start + 60);
  box.innerHTML = part.map((it, k) => {
    const i = start + k;
    const v = val(it);
    return `<div class="it ${i===idx?'cur':''} ${done[it.id]?'done':''}" onclick="go(${i})">
      <span>${it.id} ${it.kind}</span><span>${v||'⌀'}</span></div>`;
  }).join("");
  const c = box.querySelector(".cur"); if (c) c.scrollIntoView({block:"center"});
}

function go(i) { idx = Math.max(0, Math.min(DATA.length-1, i)); save(); render(); }
function save() {
  try {
    localStorage.setItem(KEY, JSON.stringify(answers));
    localStorage.setItem(KEY + "_d", JSON.stringify(done));
    localStorage.setItem(KEY + "_i", String(idx));
  } catch(e) {}
}

function confirmAns() {
  const d = cur();
  const v = ansEl.value.trim();
  if (v) answers[d.id] = v;
  done[d.id] = true;
  idx = Math.min(idx + 1, DATA.length - 1);
  save(); render();
}
function skip() { idx = Math.min(idx + 1, DATA.length - 1); save(); render(); }
function prev() { idx = Math.max(idx - 1, 0); save(); render(); }
function jumpFix() {
  for (let i = idx + 1; i < DATA.length; i++) if (!done[DATA[i].id]) { go(i); return; }
  for (let i = 0; i < DATA.length; i++) if (!done[DATA[i].id]) { go(i); return; }
  alert("全部确认完毕");
}
function resetAll() {
  if (!confirm("清空所有确认与修改？")) return;
  answers = {}; done = {}; idx = 0; save(); render();
}

function exportCSV() {
  const rows = [["id","name","kind","x","y","original","confirmed"]];
  DATA.forEach(it => rows.push([it.id, val(it), it.kind, it.x, it.y, it.name, done[it.id] ? 1 : 0]));
  const csv = "\ufeff" + rows.map(r => r.join(",")).join("\r\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"}));
  a.download = "names_filled.csv"; a.click(); URL.revokeObjectURL(a.href);
}

ansEl.addEventListener("keydown", e => {
  if (e.isComposing) return;
  if (e.key === "Enter") { e.preventDefault(); confirmAns(); }
});
window.addEventListener("keydown", e => {
  if (document.activeElement === ansEl) return;
  if (e.key === "ArrowRight") skip();
  if (e.key === "ArrowLeft") prev();
  if (e.key === " ") { e.preventDefault(); const d = cur(); center(d.x, d.y, z); }
});

vp.addEventListener("mousedown", e => { dragging = true; lx = e.clientX; ly = e.clientY; vp.classList.add("drag"); });
window.addEventListener("mouseup", () => { dragging = false; vp.classList.remove("drag"); });
window.addEventListener("mousemove", e => {
  if (!dragging) return;
  tx += e.clientX - lx; ty += e.clientY - ly; lx = e.clientX; ly = e.clientY; apply();
});
vp.addEventListener("wheel", e => {
  e.preventDefault();
  const r = vp.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top;
  const nz = Math.min(8, Math.max(0.4, z * (e.deltaY < 0 ? 1.15 : 1/1.15)));
  tx = mx - (mx-tx)*(nz/z); ty = my - (my-ty)*(nz/z); z = nz; apply();
}, { passive: false });
window.addEventListener("resize", () => { const d = cur(); center(d.x, d.y, z); });

render();
</script></body></html>"""

html = TPL.replace("__DATA__", json.dumps(items, ensure_ascii=False)) \
          .replace("W_PX", str(W)).replace("H_PX", str(H))
OUT.write_text(html, encoding="utf-8")
print("items", len(items), "->", OUT, round(OUT.stat().st_size / 1024), "KB")
