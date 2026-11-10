# -*- coding: utf-8 -*-
"""单一页面的全量地名勘误器（弹性布局，顶部不再被地图压住）。
同时输出到本地工作区与可分发包。
"""
import csv
import json
import shutil
from pathlib import Path

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
PKG = ROOT / "dist" / "map-review"
W, H = 9101, 8509

rows = list(csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")))
items = [{"id": r["id"], "name": r["name"], "kind": r["kind"],
          "x": float(r["x"]), "y": float(r["y"])} for r in rows]
items.sort(key=lambda d: (d["y"], d["x"]))

TPL = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>战国演义 · 地名勘误</title>
<style>
  *{box-sizing:border-box}
  html,body{margin:0;height:100%;overflow:hidden;font-family:"Microsoft YaHei UI",sans-serif;
    background:#141517;color:#e8e8e8}
  body{display:flex;flex-direction:column}
  #top{flex:none;background:#1b1d21;border-bottom:2px solid #3a3d44;padding:10px 16px 12px}
  #line1{display:flex;align-items:flex-end;gap:16px;min-height:52px}
  #big{font-size:40px;font-weight:800;color:#fff;line-height:1.05;letter-spacing:2px}
  #big.empty{color:#8a8d91}
  #sub{font-size:13px;color:#9aa0a6;padding-bottom:6px}
  #sub b{color:#ffd166}
  #stat{margin-left:auto;text-align:right;font-size:13px;color:#7dd3a0;line-height:1.5;padding-bottom:4px}
  #line2{display:flex;gap:8px;align-items:center;margin-top:10px}
  #ans{flex:1;font-size:24px;padding:8px 12px;border-radius:6px;border:2px solid #3d6cff;
    background:#0f1115;color:#fff;font-family:inherit;outline:none}
  #ans:focus{border-color:#68a0ff;box-shadow:0 0 0 3px rgba(61,108,255,.25)}
  .btns{display:flex;gap:6px}
  button{padding:9px 14px;border-radius:6px;border:1px solid #3a3d44;background:#2a2d33;
    color:#e8e8e8;cursor:pointer;font-family:inherit;font-size:13px;white-space:nowrap}
  button:hover{background:#343841}
  button.pri{background:#1f4fd8;border-color:#2f63ff;font-weight:700}
  #body{flex:1;min-height:0;display:flex}
  #vp{position:relative;flex:1;min-width:0;overflow:hidden;background:#000;cursor:grab}
  #vp.drag{cursor:grabbing}
  #world{position:absolute;left:0;top:0;width:W_PXpx;height:H_PXpx;transform-origin:0 0}
  #world img{position:absolute;left:0;top:0;width:W_PXpx;height:H_PXpx;user-select:none;-webkit-user-drag:none}
  #ring{position:absolute;border:3px solid #ff2d2d;border-radius:50%;
    box-shadow:0 0 0 4px rgba(255,45,45,.22);pointer-events:none}
  #side{width:220px;flex:none;background:#1c1e22;border-left:1px solid #333;overflow:auto;padding:6px}
  .it{display:flex;justify-content:space-between;gap:6px;padding:4px 6px;font-size:12px;
    color:#bbb;border-radius:3px;cursor:pointer}
  .it:hover{background:#26282d} .it.cur{background:#2b3b6b;color:#fff}
  .it.done{color:#7dd3a0} .it.chg{color:#ffd166;font-weight:700}
  #hint{position:absolute;left:10px;bottom:8px;font-size:12px;color:#aaa;
    background:rgba(0,0,0,.6);padding:4px 8px;border-radius:4px}
</style></head>
<body>
<div id="top">
  <div id="line1">
    <div id="big"></div>
    <div id="sub"></div>
    <div id="stat"></div>
  </div>
  <div id="line2">
    <input id="ans" autocomplete="off" placeholder="对照地图上的原字，改成正确的名字后回车">
    <div class="btns">
      <button class="pri" onclick="confirmAns()">确认 Enter</button>
      <button onclick="skip()">跳过 →</button>
      <button onclick="prev()">← 上一条</button>
      <button onclick="nextTodo()">下一未确认</button>
      <button onclick="exportCSV(false)">导出全部</button>
      <button onclick="exportCSV(true)">只导出改动</button>
      <button id="bindBtn" onclick="bindFile()">绑定本地文件（自动保存）</button>
    </div>
    <div id="fstat" style="font-size:12px;color:#8a8d91;padding:2px 4px"></div>
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
const KEY = "zg_names_one";
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
function changed(it){ return val(it) !== it.name; }

function render(){
  const d = cur();
  ring.style.left=(d.x-26)+"px"; ring.style.top=(d.y-26)+"px";
  ring.style.width="52px"; ring.style.height="52px";
  center(d.x,d.y,z);
  const big=document.getElementById("big");
  const v=val(d);
  big.textContent = v || "⌀ 未识别";
  big.className = v ? "" : "empty";
  document.getElementById("sub").innerHTML =
    `${d.id} · ${d.kind}` + (changed(d) ? `　原识别：<b>${d.name||"⌀"}</b>` : "");
  const nDone=Object.keys(done).length;
  const nChg=DATA.filter(changed).length;
  document.getElementById("stat").innerHTML =
    `第 ${idx+1} / ${DATA.length}　已确认 ${nDone}<br>已改 <b style="color:#ffd166">${nChg}</b> 条`;
  ansEl.value = v;
  ansEl.focus(); ansEl.select();
  renderSide();
}

function renderSide(){
  const box=document.getElementById("side");
  const start=Math.max(0,idx-8), part=DATA.slice(start,start+90);
  box.innerHTML=part.map((it,k)=>{
    const i=start+k, v=val(it);
    const cls = i===idx ? "cur" : (changed(it) ? "chg" : (done[it.id] ? "done" : ""));
    return `<div class="it ${cls}" onclick="go(${i})">
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
  scheduleWrite();
}

/* ---------- 绑定本地文件，自动写盘 ---------- */
let fh=null, wTimer=null, writing=false;
function csvText(){
  const rows=[["id","name","kind","x","y","original","changed","confirmed"]];
  DATA.forEach(it=>{ const v=val(it), ch=changed(it);
    rows.push([it.id,v,it.kind,it.x,it.y,it.name,ch?1:0,done[it.id]?1:0]); });
  return "\ufeff"+rows.map(r=>r.join(",")).join("\r\n");
}
function setFstat(t,color){ const el=document.getElementById("fstat");
  el.textContent=t; el.style.color=color||"#8a8d91"; }
async function bindFile(){
  if(!window.showSaveFilePicker){ alert("当前浏览器不支持直接写文件（需 Chrome/Edge），请用「导出」。"); return; }
  try{
    fh=await window.showSaveFilePicker({suggestedName:"names_current.csv",
      types:[{description:"CSV",accept:{"text/csv":[".csv"]}}]});
    await writeNow();
  }catch(e){ if(e.name!=="AbortError") alert("绑定失败："+e.message); }
}
async function writeNow(){
  if(!fh||writing) return;
  writing=true;
  try{
    const w=await fh.createWritable();
    await w.write(new Blob([csvText()],{type:"text/csv"}));
    await w.close();
    setFstat("已自动保存 → "+fh.name+"（"+new Date().toLocaleTimeString()+"）","#7dd3a0");
  }catch(e){ setFstat("写入失败："+e.message+"（点「绑定」重新授权）","#f0a8a8"); }
  finally{ writing=false; }
}
function scheduleWrite(){ if(!fh) return; clearTimeout(wTimer); wTimer=setTimeout(writeNow,800); }
function confirmAns(){
  const d=cur(), v=ansEl.value.trim();
  answers[d.id] = v;
  done[d.id] = true;
  idx=Math.min(idx+1,DATA.length-1); save(); render();
}
function skip(){ idx=Math.min(idx+1,DATA.length-1); save(); render(); }
function prev(){ idx=Math.max(idx-1,0); save(); render(); }
function nextTodo(){
  for(let i=idx+1;i<DATA.length;i++) if(!done[DATA[i].id]) return go(i);
  for(let i=0;i<DATA.length;i++) if(!done[DATA[i].id]) return go(i);
  alert("已全部确认");
}

function exportCSV(onlyChanged){
  const rows=[["id","name","kind","x","y","original","changed","confirmed"]];
  DATA.forEach(it=>{
    const v=val(it), ch=changed(it);
    if (onlyChanged && !ch) return;
    rows.push([it.id,v,it.kind,it.x,it.y,it.name,ch?1:0,done[it.id]?1:0]);
  });
  const csv="\ufeff"+rows.map(r=>r.join(",")).join("\r\n");
  const a=document.createElement("a");
  a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"}));
  a.download = onlyChanged ? "names_changes.csv" : "names_all.csv";
  a.click(); URL.revokeObjectURL(a.href);
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

html = (TPL.replace("__DATA__", json.dumps(items, ensure_ascii=False))
           .replace("W_PX", str(W)).replace("H_PX", str(H)))

# 本地版
(ROOT / "data" / "map" / "review" / "names.html").write_text(html, encoding="utf-8")

# 分发包（重建为单页）
if PKG.exists():
    for f in PKG.glob("group-*.html"):
        f.unlink()
(PKG / "names.html").write_text(html, encoding="utf-8")
shutil.copy2(ROOT / "ditu.png", PKG / "ditu.png")
if (PKG / "names-all.html").exists():
    (PKG / "names-all.html").unlink()
shutil.copy2(ROOT / "data" / "map" / "nodes.csv", PKG / "nodes_reference.csv")

readme = f"""# 战国演义 · 地名勘误

## 这是什么
一张战国地图（BC 400）标了 {len(items)} 座城邑。请核对每个点和它的名字是否对应。

## 怎么用
1. 解压，**双击 `names.html`**（Chrome / Edge 都行，不用联网）。
2. 顶部大字 = 这一条识别出的名字。
3. 地图会自动放大到该城，**红圈**就是它。
4. 对照红圈旁边图上的原字：
   - 一样 → 按 **回车**
   - 不对 → 改成正确的，按回车
   - 图上没有这个城 → 清空后回车
5. 进度自动保存在浏览器里，关掉再开能接着来。

## 按键
| 键 | 作用 |
|---|---|
| Enter | 确认并下一条 |
| → | 跳过（不改） |
| ← | 上一条 |
| 空格 | 镜头回正 |
| 滚轮 / 拖动 | 缩放 / 平移 |

## 做完后怎么给我
点 **「只导出改动」**，得到 `names_changes.csv`——里面只有你改过的条目，
带 `original`（原识别）和 `name`（你改的）两列，我直接合并。
如果还想要完整记录，点「导出全部」得到 `names_all.csv`。

## 注意
- `ditu.png` 必须和 `names.html` 放在同一层目录，不要单独移动，否则地图空白。
- 有些名字是两个字粘在一起的（例如「曲阜防」其实是「曲阜」+「防」）。
  遇到这种，**填你这一条该有的那个名字**即可，另一个我会补。
"""

# README 由 tools/write_readme.py 统一生成，这里不覆盖

print("items", len(items))
print("local ->", ROOT / "data" / "map" / "review" / "names.html")
print("pkg   ->", PKG)

