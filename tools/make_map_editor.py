# -*- coding: utf-8 -*-
"""完整地图编辑器：改名 / 改人口 / 移动标点 / 新建 / 删除 / 批量 / 导出。"""
import csv
import json
from pathlib import Path

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
OUT = ROOT / "data" / "map" / "review" / "map_editor.html"
W, H = 9101, 8509

items = []
for r in csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")):
    items.append({"id": r["id"], "name": r["name"], "kind": r["kind"],
                  "x": float(r["x"]), "y": float(r["y"]), "pop": float(r["pop"]), "t": 0})
for r in csv.DictReader((ROOT / "data" / "map" / "regions.csv").open(encoding="utf-8-sig")):
    items.append({"id": r["id"], "name": r["name"], "kind": "部族",
                  "x": float(r["x"]), "y": float(r["y"]), "pop": float(r["pop"]), "t": 1})

groups = [{"name": r["name"], "note": r["note"]}
          for r in csv.DictReader((ROOT / "data" / "map" / "groups.csv").open(encoding="utf-8-sig"))]
pops = [{"id": r["id"], "city": r["city_id"], "group": r["group"],
         "amount": float(r["amount"]), "note": r.get("note", "")}
        for r in csv.DictReader((ROOT / "data" / "map" / "populations.csv").open(encoding="utf-8-sig"))]

# 归属：国别清单 + 城池归属表
state = json.loads((ROOT / "data" / "state.json").read_text(encoding="utf-8"))
PALETTE = ["#c0392b", "#2980b9", "#27ae60", "#8e44ad", "#d35400",
           "#16a085", "#2c3e50", "#c2185b", "#7f8c8d", "#f39c12"]
nations = []
for i, n in enumerate(state["nations"]):
    nations.append({"id": n["id"], "name": n["name"], "color": PALETTE[i % len(PALETTE)]})
owner = {}
for r in csv.DictReader((ROOT / "data" / "map" / "ownership.csv").open(encoding="utf-8-sig")):
    if r["owner"]:
        owner[r["city_id"]] = r["owner"]

