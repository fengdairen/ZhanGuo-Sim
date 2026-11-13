# -*- coding: utf-8 -*-
"""人群库编辑器：只管「有哪些人群」，每群人一条简介。
不管某城有谁——那是地图编辑器的活。
"""
import csv
import json
from pathlib import Path

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
OUT = ROOT / "data" / "map" / "review" / "pop_table.html"
PKG = ROOT / "dist" / "map-review"

groups = [{"name": r["name"], "note": r["note"]}
          for r in csv.DictReader((ROOT / "data" / "map" / "groups.csv").open(encoding="utf-8-sig"))]

# 只读统计：每群总量与分布城市数
agg, cnt = {}, {}
for r in csv.DictReader((ROOT / "data" / "map" / "populations.csv").open(encoding="utf-8-sig")):
    g = r["group"]
    agg[g] = agg.get(g, 0) + float(r["amount"])
    cnt[g] = cnt.get(g, 0) + 1
stats = {g: {"sum": round(agg.get(g, 0), 1), "n": cnt.get(g, 0)} for g in agg}

TPL = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>战国演义 · 人群库</title>
<style>
  *{box-sizing:border-box}
  html,body{margin:0;height:100%;overflow:hidden;font-family:"Microsoft YaHei UI",sans-serif;
    background:#141517;color:#e8e8e8}
  body{display:flex;flex-direction:column}
  #top{flex:none;background:#1b1d21;border-bottom:2px solid #3a3d44;padding:10px 16px;
    display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:13px}
  #top input{background:#0f1115;color:#fff;border:1px solid #3a3d44;border-radius:5px;
    padding:7px 9px;font-family:inherit;font-size:13px}
  #top button{padding:7px 14px;border-radius:5px;border:1px solid #3a3d44;background:#2a2d33;
    color:#e8e8e8;cursor:pointer;font-family:inherit;font-size:13px}
  #top button:hover{background:#343841}
  #top button.pri{background:#1f4fd8;border-color:#2f63ff;font-weight:700}
  #stat{margin-left:auto;font-size:12px;color:#9aa0a6}
  #stat b{color:#7dd3a0}
  #main{flex:1;min-height:0;overflow:auto;padding:0}
  table{width:100%;border-collapse:collapse;font-size:13px}
  thead th{position:sticky;top:0;background:#22252a;color:#9aa0a6;font-weight:400;
    text-align:left;padding:9px 12px;border-bottom:1px solid #3a3d44;font-size:12px;z-index:2}
  tbody td{padding:6px 12px;border-bottom:1px solid #24262b;vertical-align:top}
  tbody tr:hover{background:#1f2126}
  td input{background:transparent;color:#e8e8e8;border:1px solid transparent;border-radius:4px;
    padding:5px 6px;font-family:inherit;font-size:13px;width:100%}
  td input:hover{border-color:#3a3d44}
  td input:focus{background:#0f1115;border-color:#3d6cff;outline:none}
  td input.name{font-weight:700;font-size:14px}
  .num{text-align:right;color:#8a8d91;font-variant-numeric:tabular-nums;white-space:nowrap}
  .x{color:#f0a8a8;cursor:pointer;user-select:none;text-align:center;font-size:15px}
  .hint{color:#6f7378;font-size:12px;padding:10px 16px;line-height:1.7}
</style></head>
<body>
<div id="top">
  <input id="ngName" placeholder="人群名，如「楚人」" style="width:170px">
  <input id="ngNote" placeholder="简介：文化 / 认知 / 政治倾向" style="width:420px">
  <button class="pri" onclick="addGroup()">＋ 新增人群</button>
  <button onclick="exportCSV()">导出 groups.csv</button>
  <button id="bindBtn" onclick="bindFile()">绑定本地文件</button>
  <span id="fstat" style="font-size:12px;color:#8a8d91"></span>
  <span id="stat"></span>
</div>
<div id="main">
  <table>
    <thead><tr>
      <th style="width:150px">人群</th>
      <th>简介（文化 / 认知 / 政治倾向）</th>
      <th style="width:110px;text-align:right">总人口</th>
      <th style="width:80px;text-align:right">条目数</th>
      <th style="width:36px"></th>
    </tr></thead>
    <tbody id="tbody"></tbody>
  </table>
  <div class="hint">
    这里只定义「世界上有哪些人群」。某个城里有几万什么人，请到<b>地图编辑器</b>里配。<br>
    总人口 / 条目数是只读统计，来自人口表。
  </div>
</div>
<script>
const GROUPS0 = __GROUPS__;
const STATS = __STATS__;
const KEY = "zg_groups_v1";
let groups = GROUPS0.map(g => Object.assign({}, g));
try { const s = localStorage.getItem(KEY); if (s) { const a = JSON.parse(s);
  if (a && a.length) groups = a; } } catch(e) {}

function f0(v){ return v>=10 ? v.toFixed(0) : v.toFixed(1); }

function render(){
  const tb = document.getElementById("tbody");
  tb.innerHTML = groups.map((g,i)=>`
    <tr>
      <td><input class="name" value="${(g.name||'').replace(/"/g,'&quot;')}"
            onchange="setName(${i},this.value)"></td>
      <td><input value="${(g.note||'').replace(/"/g,'&quot;')}"
            placeholder="（无简介）" onchange="setNote(${i},this.value)"></td>
      <td class="num">${STATS[g.name] ? f0(STATS[g.name].sum)+' 万' : '—'}</td>
      <td class="num">${STATS[g.name] ? STATS[g.name].n : '—'}</td>
      <td class="x" onclick="delGroup(${i})">✕</td>
    </tr>`).join("") || `<tr><td colspan="5" style="padding:20px;color:#8a8d91">还没有人群，先在上面新增一条</td></tr>`;

  const total = Object.values(STATS).reduce((s,x)=>s+x.sum,0);
  document.getElementById("stat").innerHTML =
    `人群 <b>${groups.length}</b>　已分配人口 <b>${total.toFixed(0)}</b> 万`;
  save();
}

function setName(i,v){
  const n=(v||"").trim(); if(!n) { render(); return alert("名字不能为空"); }
  if(groups.some((g,k)=>k!==i && g.name===n)) return alert("已存在同名人群");
  groups[i].name=n; render();
}
function setNote(i,v){ groups[i].note=v; save(); }
function addGroup(){
  const n=document.getElementById("ngName").value.trim();
  const note=document.getElementById("ngNote").value.trim();
  if(!n) return alert("请填人群名");
  if(groups.some(g=>g.name===n)) return alert("已存在");
  groups.push({name:n, note:note});
  document.getElementById("ngName").value="";
  document.getElementById("ngNote").value="";
  render();
}
function delGroup(i){
  const g=groups[i];
  if(STATS[g.name] && STATS[g.name].n>0){
    if(!confirm(`「${g.name}」在人口表里还有 ${STATS[g.name].n} 条记录（${f0(STATS[g.name].sum)} 万）。\n仍然从人群库删除？（不会动人口表）`)) return;
  } else if(!confirm(`删除人群「${g.name}」？`)) return;
  groups.splice(i,1); render();
}

function csvText(){
  const rows=[["name","note"]];
  groups.forEach(g=>rows.push([g.name,g.note||""]));
  return "\ufeff"+rows.map(r=>r.join(",")).join("\r\n");
}
function exportCSV(){
  const a=document.createElement("a");
  a.href=URL.createObjectURL(new Blob([csvText()],{type:"text/csv;charset=utf-8"}));
  a.download="groups.csv"; a.click(); URL.revokeObjectURL(a.href);
}

let fh=null,wTimer=null,writing=false;
function setFstat(t,c){ const el=document.getElementById("fstat"); el.textContent=t; el.style.color=c||"#8a8d91"; }
async function bindFile(){
  if(!window.showSaveFilePicker){ alert("需要 Chrome / Edge 才能直接写文件"); return; }
  try{
    fh=await window.showSaveFilePicker({suggestedName:"groups.csv",
      types:[{description:"CSV",accept:{"text/csv":[".csv"]}}]});
    await writeNow();
  }catch(e){ if(e.name!=="AbortError") alert("绑定失败："+e.message); }
}
async function writeNow(){
  if(!fh||writing) return; writing=true;
  try{
    const w=await fh.createWritable();
    await w.write(new Blob([csvText()],{type:"text/csv"}));
    await w.close();
    setFstat("已自动保存 → "+fh.name+"（"+new Date().toLocaleTimeString()+"）","#7dd3a0");
  }catch(e){ setFstat("写入失败："+e.message,"#f0a8a8"); }
  finally{ writing=false; }
}
function save(){
  try{ localStorage.setItem(KEY, JSON.stringify(groups)); }catch(e){}
  if(!fh) return;
  clearTimeout(wTimer); wTimer=setTimeout(writeNow,800);
}

render();
</script></body></html>"""

html = (TPL.replace("__GROUPS__", json.dumps(groups, ensure_ascii=False))
           .replace("__STATS__", json.dumps(stats, ensure_ascii=False)))
(OUT).write_text(html, encoding="utf-8")
(PKG / "pop_table.html").write_text(html, encoding="utf-8")
print("groups", len(groups), "stats keys", len(stats))
