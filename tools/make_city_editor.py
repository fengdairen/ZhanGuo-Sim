# -*- coding: utf-8 -*-
"""生成城池编辑器 dist/map-review/city_editor.html（矢量底图 + 自动存盘）。

与描迹器同一套设计语言：左侧模式条 / 顶部操作条 / 右侧属性面板 / 图层浮层。
数据来自 data/map/*.csv，烘进页面；改动经 /api/map/save 自动存盘。
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist" / "map-review" / "city_editor.html"
W, H = 9101, 8509

PALETTE = ["#c0392b", "#2980b9", "#27ae60", "#8e44ad", "#d35400",
           "#16a085", "#2c3e50", "#c2185b", "#7f8c8d", "#f39c12",
           "#5d6d7e", "#a04000", "#1abc9c", "#9b59b6", "#e67e22"]


def read(name):
    p = ROOT / "data" / "map" / name
    if not p.exists():
        return []
    return list(csv.DictReader(p.open(encoding="utf-8-sig")))


def main():
    items = []
    for r in read("nodes.csv"):
        items.append({"id": r["id"], "name": r["name"], "kind": r["kind"],
                      "x": float(r["x"]), "y": float(r["y"]), "pop": float(r["pop"]),
                      "source": r.get("source", ""), "t": 0})
    for r in read("regions.csv"):
        items.append({"id": r["id"], "name": r["name"], "kind": "部族",
                      "x": float(r["x"]), "y": float(r["y"]), "pop": float(r["pop"]),
                      "source": r.get("source", ""), "t": 1})

    pops = [{"id": r["id"], "city": r["city_id"], "group": r["group"],
             "amount": float(r["amount"]), "note": r.get("note", "")}
            for r in read("populations.csv")]
    groups = [r["name"] for r in read("groups.csv")] or ["无认同人口"]

    state = json.loads((ROOT / "data" / "state.json").read_text(encoding="utf-8"))
    nations = [{"id": n["id"], "name": n["name"], "color": PALETTE[i % len(PALETTE)]}
               for i, n in enumerate(state["nations"])]
    owner = {}
    for r in read("ownership.csv"):
        if r.get("owner"):
            owner[r["city_id"]] = r["owner"]

    data = {"items": items, "pops": pops, "groups": groups,
            "nations": nations, "owner": owner, "size": [W, H]}

    html = (TPL
            .replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
            .replace("W_PX", str(W)).replace("H_PX", str(H)))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"城池 {len(items)} · 人口行 {len(pops)} · 国 {len(nations)} → {OUT} "
          f"{round(OUT.stat().st_size/1024)} KB")


TPL = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>战国演义 · 城池编辑器</title>
<style>
  :root{
    --paper:#f3e8cf; --card:#faf3e2; --ink:#33241a; --line:rgba(120,90,56,.28);
    --accent:#2d5d80; --desk:#54483a;
  }
  *{box-sizing:border-box}
  html,body{margin:0;height:100%;overflow:hidden;
    font:14px/1.6 "Songti SC","SimSun",serif;color:var(--ink);background:var(--desk)}
  body{display:flex;flex-direction:column}
  .panel{position:absolute;background:rgba(250,243,226,.97);border:1px solid var(--line);
    border-radius:8px;box-shadow:0 6px 22px rgba(40,26,12,.25)}
  button{font:inherit;font-size:13px;padding:6px 11px;border-radius:6px;cursor:pointer;
    border:1px solid var(--line);background:var(--card);color:var(--ink)}
  button:hover{border-color:var(--accent)}
  button.on{background:var(--accent);border-color:var(--accent);color:#fff}
  input,select{font:inherit;font-size:13px;padding:5px 8px;border-radius:6px;
    border:1px solid var(--line);background:#fffdf6;color:inherit;min-width:0}

  #cv{flex:1;display:block;width:100%;height:100%;background:#e9dbb8}
  #rail{top:12px;left:12px;width:62px;padding:6px 5px;display:flex;flex-direction:column;gap:5px;z-index:7}
  #rail button{width:100%;padding:9px 0;letter-spacing:1px}
  #bar{top:12px;left:86px;right:12px;padding:8px 10px;display:flex;align-items:center;
    gap:8px;z-index:6;flex-wrap:wrap}
  #bar .sp{flex:1}
  #q{width:190px}
  #layers{top:58px;left:86px;width:190px;padding:8px 10px;display:none;z-index:8;font-size:12.5px}
  #layers.on{display:block}
  #layers label{display:block;margin:5px 0;cursor:pointer}
  #layers i{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:2px}
  #side{top:12px;right:12px;width:314px;bottom:52px;overflow:auto;padding:0 0 10px;z-index:6}
  #side h2{font-size:12px;letter-spacing:2px;color:#8a7350;font-weight:400;
    margin:0;padding:10px 14px 6px;border-bottom:1px solid var(--line)}
  .fld{display:flex;align-items:center;gap:8px;padding:6px 14px}
  .fld > span:first-child{width:52px;color:#7a6547;font-size:12.5px;flex:none}
  .fld input,.fld select{flex:1}
  .hint{padding:4px 14px 10px;color:#9a8464;font-size:12px;line-height:1.6}
  #status{bottom:12px;left:12px;padding:6px 12px;font-size:12px;color:#5d4c37;z-index:6}
  #status b{color:var(--accent)}
  .poprow{display:flex;gap:6px;align-items:center;padding:4px 14px}
  .poprow select{width:96px;flex:none}
  .poprow input{width:70px;flex:none}
  .poprow .x{margin-left:auto;color:#a05040;cursor:pointer;font-size:12px}
  .k{color:#7a6547}
</style>
</head>
<body>
<canvas id="cv"></canvas>

<div id="rail" class="panel">
  <button class="mode on" data-m="sel" title="选择 / 拖动 / 框选（Esc 取消）">选择</button>
  <button class="mode" data-m="add" title="点空白处新增城池">新增</button>
  <button class="mode" data-m="paint" title="按住拖动，把刷到的城池改成当前归属">归属刷</button>
</div>

<div id="bar" class="panel">
  <input id="q" placeholder="搜索城池名，回车定位">
  <select id="paintNation" title="归属刷的目标国" style="display:none"></select>
  <button id="bFit">全图</button>
  <button id="bLayers">图层 ▾</button>
  <span class="sp"></span>
  <button id="bUndo" title="Ctrl+Z">撤销</button>
  <button id="bRedo" title="Ctrl+Shift+Z">重做</button>
  <button id="bMapCsv">导出地图</button>
  <button id="bPopCsv">导出人口</button>
  <button id="bOwnCsv">导出归属</button>
</div>

<div id="layers" class="panel">
  <label><input type="checkbox" id="lSea" checked><i style="background:#b2c4cb"></i>海面</label>
  <label><input type="checkbox" id="lLake" checked><i style="background:#8ec3d8"></i>湖泽</label>
  <label><input type="checkbox" id="lCoast" checked><i style="background:#40606f"></i>海岸线</label>
  <label><input type="checkbox" id="lRiver" checked><i style="background:#2e7fb0"></i>河网</label>
  <label><input type="checkbox" id="lCity" checked><i style="background:#8b2e1e"></i>城邑</label>
  <label><input type="checkbox" id="lName" checked>城名</label>
  <label><input type="checkbox" id="lTribe" checked><i style="background:#6b4a2f"></i>部族</label>
  <label><input type="checkbox" id="lOwner" checked>按归属着色</label>
</div>

<div id="side" class="panel">
  <h2>选中</h2>
  <div id="selBox"><div class="hint">点一个城池，或拖动框选。</div></div>
  <h2>人口明细</h2>
  <div id="popBox"><div class="hint">选中单个城池后显示。</div></div>
  <h2>统计</h2>
  <div class="hint" id="statBox"></div>
</div>

<div id="status" class="panel">
  城池 <b id="sCity">0</b> · 部族 <b id="sTribe">0</b> · 选中 <b id="sSel">0</b> ·
  缩放 <b id="sZoom">—</b> · <span id="sSave">—</span>
</div>

<script>
const DATA = __DATA__;
const W = W_PX, H = H_PX;

/* ---------- 状态 ---------- */
let items = DATA.items.map(d => Object.assign({}, d));
let pops  = DATA.pops.map(d => Object.assign({}, d));
const groups = DATA.groups.slice();
const nations = DATA.nations;
let owner = Object.assign({}, DATA.owner);

const S = {
  mode:'sel', sel:new Set(), layers:{sea:1,lake:1,coast:1,river:1,city:1,name:1,tribe:1,ownerColor:1},
  V:{sea:[],rivers:[],lakes:[],coasts:[]},
  scale:0.15, tx:0, ty:0, drag:null, box:null
};

const cv = document.getElementById('cv');
const ctx = cv.getContext('2d');
const $ = id => document.getElementById(id);
let dpr = Math.min(2, window.devicePixelRatio || 1);
let vw = 0, vh = 0;

/* ---------- 视图 ---------- */
function resize(){
  vw = cv.clientWidth; vh = cv.clientHeight;
  cv.width = Math.round(vw*dpr); cv.height = Math.round(vh*dpr);
  draw();
}
function w2s(x,y){ return [x*S.scale + S.tx, y*S.scale + S.ty]; }
function s2w(x,y){ return [(x - S.tx)/S.scale, (y - S.ty)/S.scale]; }
function fit(){
  S.scale = Math.min(vw/W, vh/H) * 0.96;
  S.tx = (vw - W*S.scale)/2; S.ty = (vh - H*S.scale)/2;
  draw();
}
function center(x,y,sc){
  if (sc) S.scale = sc;
  S.tx = vw/2 - x*S.scale; S.ty = vh/2 - y*S.scale;
  draw();
}

/* ---------- 绘制 ---------- */
const COL = { sea:'#b2c4cb', lake:'#8ec3d8', lakeEdge:'#3e7ca6', coast:'#40606f', river:'#2e7fb0',
              city:'#8b2e1e', county:'#6b4a2f', village:'#7a6248', tribe:'#6b4a2f' };
function pathOf(flat){ const p = new Path2D(); p.moveTo(flat[0], flat[1]);
  for (let i = 2; i < flat.length; i += 2) p.lineTo(flat[i], flat[i+1]); return p; }

function draw(){
  ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.fillStyle = '#e9dbb8'; ctx.fillRect(0,0,vw,vh);
  ctx.setTransform(dpr*S.scale,0,0,dpr*S.scale,dpr*S.tx,dpr*S.ty);

  if (S.layers.sea) for (const f of S.V.sea){ ctx.fillStyle = COL.sea; ctx.fill(pathOf(f)); }
  if (S.layers.lake){
    ctx.strokeStyle = COL.lakeEdge; ctx.lineWidth = 2.2/S.scale; ctx.fillStyle = COL.lake;
    for (const l of S.V.lakes){ const p = pathOf(l.pts); p.closePath(); ctx.fill(p); ctx.stroke(p); }
  }
  if (S.layers.coast){
    ctx.strokeStyle = COL.coast; ctx.lineWidth = Math.max(1, 4/S.scale); ctx.lineCap = 'round';
    for (const c of S.V.coasts){ const p = pathOf(c.pts); if (c.closed) p.closePath(); ctx.stroke(p); }
  }
  if (S.layers.river){
    ctx.strokeStyle = COL.river; ctx.lineJoin = 'round';
    for (const e of S.V.rivers){
      const p = new Path2D(); p.moveTo(e[1], e[2]);
      for (let i = 3; i < e.length; i += 2) p.lineTo(e[i], e[i+1]);
      ctx.lineWidth = Math.max(1.2/S.scale, e[0]); ctx.stroke(p);
    }
  }

  /* 城邑 / 部族 */
  ctx.setTransform(dpr,0,0,dpr,0,0);
  const showName = S.layers.name && S.scale > 0.32;
  ctx.font = '11px "Songti SC","SimSun",serif';
  ctx.textBaseline = 'middle';
  for (const it of items){
    if (it.t === 1 && !S.layers.tribe) continue;
    if (it.t === 0 && !S.layers.city) continue;
    const [sx, sy] = w2s(it.x, it.y);
    if (sx < -30 || sy < -30 || sx > vw+30 || sy > vh+30) continue;
    const n = owner[it.id];
    const nat = n ? nations.find(x => x.id === n) : null;
    const col = (S.layers.ownerColor && nat) ? nat.color
              : (it.kind === '都' ? COL.city : it.kind === '城' ? COL.county : COL.village);
    const sel = S.sel.has(it.id);
    const r = (it.kind === '都' ? 4.6 : it.kind === '城' ? 3.4 : it.t === 1 ? 3.4 : 2.2);
    ctx.beginPath(); ctx.arc(sx, sy, sel ? r + 2.5 : r, 0, 6.283);
    ctx.fillStyle = col; ctx.fill();
    if (sel){ ctx.strokeStyle = '#f0b400'; ctx.lineWidth = 2.4; ctx.stroke(); }
    if (showName || sel){
      const label = it.name;
      ctx.lineWidth = 3; ctx.strokeStyle = 'rgba(246,238,216,.92)';
      ctx.strokeText(label, sx + r + 3, sy + 1);
      ctx.fillStyle = 'rgba(60,45,30,.92)';
      ctx.fillText(label, sx + r + 3, sy + 1);
    }
  }

  if (S.box){
    ctx.setTransform(dpr,0,0,dpr,0,0);
    const x = Math.min(S.box.x0, S.box.x1), y = Math.min(S.box.y0, S.box.y1);
    const w = Math.abs(S.box.x1 - S.box.x0), h = Math.abs(S.box.y1 - S.box.y0);
    ctx.fillStyle = 'rgba(45,93,128,.12)'; ctx.fillRect(x,y,w,h);
    ctx.strokeStyle = 'rgba(45,93,128,.85)'; ctx.lineWidth = 1;
    ctx.strokeRect(x,y,w,h);
  }
  updateStatus();
}

/* ---------- 命中 ---------- */
function hit(wx, wy, px){
  const tol = (px || 9) / S.scale;
  let best = null;
  for (const it of items){
    if (it.t === 0 && !S.layers.city) continue;
    if (it.t === 1 && !S.layers.tribe) continue;
    const d = Math.hypot(it.x - wx, it.y - wy);
    if (d <= tol && (!best || d < best.d)) best = { it, d };
  }
  return best ? best.it : null;
}
function itemsInBox(x0,y0,x1,y1){
  const [ax, ay] = s2w(Math.min(x0,x1), Math.min(y0,y1));
  const [bx, by] = s2w(Math.max(x0,x1), Math.max(y0,y1));
  return items.filter(it => it.x >= ax && it.x <= bx && it.y >= ay && it.y <= by);
}

/* ---------- 存盘 ---------- */
let saveTimer = null, saving = false, lastSave = '';
function scheduleSave(){
  clearTimeout(saveTimer);
  saveTimer = setTimeout(pushSave, 700);
}
async function pushSave(){
  if (saving) return;
  saving = true;
  try{
    const body = JSON.stringify({ items, pops, owner, at: new Date().toISOString() });
    const r = await fetch('/api/map/save', { method:'POST',
      headers:{'Content-Type':'application/json'}, body });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    lastSave = new Date().toLocaleTimeString();
  }catch(e){
    lastSave = '存盘失败：' + e.message;
  }finally{
    saving = false;
    updateStatus();
  }
}

/* ---------- 撤销 ---------- */
const hist = [], fut = [];
function snap(){
  hist.push(JSON.stringify({ items, pops, owner }));
  if (hist.length > 60) hist.shift();
  fut.length = 0;
}
function undo(){
  if (!hist.length) return;
  fut.push(JSON.stringify({ items, pops, owner }));
  apply(JSON.parse(hist.pop()));
}
function redo(){
  if (!fut.length) return;
  hist.push(JSON.stringify({ items, pops, owner }));
  apply(JSON.parse(fut.pop()));
}
function apply(st){
  items = st.items; pops = st.pops; owner = st.owner;
  renderSel(); draw(); scheduleSave();
}

/* ---------- 交互 ---------- */
let spaceDown = false;
cv.addEventListener('contextmenu', e => e.preventDefault());
cv.addEventListener('pointerdown', e => {
  cv.setPointerCapture(e.pointerId);
  const r = cv.getBoundingClientRect();
  const mx = e.clientX - r.left, my = e.clientY - r.top;
  const [wx, wy] = s2w(mx, my);

  if (e.button === 2 || e.button === 1 || spaceDown || S.mode === 'pan'){
    S.drag = { type:'pan', mx, my, tx:S.tx, ty:S.ty };
    return;
  }
  if (S.mode === 'add'){
    snap();
    const id = 'n' + String(items.filter(i => i.t === 0).length + 1).padStart(4,'0');
    const it = { id, name:'新城', kind:'邑', x:wx, y:wy, pop:0.5, source:'新增', t:0 };
    items.push(it);
    pops.push({ id:'p' + Date.now(), city:id, group:groups[0], amount:0.5, note:'' });
    S.sel = new Set([id]);
    renderSel(); draw(); scheduleSave();
    return;
  }
  if (S.mode === 'paint'){
    const it = hit(wx, wy, 14);
    if (it && it.t === 0){
      snap();
      const nid = $('paintNation').value;
      if (nid) owner[it.id] = nid; else delete owner[it.id];
      S.drag = { type:'paint', snapped:true };
      draw(); scheduleSave();
    }
    return;
  }

  const it = hit(wx, wy);
  if (it){
    if (!e.shiftKey && !S.sel.has(it.id)) S.sel = new Set([it.id]);
    else if (e.shiftKey) S.sel.has(it.id) ? S.sel.delete(it.id) : S.sel.add(it.id);
    else S.sel = new Set([it.id]);
    S.drag = { type:'move', x0:wx, y0:wy, snapped:false, orig:[...S.sel].map(id => {
      const o = items.find(i => i.id === id); return { id, x:o.x, y:o.y };
    })};
    renderSel(); draw();
  } else {
    S.box = { x0:mx, y0:my, x1:mx, y1:my };
    S.sel = e.shiftKey ? S.sel : new Set();
    draw();
  }
});

cv.addEventListener('pointermove', e => {
  const r = cv.getBoundingClientRect();
  const mx = e.clientX - r.left, my = e.clientY - r.top;
  if (S.drag && S.drag.type === 'pan'){
    S.tx = S.drag.tx + (mx - S.drag.mx);
    S.ty = S.drag.ty + (my - S.drag.my);
    draw(); return;
  }
  const [wx, wy] = s2w(mx, my);
  if (S.drag && S.drag.type === 'move'){
    const dx = wx - S.drag.x0, dy = wy - S.drag.y0;
    if (!S.drag.snapped && (Math.abs(dx) > 0.01 || Math.abs(dy) > 0.01)){ S.drag.snapped = true; snap(); }
    for (const o of S.drag.orig){
      const it = items.find(i => i.id === o.id);
      if (it){ it.x = Math.round((o.x + dx)*10)/10; it.y = Math.round((o.y + dy)*10)/10; }
    }
    draw(); return;
  }
  if (S.drag && S.drag.type === 'paint'){
    const it = hit(wx, wy, 14);
    const nid = $('paintNation').value;
    if (it && it.t === 0 && (owner[it.id] || '') !== nid){
      if (nid) owner[it.id] = nid; else delete owner[it.id];
      draw();
    }
    return;
  }
  if (S.box){ S.box.x1 = mx; S.box.y1 = my; draw(); }
});

cv.addEventListener('pointerup', () => {
  if (S.drag && (S.drag.type === 'move' || S.drag.type === 'paint')){
    scheduleSave();
    renderSel();
  }
  if (S.box){
    const got = itemsInBox(S.box.x0, S.box.y0, S.box.x1, S.box.y1);
    S.sel = new Set(got.map(i => i.id));
    S.box = null;
    renderSel();
  }
  S.drag = null;
  draw();
});

cv.addEventListener('wheel', e => {
  e.preventDefault();
  const r = cv.getBoundingClientRect();
  const mx = e.clientX - r.left, my = e.clientY - r.top;
  const [wx, wy] = s2w(mx, my);
  const k = Math.exp(-e.deltaY * 0.0016);
  S.scale = Math.max(0.05, Math.min(6, S.scale * k));
  S.tx = mx - wx*S.scale; S.ty = my - wy*S.scale;
  draw();
}, { passive:false });

window.addEventListener('keydown', e => {
  const t = e.target;
  if (t && (t.tagName === 'INPUT' || t.tagName === 'SELECT')) return;
  if (e.code === 'Space'){ spaceDown = true; }
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z'){ e.preventDefault(); e.shiftKey ? redo() : undo(); }
  if (e.key === 'Escape'){ S.sel = new Set(); renderSel(); draw(); }
  if (e.key === '0') fit();
});
window.addEventListener('keyup', e => { if (e.code === 'Space') spaceDown = false; });

/* ---------- 右侧面板 ---------- */
function renderSel(){
  const box = $('selBox');
  const ids = [...S.sel];
  $('sSel').textContent = ids.length;
  if (!ids.length){
    box.innerHTML = '<div class="hint">点一个城池，或拖动框选。按住 Space 拖动可平移。</div>';
    renderPop(null);
    return;
  }
  if (ids.length > 1){
    box.innerHTML =
      '<div class="fld"><span>已选</span><b>' + ids.length + '</b> 个</div>' +
      '<div class="fld"><span>归属</span><select id="ownSel">' + nationOptions('') + '</select>' +
      '<button id="bSetOwn">应用</button></div>' +
      '<div class="fld"><span></span><button id="bDelSel">删除选中</button></div>';
    $('bSetOwn').onclick = () => {
      snap();
      const v = $('ownSel').value;
      for (const id of ids){ if (v) owner[id] = v; else delete owner[id]; }
      draw(); scheduleSave();
    };
    $('bDelSel').onclick = () => {
      if (!confirm('删除这 ' + ids.length + ' 个城池？')) return;
      snap();
      items = items.filter(i => !S.sel.has(i.id));
      pops = pops.filter(p => !S.sel.has(p.city));
      for (const id of ids) delete owner[id];
      S.sel = new Set();
      renderSel(); draw(); scheduleSave();
    };
    renderPop(null);
    return;
  }

  const it = items.find(i => i.id === ids[0]);
  if (!it){ S.sel = new Set(); return renderSel(); }
  box.innerHTML =
    '<div class="fld"><span>名称</span><input id="fName" value="' + esc(it.name) + '"></div>' +
    '<div class="fld"><span>类型</span><select id="fKind">' +
      ['都','城','邑','部族'].map(k => '<option' + (k === it.kind ? ' selected' : '') + '>' + k + '</option>').join('') +
    '</select></div>' +
    '<div class="fld"><span>归属</span><select id="ownSel">' + nationOptions(owner[it.id] || '') + '</select></div>' +
    '<div class="fld"><span>坐标</span><span class="k">' + it.x.toFixed(1) + ', ' + it.y.toFixed(1) + '</span></div>' +
    '<div class="fld"><span>人口</span><span class="k">' + popOf(it.id).toFixed(2) + '</span></div>' +
    '<div class="fld"><span></span><button id="bDelOne">删除</button></div>';

  $('fName').oninput = e => { it.name = e.target.value; draw(); scheduleSave(); };
  $('fKind').onchange = e => { snap(); it.kind = e.target.value; draw(); scheduleSave(); };
  $('ownSel').onchange = e => {
    snap();
    if (e.target.value) owner[it.id] = e.target.value; else delete owner[it.id];
    draw(); scheduleSave();
  };
  $('bDelOne').onclick = () => {
    snap();
    items = items.filter(i => i.id !== it.id);
    pops = pops.filter(p => p.city !== it.id);
    delete owner[it.id];
    S.sel = new Set(); renderSel(); draw(); scheduleSave();
  };
  renderPop(it);
}

function renderPop(it){
  const box = $('popBox');
  if (!it){
    box.innerHTML = '<div class="hint">选中单个城池后显示。</div>';
    return;
  }
  const rows = pops.filter(p => p.city === it.id);
  let html = rows.map(p =>
    '<div class="poprow" data-id="' + p.id + '">' +
      '<select>' + groups.map(g => '<option' + (g === p.group ? ' selected' : '') + '>' + g + '</option>').join('') + '</select>' +
      '<input type="number" step="0.1" value="' + p.amount + '">' +
      '<span class="x">✕</span>' +
    '</div>').join('');
  if (!rows.length) html = '<div class="hint">这个城池还没有人口行。</div>';
  html += '<div class="fld"><span></span><button id="bAddPop">添加一行</button></div>';
  box.innerHTML = html;

  box.querySelectorAll('.poprow').forEach(row => {
    const p = pops.find(x => x.id === row.dataset.id);
    row.querySelector('select').onchange = e => { snap(); p.group = e.target.value; scheduleSave(); };
    row.querySelector('input').oninput = e => {
      p.amount = parseFloat(e.target.value) || 0;
      const it2 = items.find(i => i.id === p.city);
      if (it2) it2.pop = popOf(it2.id);
      scheduleSave();
    };
    row.querySelector('.x').onclick = () => {
      snap(); pops = pops.filter(x => x !== p); renderSel(); draw(); scheduleSave();
    };
  });
  $('bAddPop').onclick = () => {
    snap();
    pops.push({ id:'p' + Date.now(), city:it.id, group:groups[0], amount:0, note:'' });
    renderSel(); draw(); scheduleSave();
  };
}

function popOf(id){ return pops.filter(p => p.city === id).reduce((s,p) => s + (p.amount||0), 0); }
function nationOptions(cur){
  return '<option value="">—</option>' + nations.map(n =>
    '<option value="' + n.id + '"' + (n.id === cur ? ' selected' : '') + '>' + n.name + '</option>').join('');
}
function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;'); }

function updateStatus(){
  $('sCity').textContent = items.filter(i => i.t === 0).length;
  $('sTribe').textContent = items.filter(i => i.t === 1).length;
  $('sSel').textContent = S.sel.size;
  $('sZoom').textContent = Math.round(S.scale*100) + '%';
  $('sSave').textContent = lastSave ? ('已存盘 ' + lastSave) : '未存盘';
  $('statBox').innerHTML =
    '已归属 ' + Object.keys(owner).length + ' / ' + items.filter(i => i.t === 0).length + ' 城<br>' +
    '人口行 ' + pops.length + ' 条 · 合计 ' + pops.reduce((s,p) => s + (p.amount||0), 0).toFixed(1) + ' 万';
}

/* ---------- 导出 ---------- */
function dl(name, text){
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], { type:'text/csv;charset=utf-8' }));
  a.download = name; a.click(); URL.revokeObjectURL(a.href);
}
function csvMap(){
  const rows = [["id","name","kind","x","y","pop"]];
  for (const it of items) rows.push([it.id, it.name, it.kind, it.x.toFixed(1), it.y.toFixed(1), it.pop.toFixed(2)]);
  return "\ufeff" + rows.map(r => r.join(",")).join("\r\n");
}
function csvPop(){
  const rows = [["id","city_id","group","amount","note"]];
  for (const p of pops) rows.push([p.id, p.city, p.group, p.amount, p.note || ""]);
  return "\ufeff" + rows.map(r => r.join(",")).join("\r\n");
}
function csvOwn(){
  const rows = [["city_id","owner","note"]];
  for (const it of items) if (it.t === 0) rows.push([it.id, owner[it.id] || "", ""]);
  return "\ufeff" + rows.map(r => r.join(",")).join("\r\n");
}

/* ---------- 顶栏 ---------- */
document.querySelectorAll('#rail .mode').forEach(b => {
  b.onclick = () => {
    S.mode = b.dataset.m;
    document.querySelectorAll('#rail .mode').forEach(x => x.classList.toggle('on', x === b));
    cv.style.cursor = S.mode === 'add' ? 'copy' : S.mode === 'paint' ? 'crosshair' : 'default';
    $('paintNation').style.display = S.mode === 'paint' ? '' : 'none';
  };
});
(function fillPaintNation(){
  const sel = $('paintNation');
  sel.innerHTML = '<option value="">— 无归属 —</option>' +
    nations.map(n => '<option value="' + n.id + '">' + n.name + '</option>').join('');
})();
$('bFit').onclick = fit;
$('bLayers').onclick = () => $('layers').classList.toggle('on');
$('bUndo').onclick = undo;
$('bRedo').onclick = redo;
$('bMapCsv').onclick = () => dl('map_edited.csv', csvMap());
$('bPopCsv').onclick = () => dl('populations.csv', csvPop());
$('bOwnCsv').onclick = () => dl('ownership.csv', csvOwn());

const LAYER_MAP = { lSea:'sea', lLake:'lake', lCoast:'coast', lRiver:'river',
                    lCity:'city', lName:'name', lTribe:'tribe', lOwner:'ownerColor' };
for (const [id, key] of Object.entries(LAYER_MAP)){
  const el = $(id);
  if (!el) continue;
  el.checked = !!S.layers[key];
  el.onchange = () => { S.layers[key] = el.checked; draw(); };
}

$('q').addEventListener('keydown', e => {
  if (e.key !== 'Enter') return;
  const q = e.target.value.trim();
  if (!q) return;
  const it = items.find(i => i.name === q) || items.find(i => i.name.includes(q));
  if (!it) { alert('没找到「' + q + '」'); return; }
  S.sel = new Set([it.id]);
  center(it.x, it.y, Math.max(S.scale, 0.8));
  renderSel();
});

window.addEventListener('resize', resize);

/* ---------- 调试 / 冒烟测试入口 ---------- */
window.__CITY_EDITOR__ = {
  S, draw, fit, center, renderSel, undo, redo, hit, w2s, s2w, popOf,
  csvMap, csvPop, csvOwn,
  get items(){ return items; },
  get pops(){ return pops; },
  get owner(){ return owner; }
};

/* ---------- 启动 ---------- */
(async function init(){
  resize(); fit();
  try{
    const r = await fetch('/api/vector', { cache:'no-store' });
    if (r.ok){
      const V = await r.json();
      S.V = { sea: V.sea || [], rivers: V.rivers || [], lakes: V.lakes || [], coasts: V.coasts || [] };
      draw();
    }
  }catch(e){}
  try{
    const r = await fetch('/api/map/load', { cache:'no-store' });
    if (r.ok){
      const a = await r.json();
      if (a && Array.isArray(a.items) && a.items.length){
        items = a.items; pops = a.pops || pops; owner = a.owner || owner;
        lastSave = '已从服务端恢复';
        draw(); updateStatus();
      }
    }
  }catch(e){}
  renderSel();

  // 深链：city_editor.html#n0231 → 选中并居中（控制台"在地图中打开"用）
  if (typeof location !== 'undefined' && location.hash){
    const id = location.hash.slice(1);
    const it = items.find(i => i.id === id);
    if (it){ S.sel = new Set([it.id]); center(it.x, it.y, Math.max(S.scale, 1.2)); renderSel(); }
  }
})();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