TPL = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>战国演义 · 地图编辑器</title>
<style>
  *{box-sizing:border-box}
  html,body{margin:0;height:100%;overflow:hidden;font-family:"Microsoft YaHei UI",sans-serif;
    background:#141517;color:#e8e8e8}
  body{display:flex;flex-direction:column}
  #top{flex:none;background:#1b1d21;border-bottom:2px solid #3a3d44;padding:8px 14px;
    display:flex;align-items:center;gap:10px;flex-wrap:wrap}
  #top button{padding:7px 14px;border-radius:6px;border:1px solid #3a3d44;background:#2a2d33;
    color:#dfe;cursor:pointer;font-family:inherit;font-size:13px}
  #top button:hover{background:#343841}
  #top button.on{background:#1f4fd8;border-color:#2f63ff;color:#fff;font-weight:700}
  #stat{margin-left:auto;font-size:12px;color:#9aa0a6;line-height:1.5;text-align:right}
  #stat b{color:#7dd3a0}
  #body{flex:1;min-height:0;display:flex}
  #vp{position:relative;flex:1;min-width:0;overflow:hidden;background:#000;cursor:default}
  #vp.pan{cursor:grabbing} #vp.movecur{cursor:move} #vp.paintcur{cursor:crosshair}
  #vp.addcur{cursor:copy}
  #world{position:absolute;left:0;top:0;width:W_PXpx;height:H_PXpx;transform-origin:0 0}
  #world img{position:absolute;left:0;top:0;width:W_PXpx;height:H_PXpx;user-select:none;-webkit-user-drag:none}
  #paint{position:absolute;inset:0;pointer-events:none;z-index:6}
  body.painting #paint{pointer-events:auto;cursor:crosshair}
  .mk{position:absolute;border-radius:50%;box-sizing:border-box;transform:translate(-50%,-50%);
    pointer-events:none}
  .mk.邑{border:2px solid #1f9d3a} .mk.城{border:3px solid #d98200}
  .mk.都{border:3px solid #d02020} .mk.部族{border:2px dashed #8e5bd0}
  .mk.sel{box-shadow:0 0 0 3px #ffe066,0 0 12px #ffe066}
  .mk.moved{outline:2px dotted #00d0ff}
  .lb{position:absolute;transform:translate(-50%,0);font-size:13px;line-height:1;
    padding:2px 4px;border-radius:3px;background:rgba(255,255,255,.88);color:#1b1b1b;
    white-space:nowrap;pointer-events:none;font-variant-numeric:tabular-nums;
    box-shadow:0 0 0 1px rgba(0,0,0,.12)}
  .lb.big{color:#b00000;font-weight:700}
  body.hide-lb .lb{display:none}
  #right{width:340px;flex:none;background:#1c1e22;border-left:1px solid #333;padding:12px;
    display:flex;flex-direction:column;gap:9px;overflow:auto}
  h1{font-size:14px;margin:0;color:#fff}
  .box{background:#24262b;border:1px solid #333;border-radius:6px;padding:9px}
  .k{color:#8a8d91;font-size:12px;margin-bottom:4px}
  input[type=text],input[type=number]{width:100%;font-size:16px;padding:7px;border-radius:5px;
    border:1px solid #3d6cff;background:#0f1115;color:#fff;font-family:inherit;outline:none}
  .row{display:flex;gap:6px;margin-top:6px}
  .row button{flex:1;padding:7px 4px;border-radius:6px;border:1px solid #3a3d44;background:#2a2d33;
    color:#e8e8e8;cursor:pointer;font-family:inherit;font-size:12px}
  .row button:hover{background:#343841}
  .up{border-color:#2f6f45;color:#9ee6b8} .dn{border-color:#7a3b3b;color:#f0a8a8}
  .pri{background:#1f4fd8!important;border-color:#2f63ff!important}
  .del{background:#5a2323!important;border-color:#8c3232!important;color:#ffb3b3!important}
  #list{flex:1;overflow:auto;border-top:1px solid #333;margin-top:2px;padding-top:6px}
  .it{display:flex;justify-content:space-between;padding:3px 5px;font-size:12px;color:#bbb;
    border-radius:3px;cursor:pointer}
  .it:hover{background:#26282d} .it.sel{background:#3a3320;color:#ffe066}
  #hint{position:absolute;left:10px;bottom:8px;font-size:12px;color:#aaa;
    background:rgba(0,0,0,.6);padding:4px 8px;border-radius:4px}
</style></head>
<body>
<div id="top">
  <button id="mSel" class="on" onclick="setMode('sel')">选择</button>
  <button id="mMove" onclick="setMode('move')">移动标点</button>
  <button id="mPaint" onclick="setMode('paint')">涂色选区</button>
  <button id="mAdd" onclick="setMode('add')">新增标点</button>
  <button onclick="undo()">撤销</button>
  <button onclick="exportCSV()">导出地图 CSV</button>
  <button onclick="exportPops()">导出人口 CSV</button>
  <button id="bindBtn" onclick="bindFile()">绑定本地文件</button>
  <button onclick="bindOwnerFile()">绑定归属文件</button>
  <span id="fstat" style="font-size:12px;color:#8a8d91"></span>
  <span id="stat"></span>
</div>
<div id="body">
  <div id="vp"><div id="world"><img src="__IMG__" alt="map"><div id="mks"></div></div>
    <canvas id="paint"></canvas>
    <div id="hint">滚轮缩放 · 右键拖平移 · 空格复位</div>
  </div>
  <div id="right">
    <h1>编辑</h1>
    <div class="box">
      <div class="k">所选 <span id="cnt">0</span> 个　合计 <span id="sumpop">0</span> 万</div>
      <div class="k" id="ids" style="word-break:break-all;line-height:1.5"></div>
    </div>
    <div class="box">
      <div class="k">名字（选中单个时）</div>
      <input type="text" id="nameIn" placeholder="输入名字，回车生效">
      <div class="row"><button onclick="applyName()">应用名字</button></div>
    </div>
    <div class="box">
      <div class="k">人口（选中单个时的精确值，万）</div>
      <input type="text" id="popIn" placeholder="输入人口，回车生效">
      <div class="row"><button onclick="applyPop()">应用人口</button></div>
    </div>
    <div class="box">
      <div class="k">批量调整人口</div>
      <div class="row"><button class="up" onclick="adj(1.1)">+10%</button>
        <button class="up" onclick="adj(1.2)">+20%</button>
        <button class="up" onclick="adj(1.5)">+50%</button></div>
      <div class="row"><button class="dn" onclick="adj(0.9)">−10%</button>
        <button class="dn" onclick="adj(0.8)">−20%</button>
        <button class="dn" onclick="adj(0.5)">−50%</button></div>
    </div>
    <div class="box">
      <div class="k">类型（选中单个时）</div>
      <div class="row"><button onclick="setKind('都')">都</button>
        <button onclick="setKind('城')">城</button>
        <button onclick="setKind('邑')">邑</button>
        <button onclick="setKind('部族')">部族</button></div>
    </div>
    <div class="box" id="ownBox">
      <div class="k">城池归属（选中后可批量分配）</div>
      <div class="k" id="ownNow" style="color:#ffd166"></div>
      <div class="row">
        <select id="ownNation" style="flex:1;background:#0f1115;color:#fff;border:1px solid #3a3d44;
          border-radius:5px;padding:5px;font-family:inherit;font-size:12px"></select>
      </div>
      <div class="row">
        <button onclick="assignSel(document.getElementById('ownNation').value)">分配</button>
        <button onclick="assignSel('')">清除归属</button>
      </div>
      <div class="row">
        <button onclick="exportOwner()">导出 ownership.csv</button>
      </div>
    </div>
    <div class="box" id="popBox" style="display:none">
      <div class="k">人口构成（改动即改总量）</div>
      <table style="width:100%;border-collapse:collapse;font-size:12px">
        <thead><tr><th style="text-align:left;color:#8a8d91;font-weight:400">人群</th>
          <th style="width:70px;text-align:right;color:#8a8d91;font-weight:400">万</th>
          <th style="width:24px"></th></tr></thead>
        <tbody id="popRows"></tbody>
      </table>
      <div class="row">
        <select id="rowGroup" style="flex:1;background:#0f1115;color:#fff;border:1px solid #3a3d44;
          border-radius:5px;padding:5px;font-family:inherit;font-size:12px"></select>
        <input id="rowAmt" type="number" step="0.1" min="0" placeholder="万"
          style="width:66px;background:#0f1115;color:#fff;border:1px solid #3a3d44;border-radius:5px;
          padding:5px;font-family:inherit;font-size:12px">
        <button onclick="addPopRow()" style="flex:none;padding:5px 10px">＋</button>
      </div>
      <div class="row">
        <input id="splitPct" type="number" value="30" min="1" max="100"
          style="width:56px;background:#0f1115;color:#fff;border:1px solid #3a3d44;border-radius:5px;
          padding:5px;font-family:inherit;font-size:12px">
        <span class="k">% →</span>
        <select id="splitGroup" style="flex:1;background:#0f1115;color:#fff;border:1px solid #3a3d44;
          border-radius:5px;padding:5px;font-family:inherit;font-size:12px"></select>
        <button onclick="splitTo()" style="flex:none;padding:5px 10px">划分</button>
      </div>
    </div>
    <div class="row"><button class="del" onclick="delSel()">删除所选</button>
      <button onclick="selNone()">取消选择</button></div>
    <div id="list"></div>
  </div>
</div>
<script>
const DATA = __DATA__;
const GROUPS0 = __GROUPS__;
const POPS0 = __POPS__;
const NATIONS = __NATIONS__;
const OWNER0 = __OWNER__;
const KEY = "zg_mapedit_v2";
let items = DATA.map(d => Object.assign({}, d, {
  oname: d.name, opop: d.pop, ox: d.x, oy: d.y, del: false
}));
let groups = GROUPS0.map(g => Object.assign({}, g));
let pops = POPS0.map(p => Object.assign({}, p));
let owner = Object.assign({}, OWNER0);
try { const s = localStorage.getItem(KEY); if (s) { const a = JSON.parse(s);
  if (a && a.items && a.items.length === items.length) {
    items = a.items; pops = a.pops || pops; owner = a.owner || owner; } } } catch(e) {}
const sel = new Set();
let hist = [];
let z = 1.2, tx = 0, ty = 0, mode = "sel";

const vp = document.getElementById("vp"), world = document.getElementById("world");
const mks = document.getElementById("mks");
const cv = document.getElementById("paint"), ctx = cv.getContext("2d");
const nameIn = document.getElementById("nameIn"), popIn = document.getElementById("popIn");
const RAD = { "都": 9, "城": 6, "邑": 4.5, "部族": 7 };
const byId = {};
items.forEach(it => byId[it.id] = it);

function rowsOf(id){ return pops.filter(p => p.city === id); }
function cityTotal(id){ return rowsOf(id).reduce((s,p) => s + p.amount, 0); }
function syncPops(){ for (const it of items) it.pop = Math.round(cityTotal(it.id)*100)/100; }
syncPops();

/* ---------- 归属 ---------- */
const NATION_BY_ID = {}; NATIONS.forEach(n => NATION_BY_ID[n.id] = n);
function ownerColor(id){ const o = owner[id]; return o && NATION_BY_ID[o] ? NATION_BY_ID[o].color : null; }
function paintOwner(){
  for (const it of items){
    if (!it._mk) continue;
    const c = ownerColor(it.id);
    it._mk.style.background = c ? c : "transparent";
    it._mk.style.borderColor = c ? c : "";
    it._mk.style.opacity = c ? "1" : "0.55";
  }
}
function assignSel(nid){
  if (!sel.size) return alert("请先选择城池");
  snapshot();
  for (const id of sel){ if (nid) owner[id] = nid; else delete owner[id]; }
  save(); repaint();
}
function ownerLabel(id){ const o = owner[id]; return o && NATION_BY_ID[o] ? NATION_BY_ID[o].name : "未归属"; }

function fmt(p){ return p>=10? p.toFixed(0) : (p<1? p.toFixed(2) : p.toFixed(1)); }
function apply(){ world.style.transform = `translate(${tx}px,${ty}px) scale(${z})`;
  document.body.classList.toggle("hide-lb", z < 0.55);
  document.body.classList.toggle("painting", mode === "paint"); }
function center(x,y,zz){ if(zz) z=zz; tx=vp.clientWidth/2-x*z; ty=vp.clientHeight/2-y*z; apply(); }
function toScreen(x,y){ return [x*z+tx, y*z+ty]; }

function build(){
  mks.innerHTML="";
  const frag=document.createDocumentFragment();
  for (const it of items){
    if (it.del) continue;
    const r = RAD[it.kind] || 4.5;
    const d = document.createElement("div");
    d.className = "mk " + it.kind;
    d.style.left = it.x+"px"; d.style.top = it.y+"px";
    d.style.width = (r*2)+"px"; d.style.height = (r*2)+"px";
    frag.appendChild(d);
    const l = document.createElement("div");
    l.className="lb"; l.style.left=it.x+"px"; l.style.top=(it.y+r+2)+"px";
    frag.appendChild(l);
    it._mk=d; it._lb=l;
  }
  mks.appendChild(frag);
  repaint();
}

function repaint(){
  let tot=0, s=0, chg=0, alive=0;
  for (const it of items){
    if (it.del) continue;
    alive++;
    tot += it.pop;
    if (sel.has(it.id)) s += it.pop;
    if (it.name!==it.oname || it.pop!==it.opop || it.x!==it.ox || it.y!==it.oy) chg++;
    if (!it._mk) continue;
    it._mk.classList.toggle("sel", sel.has(it.id));
    it._mk.classList.toggle("moved", it.x!==it.ox || it.y!==it.oy);
    it._lb.textContent = fmt(it.pop);
    it._lb.classList.toggle("big", it.pop>=25);
  }
  document.getElementById("cnt").textContent = sel.size;
  document.getElementById("sumpop").textContent = s.toFixed(1);
  const arr=[...sel].map(id=>byId[id]).filter(Boolean);
  document.getElementById("ids").textContent =
    arr.slice(0,12).map(it=>it.name||it.id).join("、") + (arr.length>12? " …" : "");
  document.getElementById("stat").innerHTML =
    `城邑/部族 <b>${alive}</b>　总人口 <b>${tot.toFixed(0)}</b> 万　已改 <b style="color:#ffd166">${chg}</b> 条`;
  paintOwner();
  const ov = sel.size===1 ? ownerLabel([...sel][0]) : "";
  const oe = document.getElementById("ownNow");
  if (oe) oe.textContent = sel.size===1 ? ("当前归属：" + ov) : "";
  const box=document.getElementById("list");
  box.innerHTML = arr.slice(0,200).map(it=>
    `<div class="it sel"><span>${it.name||'⌀'} <span class="k">${it.kind}</span></span><span>${fmt(it.pop)}</span></div>`
  ).join("") || '<div class="k" style="padding:6px">未选中</div>';
  renderPopRows();
}

function snapshot(){ hist.push({items: items.map(i=>Object.assign({},i,{_mk:null,_lb:null})),
                                 pops: pops.map(p=>Object.assign({},p))}); if(hist.length>60) hist.shift(); }
function undo(){
  if (!hist.length) return;
  const p = hist.pop();
  items = p.items.map(o => Object.assign({}, o));
  pops = p.pops.map(o => Object.assign({}, o));
  items.forEach(it => byId[it.id] = it);
  sel.clear(); syncPops(); save(); build();
}
function save(){
  try { localStorage.setItem(KEY, JSON.stringify({
    items: items.map(({_mk,_lb,...r})=>r), pops: pops, owner: owner })); } catch(e){}
  scheduleWrite(); ownerSchedule();
}

/* ---------- 绑定本地文件，自动写盘 ---------- */
let fh = null, wTimer = null, writing = false;
function csvText(){
  const rows=[["id","name","kind","x","y","pop","deleted","oname","opop","ox","oy"]];
  items.forEach(it=>rows.push([it.id,it.name,it.kind,it.x.toFixed(1),it.y.toFixed(1),
    it.pop.toFixed(2), it.del?1:0, it.oname, it.opop, it.ox.toFixed(1), it.oy.toFixed(1)]));
  return "\ufeff" + rows.map(r=>r.join(",")).join("\r\n");
}
function setFstat(t, color){
  const el=document.getElementById("fstat");
  el.textContent = t; el.style.color = color || "#8a8d91";
}
async function bindFile(){
  if (!window.showSaveFilePicker){
    alert("当前浏览器不支持直接写文件（需要 Chrome / Edge）。请改用「导出 CSV」。");
    return;
  }
  try{
    fh = await window.showSaveFilePicker({
      suggestedName: "map_edited.csv",
      types: [{ description: "CSV", accept: { "text/csv": [".csv"] } }]
    });
    await writeNow();
  }catch(e){
    if (e.name !== "AbortError") alert("绑定失败：" + e.message);
  }
}
async function writeNow(){
  if (!fh || writing) return;
  writing = true;
  try{
    const w = await fh.createWritable();
    await w.write(new Blob([csvText()], { type: "text/csv" }));
    await w.close();
    const t = new Date();
    setFstat("已自动保存 → " + fh.name + "（" + t.toLocaleTimeString() + "）", "#7dd3a0");
  }catch(e){
    setFstat("写入失败：" + e.message + "（点「绑定」重新授权）", "#f0a8a8");
  }finally{
    writing = false;
  }
}
function scheduleWrite(){
  if (!fh) return;
  clearTimeout(wTimer);
  wTimer = setTimeout(writeNow, 800);
}

/* ---------- 编辑动作 ---------- */
function one(){ return sel.size===1 ? byId[[...sel][0]] : null; }
function applyName(){
  const it=one(); if(!it) return alert("请只选中一个标点");
  const v=nameIn.value.trim(); if(!v) return;
  snapshot(); it.name=v; save(); repaint();
}
function applyPop(){
  const it=one(); if(!it) return alert("请只选中一个标点");
  const v=parseFloat(popIn.value); if(isNaN(v)||v<0) return;
  snapshot();
  const rs = rowsOf(it.id);
  if (rs.length <= 1){
    if (rs.length === 1) rs[0].amount = Math.round(v*100)/100;
    else pops.push({id:"r"+Date.now().toString(36), city:it.id, group:"无认同人口",
                    amount:Math.round(v*100)/100, note:""});
  } else {
    const cur = cityTotal(it.id);
    const k = cur > 0 ? v / cur : 0;
    if (cur > 0) rs.forEach(p => p.amount = Math.round(p.amount*k*100)/100);
    else rs[0].amount = Math.round(v*100)/100;
  }
  syncPops(); save(); repaint();
}
function adj(k){
  if(!sel.size) return;
  snapshot();
  for(const id of sel){
    for(const p of rowsOf(id)) p.amount = Math.max(0, Math.round(p.amount*k*100)/100);
  }
  syncPops(); save(); repaint();
}
function setKind(k){
  const it=one(); if(!it) return alert("请只选中一个标点");
  snapshot(); it.kind=k;
  const r=RAD[k]||4.5;
  if(it._mk){ it._mk.className="mk "+k+(sel.has(it.id)?" sel":""); }
  save(); build();
}
function delSel(){
  if(!sel.size) return;
  if(!confirm("删除选中的 "+sel.size+" 个标点？（导出 CSV 时会带删除标记）")) return;
  snapshot();
  for(const id of sel){ const it=byId[id]; if(it){ it.del=true; } }
  pops = pops.filter(p => !sel.has(p.city));
  sel.clear(); syncPops(); save(); build();
}
function selNone(){ sel.clear(); repaint(); }

/* ---------- 人口条目编辑 ---------- */
function renderPopRows(){
  const box = document.getElementById("popBox");
  const it = one();
  box.style.display = it ? "" : "none";
  if (!it) return;
  const rs = rowsOf(it.id);
  document.getElementById("popRows").innerHTML = rs.map(p => `
    <tr>
      <td><input value="${p.group}" onchange="setRowGroup('${p.id}',this.value)"
        style="width:100%;background:transparent;border:1px solid transparent;color:#e8e8e8;
        font-family:inherit;font-size:12px;padding:3px"></td>
      <td><input type="number" step="0.1" min="0" value="${p.amount}" onchange="setRowAmt('${p.id}',this.value)"
        style="width:100%;text-align:right;background:transparent;border:1px solid transparent;
        color:#e8e8e8;font-family:inherit;font-size:12px;padding:3px"></td>
      <td class="x" onclick="delRow('${p.id}')" style="color:#f0a8a8;cursor:pointer;text-align:center">✕</td>
    </tr>`).join("") || `<tr><td colspan="3" class="k">（无条目）</td></tr>`;
  const opts = groups.map(g=>`<option>${g.name}</option>`).join("");
  document.getElementById("rowGroup").innerHTML = opts;
  document.getElementById("splitGroup").innerHTML = opts;
}
function setRowAmt(pid,v){
  const p=pops.find(x=>x.id===pid); if(!p) return;
  snapshot(); p.amount=Math.max(0, Math.round(parseFloat(v)*100)/100);
  syncPops(); save(); repaint();
}
function setRowGroup(pid,v){
  const p=pops.find(x=>x.id===pid); if(!p) return;
  p.group=(v||"").trim()||p.group; save(); repaint();
}
function delRow(pid){
  const i=pops.findIndex(x=>x.id===pid); if(i<0) return;
  snapshot(); pops.splice(i,1); syncPops(); save(); repaint();
}
function addPopRow(){
  const it=one(); if(!it) return alert("请先选中一个城市");
  const g=document.getElementById("rowGroup").value;
  const a=parseFloat(document.getElementById("rowAmt").value);
  if(!g||isNaN(a)||a<=0) return alert("请填人群与数量");
  snapshot();
  pops.push({id:"r"+Date.now().toString(36)+Math.floor(Math.random()*100),
             city:it.id, group:g, amount:Math.round(a*100)/100, note:""});
  document.getElementById("rowAmt").value="";
  syncPops(); save(); repaint();
}
function splitTo(){
  if(!sel.size) return alert("请先选中城市");
  const pct=parseFloat(document.getElementById("splitPct").value);
  const g=document.getElementById("splitGroup").value;
  if(isNaN(pct)||pct<=0||pct>100) return alert("比例需在 1–100");
  if(!g) return alert("请选择目标人群");
  snapshot();
  let moved=0;
  for(const cid of sel){
    const rs=rowsOf(cid);
    const tot=rs.reduce((s,p)=>s+p.amount,0);
    if(tot<=0) continue;
    const amt=Math.round(tot*pct/100*100)/100;
    moved+=amt;
    let need=amt;
    const ordered=rs.slice().sort((a,b)=>(a.group==="无认同人口"?0:1)-(b.group==="无认同人口"?0:1));
    for(const p of ordered){
      if(need<=0) break;
      const take=Math.min(p.amount, need);
      p.amount=Math.round((p.amount-take)*100)/100;
      need=Math.round((need-take)*100)/100;
    }
    const ex=pops.find(p=>p.city===cid && p.group===g);
    if(ex) ex.amount=Math.round((ex.amount+amt)*100)/100;
    else pops.push({id:"r"+Date.now().toString(36)+Math.floor(Math.random()*100),
                    city:cid, group:g, amount:amt, note:""});
  }
  syncPops(); save(); repaint();
  alert("已划分约 "+moved.toFixed(1)+" 万 → "+g);
}

/* ---------- 命中 ---------- */
function nearest(px,py){
  let best=null, bd=26*26;
  for(const it of items){
    if(it.del) continue;
    const s=toScreen(it.x,it.y);
    const d=(s[0]-px)*(s[0]-px)+(s[1]-py)*(s[1]-py);
    if(d<bd){ bd=d; best=it; }
  }
  return best;
}

/* ---------- 模式 ---------- */
function setMode(m){
  mode=m;
  ["sel","move","paint","add"].forEach(k=>{
    document.getElementById("m"+k[0].toUpperCase()+k.slice(1)).classList.toggle("on", k===m);
  });
  vp.className = m==="move" ? "movecur" : (m==="add" ? "addcur" : (m==="paint" ? "paintcur" : ""));
  apply();
}
function fitCanvas(){ cv.width=vp.clientWidth; cv.height=vp.clientHeight; }
window.addEventListener("resize",()=>{ fitCanvas(); });

/* ---------- 涂色 ---------- */
let painting=false, lastPt=null;
function paintTo(x,y){
  const b=46;
  ctx.strokeStyle="rgba(255,190,40,.45)"; ctx.fillStyle="rgba(255,190,40,.45)";
  ctx.lineWidth=b; ctx.lineCap="round"; ctx.lineJoin="round";
  if(lastPt){ ctx.beginPath(); ctx.moveTo(lastPt[0],lastPt[1]); ctx.lineTo(x,y); ctx.stroke(); }
  else { ctx.beginPath(); ctx.arc(x,y,b/2,0,Math.PI*2); ctx.fill(); }
  lastPt=[x,y];
}
cv.addEventListener("mousedown",e=>{ if(e.button!==0) return; e.preventDefault(); painting=true; lastPt=null;
  const r=cv.getBoundingClientRect(); paintTo(e.clientX-r.left, e.clientY-r.top); });
cv.addEventListener("mousemove",e=>{ if(!painting) return; const r=cv.getBoundingClientRect();
  paintTo(e.clientX-r.left, e.clientY-r.top); });
cv.addEventListener("mouseup",()=>{ if(!painting) return; painting=false; detectPaint(); });
function detectPaint(){
  const w=cv.width,h=cv.height,d=ctx.getImageData(0,0,w,h).data;
  sel.clear(); let hit=0;
  for(const it of items){
    if(it.del) continue;
    const s=toScreen(it.x,it.y), x=Math.round(s[0]), y=Math.round(s[1]);
    if(x<0||y<0||x>=w||y>=h) continue;
    if(d[(y*w+x)*4+3]>8){ sel.add(it.id); hit++; }
  }
  repaint();
}
function clearPaint(){ ctx.clearRect(0,0,cv.width,cv.height); }

/* ---------- 交互 ---------- */
let dragging=false, panning=false, moving=null, sx=0, sy=0, boxEl=null, base=null;

vp.addEventListener("contextmenu",e=>e.preventDefault());
vp.addEventListener("mousedown",e=>{
  if(e.button===2 || e.button===1 || e.altKey){ panning=true; sx=e.clientX; sy=e.clientY; vp.classList.add("pan"); e.preventDefault(); return; }
  if(e.button!==0) return;
  const r=vp.getBoundingClientRect(), px=e.clientX-r.left, py=e.clientY-r.top;
  if(mode==="add"){
    snapshot();
    const wx=(px-tx)/z, wy=(py-ty)/z;
    const id="x"+Date.now().toString(36);
    const it={id:id,name:"",kind:"邑",x:wx,y:wy,pop:1.2,t:0,oname:"",opop:1.2,ox:wx,oy:wy,del:false};
    items.push(it); byId[id]=it;
    pops.push({id:"r"+Date.now().toString(36), city:id, group:"无认同人口", amount:1.2, note:""});
    syncPops(); build();
    sel.clear(); sel.add(id); repaint();
    nameIn.value=""; nameIn.focus();
    return;
  }
  const it=nearest(px,py);
  if(mode==="move" && it){
    snapshot(); moving=it; sel.clear(); sel.add(it.id); repaint(); return;
  }
  if(it){
    if(!e.shiftKey) sel.clear();
    if(sel.has(it.id)&&e.shiftKey) sel.delete(it.id); else sel.add(it.id);
    repaint();
    const o=one();
    if(o){ nameIn.value=o.name; popIn.value=o.pop; }
    return;
  }
  dragging=true; base=new Set(sel); sx=px; sy=py;
  boxEl=document.createElement("div");
  boxEl.style.cssText="position:absolute;border:1px solid #ffe066;background:rgba(255,224,102,.15);pointer-events:none;z-index:12";
  boxEl.style.left=px+"px"; boxEl.style.top=py+"px";
  vp.appendChild(boxEl);
  if(!e.shiftKey){ sel.clear(); base.clear(); repaint(); }
});

window.addEventListener("mousemove",e=>{
  if(panning){ tx+=e.clientX-sx; ty+=e.clientY-sy; sx=e.clientX; sy=e.clientY; apply(); return; }
  if(moving){
    const r=vp.getBoundingClientRect();
    const wx=(e.clientX-r.left-tx)/z, wy=(e.clientY-r.top-ty)/z;
    moving.x=Math.round(wx*10)/10; moving.y=Math.round(wy*10)/10;
    const rad=RAD[moving.kind]||4.5;
    moving._mk.style.left=moving.x+"px"; moving._mk.style.top=moving.y+"px";
    moving._lb.style.left=moving.x+"px"; moving._lb.style.top=(moving.y+rad+2)+"px";
    moving._mk.classList.add("moved");
    return;
  }
  if(!dragging||!boxEl) return;
  const r=vp.getBoundingClientRect(), px=e.clientX-r.left, py=e.clientY-r.top;
  const x0=Math.min(sx,px), y0=Math.min(sy,py), w=Math.abs(px-sx), h=Math.abs(py-sy);
  boxEl.style.left=x0+"px"; boxEl.style.top=y0+"px";
  boxEl.style.width=w+"px"; boxEl.style.height=h+"px";
  const wx0=(x0-tx)/z, wy0=(y0-ty)/z, wx1=(x0+w-tx)/z, wy1=(y0+h-ty)/z;
  sel.clear(); for(const id of base) sel.add(id);
  for(const it of items) if(!it.del && it.x>=wx0&&it.x<=wx1&&it.y>=wy0&&it.y<=wy1) sel.add(it.id);
  repaint();
});

window.addEventListener("mouseup",()=>{
  if(moving){ save(); repaint(); moving=null; }
  panning=false; vp.classList.remove("pan");
  if(boxEl){ boxEl.remove(); boxEl=null; }
  dragging=false;
});

vp.addEventListener("wheel",e=>{
  e.preventDefault();
  const r=vp.getBoundingClientRect(), mx=e.clientX-r.left, my=e.clientY-r.top;
  const nz=Math.min(6,Math.max(0.12, z*(e.deltaY<0?1.15:1/1.15)));
  tx=mx-(mx-tx)*(nz/z); ty=my-(my-ty)*(nz/z); z=nz; apply();
},{passive:false});

nameIn.addEventListener("keydown",e=>{ if(e.key==="Enter"){ e.preventDefault(); applyName(); } });
popIn.addEventListener("keydown",e=>{ if(e.key==="Enter"){ e.preventDefault(); applyPop(); } });
window.addEventListener("keydown",e=>{
  if(e.target===nameIn||e.target===popIn) return;
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="z"){ e.preventDefault(); undo(); }
  if(e.key===" "){ e.preventDefault(); center(5000,3700,1.2); }
  if(e.key==="Escape") selNone();
  if(e.key==="Delete") delSel();
});

function exportCSV(){
  const rows=[["id","name","kind","x","y","pop","deleted","oname","opop","ox","oy"]];
  items.forEach(it=>rows.push([it.id,it.name,it.kind,it.x.toFixed(1),it.y.toFixed(1),
    it.pop.toFixed(2), it.del?1:0, it.oname, it.opop, it.ox.toFixed(1), it.oy.toFixed(1)]));
  const csv="\ufeff"+rows.map(r=>r.join(",")).join("\r\n");
  const a=document.createElement("a");
  a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"}));
  a.download="map_edited.csv"; a.click(); URL.revokeObjectURL(a.href);
}
function exportPops(){
  const rows=[["id","city_id","group","amount","note"]];
  pops.forEach(p=>rows.push([p.id,p.city,p.group,p.amount.toFixed(2),p.note||""]));
  const csv="\ufeff"+rows.map(r=>r.join(",")).join("\r\n");
  const a=document.createElement("a");
  a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"}));
  a.download="populations.csv"; a.click(); URL.revokeObjectURL(a.href);
}
function ownerCsv(){
  const rows=[["city_id","owner","note"]];
  items.forEach(it=>rows.push([it.id, owner[it.id]||"", ""]));
  return "\ufeff"+rows.map(r=>r.join(",")).join("\r\n");
}
function exportOwner(){
  const a=document.createElement("a");
  a.href=URL.createObjectURL(new Blob([ownerCsv()],{type:"text/csv;charset=utf-8"}));
  a.download="ownership.csv"; a.click(); URL.revokeObjectURL(a.href);
}
/* 绑定归属文件（自动保存） */
let ofh=null, otimer=null, owriting=false;
async function bindOwnerFile(){
  if(!window.showSaveFilePicker){ alert("需要 Chrome / Edge"); return; }
  try{
    ofh=await window.showSaveFilePicker({suggestedName:"ownership.csv",
      types:[{description:"CSV",accept:{"text/csv":[".csv"]}}]});
    await ownerWrite();
  }catch(e){ if(e.name!=="AbortError") alert("绑定失败："+e.message); }
}
async function ownerWrite(){
  if(!ofh||owriting) return; owriting=true;
  try{
    const w=await ofh.createWritable();
    await w.write(new Blob([ownerCsv()],{type:"text/csv"}));
    await w.close();
    const el=document.getElementById("fstat");
    if(el){ el.textContent="归属已保存 → "+ofh.name+"（"+new Date().toLocaleTimeString()+"）"; el.style.color="#7dd3a0"; }
  }catch(e){
    const el=document.getElementById("fstat");
    if(el){ el.textContent="归属写入失败："+e.message; el.style.color="#f0a8a8"; }
  }finally{ owriting=false; }
}
function ownerSchedule(){ if(!ofh) return; clearTimeout(otimer); otimer=setTimeout(ownerWrite,800); }

fitCanvas(); build(); center(5000,3700,1.2);
(function initNations(){
  const s=document.getElementById("ownNation");
  s.innerHTML = NATIONS.map(n=>`<option value="${n.id}">${n.name}</option>`).join("");
})();
/* 深链：#n0123 → 定位该城 */
(function deepLink(){
  const h = (location.hash || "").replace(/^#/, "");
  if (!h) return;
  const it = byId[h];
  if (it){ sel.clear(); sel.add(h); center(it.x, it.y, Math.max(z, 1.8)); repaint(); }
})();
</script></body></html>"""

html = (TPL.replace("__DATA__", json.dumps(items, ensure_ascii=False))
           .replace("__GROUPS__", json.dumps(groups, ensure_ascii=False))
           .replace("__POPS__", json.dumps(pops, ensure_ascii=False))
           .replace("__NATIONS__", json.dumps(nations, ensure_ascii=False))
           .replace("__OWNER__", json.dumps(owner, ensure_ascii=False))
           .replace("W_PX", str(W)).replace("H_PX", str(H)))

OUT.write_text(html.replace("__IMG__", "../../../ditu.png"), encoding="utf-8")

# 同步到分发包（地图用相对路径 ditu.png，本地版也一样放同目录）
import shutil
PKG = ROOT / "dist" / "map-review"
PKG.mkdir(parents=True, exist_ok=True)
(PKG / "map_editor.html").write_text(html.replace("__IMG__", "ditu.png"), encoding="utf-8")
shutil.copy2(ROOT / "ditu.png", PKG / "ditu.png")

print("items", len(items), "->", OUT, round(OUT.stat().st_size/1024), "KB")




