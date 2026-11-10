# -*- coding: utf-8 -*-
"""生成可缩放的地图勘误页（单文件 HTML，无外部依赖）。
打开后：滚轮缩放、按住拖动、复选框切换标签。
"""
import csv
from pathlib import Path

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
OUT = ROOT / "data" / "map" / "review" / "map.html"

rows = list(csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")))
W, H = 9101, 8509

RAD = {"都": 16, "城": 12, "邑": 10}
parts = []
for r in rows:
    x, y = float(r["x"]), float(r["y"])
    name = r["name"]
    n = len(name)
    if n == 0:
        cls, label = "miss", "⌀"
    elif n >= 3:
        cls, label = "long", name
    else:
        cls, label = "ok", name
    rad = RAD[r["kind"]]
    txt = f'{r["id"]} {label}' if cls != "ok" else ""
    parts.append(
        f'<div class="n {cls}" style="left:{x - rad:.0f}px;top:{y - rad:.0f}px;'
        f'width:{rad * 2}px;height:{rad * 2}px" title="{r["id"]} {name or "未识别"}">'
        f'<span>{txt}</span></div>'
    )

html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>战国演义 · 地图勘误</title>
<style>
  html,body{{margin:0;height:100%;background:#111;overflow:hidden;
    font-family:"Microsoft YaHei UI",sans-serif}}
  #vp{{position:absolute;inset:0;overflow:hidden;cursor:grab}}
  #vp.drag{{cursor:grabbing}}
  #world{{position:absolute;left:0;top:0;width:{W}px;height:{H}px;
    transform-origin:0 0;will-change:transform}}
  #world img{{position:absolute;left:0;top:0;width:{W}px;height:{H}px;
    image-rendering:auto;user-select:none;-webkit-user-drag:none}}
  .n{{position:absolute;border-radius:50%;box-sizing:border-box;border:2px solid}}
  .n.ok{{border-color:#0a0}}
  .n.long{{border-color:#c00}}
  .n.miss{{border-color:#e80}}
  .n span{{position:absolute;left:100%;top:-6px;margin-left:6px;white-space:nowrap;
    font-size:22px;line-height:1.15;padding:1px 4px;border-radius:2px;
    background:rgba(255,255,255,.92);border:1px solid #ccc}}
  .n.long span{{color:#c00}} .n.miss span{{color:#c60}}
  body.hide-ok .n.ok span{{display:none}}
  body.hide-all span{{display:none}}
  #bar{{position:absolute;left:12px;top:12px;z-index:10;background:rgba(255,255,255,.95);
    padding:10px 14px;border-radius:6px;font-size:14px;line-height:1.9;
    box-shadow:0 2px 10px rgba(0,0,0,.3)}}
  #bar b{{color:#333}} #bar small{{color:#666}}
  #bar label{{margin-right:14px;cursor:pointer}}
  #pos{{color:#666;font-variant-numeric:tabular-nums}}
</style></head>
<body class="hide-ok">
<div id="vp"><div id="world">
  <img src="../../../ditu.png" alt="map">
  {''.join(parts)}
</div></div>
<div id="bar">
  <b>战国演义 · 地图勘误</b><br>
  <small>滚轮缩放 · 按住拖动 · 双击复位</small><br>
  <label><input type="checkbox" id="c1" checked> 显示待处理标签</label>
  <label><input type="checkbox" id="c2"> 显示全部标签</label><br>
  <span id="pos"></span>
</div>
<script>
const vp=document.getElementById('vp'), world=document.getElementById('world');
let s=0.18, tx=0, ty=0, dragging=false, lx=0, ly=0;
function apply(){{world.style.transform=`translate(${{tx}}px,${{ty}}px) scale(${{s}})`;
  document.getElementById('pos').textContent=`缩放 ${{(s*100).toFixed(0)}}%`;}}
function fit(){{s=Math.min(vp.clientWidth/{W}, vp.clientHeight/{H})*0.98;
  tx=(vp.clientWidth-{W}*s)/2; ty=(vp.clientHeight-{H}*s)/2; apply();}}
vp.addEventListener('wheel',e=>{{
  e.preventDefault();
  const r=vp.getBoundingClientRect();
  const mx=e.clientX-r.left, my=e.clientY-r.top;
  const k=e.deltaY<0?1.15:1/1.15;
  const ns=Math.min(6,Math.max(0.05,s*k));
  tx=mx-(mx-tx)*(ns/s); ty=my-(my-ty)*(ns/s); s=ns; apply();
}},{{passive:false}});
vp.addEventListener('mousedown',e=>{{dragging=true;lx=e.clientX;ly=e.clientY;vp.classList.add('drag');}});
window.addEventListener('mouseup',()=>{{dragging=false;vp.classList.remove('drag');}});
window.addEventListener('mousemove',e=>{{if(!dragging)return;
  tx+=e.clientX-lx; ty+=e.clientY-ly; lx=e.clientX; ly=e.clientY; apply();}});
vp.addEventListener('dblclick',fit);
document.getElementById('c1').onchange=e=>document.body.classList.toggle('hide-ok',!e.target.checked);
document.getElementById('c2').onchange=e=>document.body.classList.toggle('hide-all',e.target.checked);
fit();
</script></body></html>"""

OUT.write_text(html, encoding="utf-8")
from collections import Counter
print("nodes", len(rows), Counter("ok" if 0 < len(r["name"]) <= 2 else ("long" if len(r["name"]) >= 3 else "miss") for r in rows))
print("html", OUT, round(OUT.stat().st_size / 1024), "KB")
