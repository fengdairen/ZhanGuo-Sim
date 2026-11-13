# -*- coding: utf-8 -*-
"""生成可分发的「地名勘误包」：11 个分组 + 全量版 + 自带地图 + 说明。"""
import csv
import json
import shutil
from pathlib import Path

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
PKG = ROOT / "dist" / "map-review"
W, H = 9101, 8509
GROUPS = 11

if PKG.exists():
    shutil.rmtree(PKG)
PKG.mkdir(parents=True)

rows = list(csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")))
items = [{"id": r["id"], "name": r["name"], "kind": r["kind"],
          "x": float(r["x"]), "y": float(r["y"])} for r in rows]
items.sort(key=lambda d: (d["y"], d["x"]))

per = (len(items) + GROUPS - 1) // GROUPS
groups = [items[i * per:(i + 1) * per] for i in range(GROUPS)]
groups = [g for g in groups if g]

shutil.copy2(ROOT / "assets" / "source" / "ditu.png", PKG / "ditu.png")

TPL = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>地名勘误 · __TITLE__</title>
<style>
  *{box-sizing:border-box}
  html,body{margin:0;height:100%;overflow:hidden;font-family:"Microsoft YaHei UI",sans-serif;
    background:#141517;color:#e8e8e8}
  #top{height:132px;background:#1b1d21;border-bottom:2px solid #333;padding:10px 16px;
    display:flex;flex-direction:column;gap:8px}
  #line1{display:flex;align-items:baseline;gap:14px}
  #big{font-size:46px;font-weight:800;color:#fff;line-height:1.05;letter-spacing:2px}
  #big.empty{color:#8a8d91}
  #sub{font-size:13px;color:#9aa0a6}
  #sub b{color:#ffd166}
  #prog{margin-left:auto;font-size:13px;color:#7dd3a0;text-align:right;line-height:1.5}
  #line2{display:flex;gap:8px;align-items:center}
  #ans{flex:1;font-size:26px;padding:8px 12px;border-radius:6px;border:2px solid #3d6cff;
    background:#0f1115;color:#fff;font-family:inherit;outline:none}
  #ans:focus{border-color:#68a0ff;box-shadow:0 0 0 3px rgba(61,108,255,.25)}
  .btns{display:flex;gap:6px}
  button{padding:9px 14px;border-radius:6px;border:1px solid #3a3d44;background:#2a2d33;
    color:#e8e8e8;cursor:pointer;font-family:inherit;font-size:13px;white-space:nowrap}
  button:hover{background:#343841}
  button.pri{background:#1f4fd8;border-color:#2f63ff;font-weight:700}
  #body{display:flex;height:calc(100% - 132px)}
  #vp{position:relative;flex:1;min-width:0;overflow:hidden;background:#000;cursor:grab}
  #vp.drag{cursor:grabbing}
  #world{position:absolute;left:0;top:0;width:W_PXpx;height:H_PXpx;transform-origin:0 0}
  #world img{position:absolute;left:0;top:0;width:W_PXpx;height:H_PXpx;user-select:none;-webkit-user-drag:none}
  #ring{position:absolute;border:3px solid #ff2d2d;border-radius:50%;
    box-shadow:0 0 0 4px rgba(255,45,45,.22);pointer-events:none}
  #side{width:230px;flex:none;background:#1c1e22;border-left:1px solid #333;overflow:auto;padding:6px}
  .it{display:flex;justify-content:space-between;gap:6px;padding:4px 6px;font-size:12px;
    color:#bbb;border-radius:3px;cursor:pointer}
  .it:hover{background:#26282d} .it.cur{background:#2b3b6b;color:#fff}
  .it.done{color:#7dd3a0}
  #hint{position:absolute;left:10px;bottom:8px;font-size:12px;color:#aaa;
    background:rgba(0,0,0,.6);padding:4px 8px;border-radius:4px}
</style></head>
<body>
<div id="top">
  <div id="line1">
    <div id="big"></div>
    <div id="sub"></div>
    <div id="prog"></div>
  </div>
  <div id="line2">
    <input id="ans" autocomplete="off" placeholder="对照地图，输入正确地名后回车">
    <div class="btns">
      <button class="pri" onclick="confirmAns()">确认 Enter</button>
      <button onclick="skip()">跳过 →</button>
      <button onclick="prev()">← 上一条</button>
      <button onclick="nextTodo()">下一未确认</button>
      <button onclick="exportCSV()">导出 CSV</button>
    </div>
  </div>
</div>
<div id="body">
  <div id="vp"><div id="world"><img src="ditu.png" alt="map"><div id="ring"></div></div>
    <div id="hint">滚轮缩放 · 拖动平移 · 空格镜头回正</div>
  </div>
  <div id="side"></div>
</div>
<script>
const DATA = __DATA__;
const GROUP = "__GROUP__";
const KEY = "zg_names_" + GROUP;
let answers = {}, done = {};
try {
  answers = JSON.parse(localStorage.getItem(KEY) || "{}");
  done = JSON.parse(localStorage.getItem(KEY + "_d") || "{}");
} catch(e) {}
let idx = parseInt(localStorage.getItem(KEY + "_i") || "0");
if (isNaN(idx) || idx < 0 || idx >= DATA.length) idx = 0;

const vp = document.getElementById("vp"), world = document.getElementById("world");
const ring = document.getElementById("ring"), ansEl = document.getElementById("ans");
let z = 2.5, tx = 0, ty = 0, dragging = false, lx = 0, ly = 0;

function apply(){ world.style.transform = `translate(${tx}px,${ty}px) scale(${z})`; }
function center(x,y,zz){ if(zz) z=zz; tx=vp.clientWidth/2-x*z; ty=vp.clientHeight/2-y*z; apply(); }
function cur(){ return DATA[idx]; }
function val(it){ return answers[it.id] !== undefined ? answers[it.id] : it.name; }

function render(){
  const d = cur();
  ring.style.left=(d.x-26)+"px"; ring.style.top=(d.y-26)+"px";
  ring.style.width="52px"; ring.style.height="52px";
  center(d.x,d.y,z);
  const n=Object.keys(done).length;
  const big=document.getElementById("big");
  const v=val(d);
  big.textContent = v || "⌀ 未识别";
  big.className = v ? "" : "empty";
  const changed = v !== d.name;
  document.getElementById("sub").innerHTML =
    `${d.id} · ${d.kind}` +
    (changed ? `　原识别：<b>${d.name||"⌀"}</b>` : "") +
    (done[d.id] ? '　<span style="color:#7dd3a0">已确认</span>' : "");
  document.getElementById("prog").innerHTML =
    `${GROUP}<br>第 ${idx+1} / ${DATA.length}<br>已确认 ${n}`;
  ansEl.value = v;
  ansEl.focus(); ansEl.select();
  renderSide();
}

function renderSide(){
  const box=document.getElementById("side");
  const start=Math.max(0,idx-8), part=DATA.slice(start,start+90);
  box.innerHTML=part.map((it,k)=>{
    const i=start+k, v=val(it);
    return `<div class="it ${i===idx?'cur':''} ${done[it.id]?'done':''}" onclick="go(${i})">
      <span>${it.id} ${it.kind}</span><span>${v||'⌀'}</span></div>`;
  }).join("");
  const c=box.querySelector(".cur"); if(c) c.scrollIntoView({block:"center"});
}

function go(i){ idx=Math.max(0,Math.min(DATA.length-1,i)); save(); render(); }
function save(){
  try{
    localStorage.setItem(KEY,JSON.stringify(answers));
    localStorage.setItem(KEY+"_d",JSON.stringify(done));
    localStorage.setItem(KEY+"_i",String(idx));
  }catch(e){}
}
function confirmAns(){
  const d=cur(), v=ansEl.value.trim();
  if(v) answers[d.id]=v; else answers[d.id]="";
  done[d.id]=true;
  idx=Math.min(idx+1,DATA.length-1); save(); render();
}
function skip(){ idx=Math.min(idx+1,DATA.length-1); save(); render(); }
function prev(){ idx=Math.max(idx-1,0); save(); render(); }
function nextTodo(){
  for(let i=idx+1;i<DATA.length;i++) if(!done[DATA[i].id]) return go(i);
  for(let i=0;i<DATA.length;i++) if(!done[DATA[i].id]) return go(i);
  alert("本组已全部确认");
}

function exportCSV(){
  const rows=[["id","name","kind","x","y","original","confirmed"]];
  DATA.forEach(it=>rows.push([it.id,val(it),it.kind,it.x,it.y,it.name,done[it.id]?1:0]));
  const csv="\ufeff"+rows.map(r=>r.join(",")).join("\r\n");
  const a=document.createElement("a");
  a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"}));
  a.download="names_"+GROUP+".csv"; a.click(); URL.revokeObjectURL(a.href);
}

ansEl.addEventListener("keydown",e=>{
  if(e.isComposing) return;
  if(e.key==="Enter"){ e.preventDefault(); confirmAns(); }
});
window.addEventListener("keydown",e=>{
  if(document.activeElement===ansEl) return;
  if(e.key==="ArrowRight") skip();
  if(e.key==="ArrowLeft") prev();
  if(e.key===" "){ e.preventDefault(); const d=cur(); center(d.x,d.y,z); }
});
vp.addEventListener("mousedown",e=>{ dragging=true; lx=e.clientX; ly=e.clientY; vp.classList.add("drag"); });
window.addEventListener("mouseup",()=>{ dragging=false; vp.classList.remove("drag"); });
window.addEventListener("mousemove",e=>{
  if(!dragging) return;
  tx+=e.clientX-lx; ty+=e.clientY-ly; lx=e.clientX; ly=e.clientY; apply();
});
vp.addEventListener("wheel",e=>{
  e.preventDefault();
  const r=vp.getBoundingClientRect(), mx=e.clientX-r.left, my=e.clientY-r.top;
  const nz=Math.min(8,Math.max(0.4,z*(e.deltaY<0?1.15:1/1.15)));
  tx=mx-(mx-tx)*(nz/z); ty=my-(my-ty)*(nz/z); z=nz; apply();
},{passive:false});
window.addEventListener("resize",()=>{ const d=cur(); center(d.x,d.y,z); });

render();
</script></body></html>"""

made = []
for i, g in enumerate(groups, 1):
    tag = f"group-{i:02d}"
    html = (TPL.replace("__DATA__", json.dumps(g, ensure_ascii=False))
               .replace("__GROUP__", tag)
               .replace("__TITLE__", tag)
               .replace("W_PX", str(W)).replace("H_PX", str(H)))
    (PKG / f"{tag}.html").write_text(html, encoding="utf-8")
    made.append((tag, len(g), g[0]["y"]))

# 全量版
html = (TPL.replace("__DATA__", json.dumps(items, ensure_ascii=False))
           .replace("__GROUP__", "all").replace("__TITLE__", "全量")
           .replace("W_PX", str(W)).replace("H_PX", str(H)))
(PKG / "names-all.html").write_text(html, encoding="utf-8")

# 参考数据
shutil.copy2(ROOT / "data" / "map" / "nodes.csv", PKG / "nodes_reference.csv")

readme = f"""# 战国演义 · 地名勘误包

## 这是什么
一张战国地图（BC 400）上标了 {len(items)} 座城邑。我们要核对每个点和它的名字是否对应。
共分 {len(groups)} 个组，每人一组。

## 怎么用
1. 解压后**直接双击**你负责的那个 HTML（`group-01.html` … `group-{len(groups):02d}.html`）。
   不需要联网，也不需要装任何东西（Chrome / Edge 都行）。
2. 页面顶部大字 = 当前这一条识别出的名字。
3. 地图会自动放大到那个城，红圈是它。
4. **对照红圈旁边的原字**：
   - 一样 → 直接按 **回车**
   - 不对 → 直接改，回车
   - 图上根本没有这个城 → 清空后回车
5. 进度自动保存在浏览器里，关了再开能接着来。

## 按键
| 键 | 作用 |
|---|---|
| Enter | 确认并下一条 |
| → | 跳过（不改） |
| ← | 上一条 |
| 空格 | 镜头回正（拖歪了用） |
| 滚轮 / 拖动 | 缩放 / 平移 |

## 做完
点右上「导出 CSV」，会得到 `names_group-XX.csv`，把这个文件发回即可。

导出文件里有 `original`（改之前）和 `confirmed`（是否过了一遍）两列，
方便合并时核对。

## 分组
""" + "\n".join(f"- `{t}.html`：{n} 条（从 y≈{int(y)} 开始）" for t, n, y in made) + """

## 注意
- 有些名字是两个字粘在一起的（例如「曲阜防」其实是「曲阜」+「防」）。
  遇到这种，**填你这一条该有的那个名字**即可，另一个我会补。
- 地图文件 `ditu.png` 必须和 HTML 放在同一层目录，不要移动。
"""

(PKG / "README.md").write_text(readme, encoding="utf-8")

total = sum(n for _, n, _ in made)
print(f"分组 {len(groups)}，合计 {total} 条 -> {PKG}")
for t, n, y in made:
    print(f"  {t}: {n} 条")
