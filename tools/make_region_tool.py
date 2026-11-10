# -*- coding: utf-8 -*-
"""生成部族识别台（一题一屏）。镜头放大到能看清虚线圈的程度。"""
import csv
import json
from pathlib import Path

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
OUT = ROOT / "data" / "map" / "review" / "regions.html"
W, H = 9101, 8509

rows = list(csv.DictReader((ROOT / "data" / "map" / "regions.csv").open(encoding="utf-8-sig")))
data = [{"id": r["id"], "x": float(r["x"]), "y": float(r["y"]), "guess": r.get("note", "")} for r in rows]
payload = json.dumps(data, ensure_ascii=False)

html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>部族识别台</title>
<style>
  *{{box-sizing:border-box}}
  html,body{{margin:0;height:100%;overflow:hidden;font-family:"Microsoft YaHei UI",sans-serif;
    background:#141517;color:#e8e8e8}}
  #wrap{{display:flex;height:100%}}
  #left{{position:relative;flex:1;min-width:0;background:#000}}
  #vp{{position:absolute;inset:0;overflow:hidden;cursor:grab}}
  #vp.drag{{cursor:grabbing}}
  #world{{position:absolute;left:0;top:0;width:{W}px;height:{H}px;transform-origin:0 0}}
  #world img{{position:absolute;left:0;top:0;width:{W}px;height:{H}px;user-select:none;-webkit-user-drag:none}}
  #mark{{position:absolute;border:3px dashed #ff2d2d;border-radius:8px;
    box-shadow:0 0 0 3px rgba(255,45,45,.2);pointer-events:none}}
  #hint{{position:absolute;left:12px;bottom:10px;font-size:12px;color:#aaa;
    background:rgba(0,0,0,.55);padding:4px 8px;border-radius:4px}}
  #right{{width:390px;flex:none;background:#1c1e22;border-left:1px solid #333;
    padding:16px;display:flex;flex-direction:column;gap:10px;overflow:auto}}
  h1{{font-size:16px;margin:0;color:#fff}}
  .sub{{font-size:12px;color:#888}}
  #prog{{font-size:13px;color:#7dd3a0}}
  #meta{{font-size:13px;color:#cfcfcf;background:#26282d;padding:8px;border-radius:5px;line-height:1.7}}
  #ans{{width:100%;font-size:24px;padding:10px;border-radius:6px;border:2px solid #3d6cff;
    background:#0f1115;color:#fff;font-family:inherit;outline:none}}
  .row{{display:flex;gap:8px}}
  button{{flex:1;font-size:14px;padding:9px 10px;border-radius:6px;border:1px solid #3a3d44;
    background:#2a2d33;color:#e8e8e8;cursor:pointer;font-family:inherit}}
  button:hover{{background:#343841}}
  button.pri{{background:#1f4fd8;border-color:#2f63ff}}
  #list{{flex:1;overflow:auto;border-top:1px solid #333;margin-top:6px;padding-top:8px}}
  .it{{padding:4px 6px;border-radius:4px;font-size:12px;color:#bbb;cursor:pointer;
    display:flex;justify-content:space-between;gap:8px}}
  .it:hover{{background:#26282d}} .it.cur{{background:#2b3b6b;color:#fff}}
  .it.done{{color:#7dd3a0}}
</style></head>
<body>
<div id="wrap">
  <div id="left">
    <div id="vp"><div id="world">
      <img src="../../../ditu.png" alt="map">
      <div id="mark"></div>
    </div></div>
    <div id="hint">滚轮缩放 · 拖动平移 · 空格回正</div>
  </div>
  <div id="right">
    <h1>部族识别台</h1>
    <div class="sub">镜头已对准该部族名的位置</div>
    <div id="prog"></div>
    <div id="meta"></div>
    <input id="ans" autocomplete="off" placeholder="输入部族名，回车确认">
    <div class="row">
      <button class="pri" onclick="confirmAns()">确认 (Enter)</button>
      <button onclick="skip()">跳过 (→)</button>
    </div>
    <div class="row">
      <button onclick="prev()">← 上一题</button>
      <button onclick="notTribe()">不是部族（删）</button>
    </div>
    <div class="row">
      <button onclick="exportCSV()">导出 CSV</button>
      <button onclick="resetAll()">重置进度</button>
    </div>
    <div id="list"></div>
  </div>
</div>
<script>
const DATA = {payload};
const KEY = "zg_regions_v1";
let answers = JSON.parse(localStorage.getItem(KEY) || "{{}}");
let idx = parseInt(localStorage.getItem(KEY + "_idx") || "0");
if (isNaN(idx) || idx < 0 || idx >= DATA.length) idx = 0;

const vp = document.getElementById("vp"), world = document.getElementById("world");
const mark = document.getElementById("mark"), ansEl = document.getElementById("ans");
let z = 1.5, tx = 0, ty = 0, dragging = false, lx = 0, ly = 0;
function apply() {{ world.style.transform = `translate(${{tx}}px,${{ty}}px) scale(${{z}})`; }}
function center(x, y) {{ tx = vp.clientWidth / 2 - x * z; ty = vp.clientHeight / 2 - y * z; apply(); }}

function render() {{
  const d = DATA[idx];
  mark.style.left = (d.x - 60) + "px"; mark.style.top = (d.y - 40) + "px";
  mark.style.width = "120px"; mark.style.height = "80px";
  center(d.x, d.y);
  document.getElementById("prog").textContent =
    `第 ${{idx + 1}} / ${{DATA.length}} · 已填 ${{Object.keys(answers).length}}`;
  document.getElementById("meta").innerHTML =
    `<b>${{d.id}}</b>` + (d.guess ? `<br>OCR 初判：<b style="color:#ffd166">${{d.guess}}</b>` : `<br>OCR 初判：<span style="color:#888">无</span>`);
  ansEl.value = answers[d.id] !== undefined ? answers[d.id] : "";
  ansEl.focus(); ansEl.select();
  renderList();
}}

function renderList() {{
  const box = document.getElementById("list");
  box.innerHTML = "";
  DATA.forEach((d, i) => {{
    const div = document.createElement("div");
    const v = answers[d.id];
    div.className = "it" + (i === idx ? " cur" : "") + (v ? " done" : "");
    div.innerHTML = `<span>${{d.id}}</span><span>${{v !== undefined ? (v || "（删）") : (d.guess || "")}}</span>`;
    div.onclick = () => {{ idx = i; save(); render(); }};
    box.appendChild(div);
  }});
  const cur = box.querySelector(".cur"); if (cur) cur.scrollIntoView({{ block: "center" }});
}}

function save() {{
  localStorage.setItem(KEY, JSON.stringify(answers));
  localStorage.setItem(KEY + "_idx", String(idx));
}}
function confirmAns() {{
  const v = ansEl.value.trim();
  if (!v) {{ skip(); return; }}
  answers[DATA[idx].id] = v;
  idx = Math.min(idx + 1, DATA.length - 1); save(); render();
}}
function skip() {{ idx = Math.min(idx + 1, DATA.length - 1); save(); render(); }}
function prev() {{ idx = Math.max(idx - 1, 0); save(); render(); }}
function notTribe() {{ answers[DATA[idx].id] = "（删）"; skip(); }}
function resetAll() {{
  if (!confirm("清空所有已填？")) return;
  answers = {{}}; idx = 0; save(); render();
}}
function exportCSV() {{
  const rows = [["id","name","x","y"]];
  DATA.forEach(d => rows.push([d.id, answers[d.id] || "", d.x, d.y]));
  const csv = "\\ufeff" + rows.map(r => r.map(v => {{
    const s = String(v); return /[",\\n]/.test(s) ? '"' + s.replace(/"/g,'""') + '"' : s;
  }}).join(",")).join("\\r\\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], {{ type: "text/csv;charset=utf-8" }}));
  a.download = "regions_filled.csv";
  a.click();
  URL.revokeObjectURL(a.href);
}}

ansEl.addEventListener("keydown", e => {{
  if (e.isComposing) return;
  if (e.key === "Enter") {{ e.preventDefault(); confirmAns(); }}
}});
window.addEventListener("keydown", e => {{
  if (document.activeElement === ansEl) return;
  if (e.key === "ArrowRight") skip();
  if (e.key === "ArrowLeft") prev();
  if (e.key === " ") {{ e.preventDefault(); const d = DATA[idx]; center(d.x, d.y); }}
}});
vp.addEventListener("wheel", e => {{
  e.preventDefault();
  const r = vp.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top;
  const nz = Math.min(6, Math.max(0.4, z * (e.deltaY < 0 ? 1.15 : 1/1.15)));
  tx = mx - (mx - tx) * (nz / z); ty = my - (my - ty) * (nz / z); z = nz; apply();
}}, {{ passive: false }});
vp.addEventListener("mousedown", e => {{ dragging = true; lx = e.clientX; ly = e.clientY; vp.classList.add("drag"); }});
window.addEventListener("mouseup", () => {{ dragging = false; vp.classList.remove("drag"); }});
window.addEventListener("mousemove", e => {{
  if (!dragging) return;
  tx += e.clientX - lx; ty += e.clientY - ly; lx = e.clientX; ly = e.clientY; apply();
}});
window.addEventListener("resize", () => {{ const d = DATA[idx]; center(d.x, d.y); }});
render();
</script></body></html>"""

OUT.write_text(html, encoding="utf-8")
print("regions", len(data), "->", OUT, round(OUT.stat().st_size / 1024), "KB")
