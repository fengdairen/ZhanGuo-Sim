# -*- coding: utf-8 -*-
"""生成国界绘制器 dist/map-review/border_editor.html。

思路与河流描迹器一致：画边界线（吸附到海岸/河流/湖泊/其他边界线），
选中数条边界线后，自动用周围水系（海岸、河流、湖泊）补全成封闭疆域，
疆域指定国家后，其内部城邑自动改变归属。

产物：data/map/borders.json（边界线 + 疆域）
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "dist" / "map-review" / "border_editor.html"
BORDERS = ROOT / "data" / "map" / "borders.json"
W, H = 9101, 8509

PALETTE = ["#c0392b", "#2980b9", "#27ae60", "#8e44ad", "#d35400",
           "#16a085", "#2c3e50", "#c2185b", "#7f8c8d", "#f39c12",
           "#5d6d7e", "#a04000", "#1abc9c", "#9b59b6", "#e67e22"]


def read(name):
    p = ROOT / "data" / "map" / name
    return list(csv.DictReader(p.open(encoding="utf-8-sig"))) if p.exists() else []


def main():
    cities = [{"id": r["id"], "name": r["name"], "kind": r["kind"],
               "x": float(r["x"]), "y": float(r["y"])} for r in read("nodes.csv")]
    nations = []
    sp = ROOT / "data" / "state.json"
    if sp.exists():
        st = json.loads(sp.read_text(encoding="utf-8"))
        nations = [{"id": n["id"], "name": n["name"], "color": PALETTE[i % len(PALETTE)]}
                   for i, n in enumerate(st.get("nations", []))]

    state = {"version": 1, "canvas": [W, H], "edges": [], "realms": []}
    if BORDERS.exists():
        try:
            state = json.loads(BORDERS.read_text(encoding="utf-8-sig"))
        except Exception:
            pass

    owner = {}
    for r in read("ownership.csv"):
        if r.get("owner"):
            owner[r["city_id"]] = r["owner"]

    data = {"cities": cities, "nations": nations, "owner": owner,
            "borders": state, "palette": PALETTE, "size": [W, H]}

    html = (TPL.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
               .replace("W_PX", str(W)).replace("H_PX", str(H)))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"城邑 {len(cities)} · 国家 {len(nations)} · 边界 {len(state.get('edges', []))} "
          f"· 疆域 {len(state.get('realms', []))} → {OUT} {round(OUT.stat().st_size/1024)} KB")


TPL = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>战国演义 · 国界绘制器</title>
<style>
  :root{--paper:#f3e8cf;--card:#faf3e2;--ink:#33241a;--line:rgba(120,90,56,.28);
        --accent:#2d5d80;--desk:#54483a}
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
  button:disabled{opacity:.45;cursor:default}
  input,select{font:inherit;font-size:13px;padding:5px 8px;border-radius:6px;
    border:1px solid var(--line);background:#fffdf6;color:inherit;min-width:0}
  #cv{flex:1;display:block;width:100%;height:100%;background:#e9dbb8}
  #rail{top:12px;left:12px;width:64px;padding:6px 5px;display:flex;flex-direction:column;gap:5px;z-index:7}
  #rail button{width:100%;padding:9px 0;letter-spacing:1px}
  #bar{top:12px;left:88px;right:348px;padding:8px 10px;display:flex;align-items:center;
    gap:8px;z-index:6;flex-wrap:wrap}
  #bar .sp{flex:1}
  #layers{top:58px;left:88px;width:190px;padding:8px 10px;display:none;z-index:8;font-size:12.5px}
  #layers.on{display:block}
  #layers label{display:block;margin:5px 0;cursor:pointer}
  #side{top:12px;right:12px;width:326px;bottom:52px;overflow:auto;padding:0 0 10px;z-index:6}
  #side h2{font-size:12px;letter-spacing:2px;color:#8a7350;font-weight:400;
    margin:0;padding:10px 14px 6px;border-bottom:1px solid var(--line)}
  .fld{display:flex;align-items:center;gap:8px;padding:6px 14px}
  .fld > span:first-child{width:56px;color:#7a6547;font-size:12.5px;flex:none}
  .fld input,.fld select{flex:1}
  .hint{padding:4px 14px 10px;color:#9a8464;font-size:12px;line-height:1.7}
  .hint b{color:var(--accent)}
  #status{bottom:12px;left:12px;padding:6px 12px;font-size:12px;color:#5d4c37;z-index:6}
  #status b{color:var(--accent)}
  .erow{display:flex;align-items:center;gap:6px;padding:5px 14px;font-size:12.5px;
    border-bottom:1px solid rgba(120,90,56,.10)}
  .erow:last-child{border-bottom:none}
  .erow .x{color:#a05040;cursor:pointer;margin-left:auto;padding:0 4px;font-size:13px}
  .erow.sel{background:rgba(45,93,128,.07)}
  .tag{font-size:11px;padding:0 6px;border-radius:8px;border:1px solid var(--line);color:#8a7350}
  #mgr{position:fixed;inset:0;background:rgba(30,20,10,.45);display:none;
    align-items:center;justify-content:center;z-index:30}
  #mgr.on{display:flex}
  #mgrBox{background:var(--paper);border:1px solid var(--line);border-radius:10px;
    width:min(680px,92vw);max-height:80vh;overflow:auto;padding:18px 20px}
  #mgrBox h2{font-size:15px;margin:0 0 10px;letter-spacing:2px;color:var(--accent)}
  .mrow{display:flex;align-items:center;gap:6px;margin:6px 0}
  .mrow input[type=text]{flex:1;min-width:0}
  .mrow input[type=color]{width:32px;height:28px;padding:0;border:1px solid var(--line);border-radius:5px}
  .mrow .x{color:#a05040;cursor:pointer;padding:0 4px}
  .mhead{display:flex;gap:6px;font-size:11.5px;color:#8a7350;padding:0 2px}
  .mhead span:nth-child(1){width:32px}
  .mhead span:nth-child(2){flex:1}
  .mhead span:nth-child(3){flex:1}
  .mhead span:nth-child(4){width:14px}
  .mfoot{margin-top:14px;text-align:right}
  #toast{position:absolute;left:50%;top:70px;transform:translateX(-50%);padding:8px 16px;
    background:rgba(40,26,12,.86);color:#f3e8cf;border-radius:7px;font-size:13px;
    opacity:0;transition:.2s;pointer-events:none;z-index:30}
  #toast.on{opacity:1}
</style>
</head>
<body>
<canvas id="cv"></canvas>

<div id="rail" class="panel">
  <button class="mode on" data-m="sel" title="选择 / 拖动 / 框选">选择</button>
  <button class="mode" data-m="draw" title="普通边界线：起止点必须落在海岸/河流/湖泊/其他边界线上">画边界</button>
  <button class="mode" data-m="loop" title="闭环边界线：首尾自己咬上，端点不受水系约束">闭环</button>
</div>

<div id="bar" class="panel">
  <input id="q" placeholder="搜索城邑名，回车定位">
  <button id="bFit">全图</button>
  <button id="bLayers">图层 ▾</button>
  <span class="sp"></span>
  <button id="bUndo" title="Ctrl+Z">撤销</button>
  <button id="bRedo">重做</button>
  <button id="bRealm" disabled>生成疆域</button>
  <button id="bNations">国家…</button>
  <button id="bSave">存盘</button>
</div>

<div id="layers" class="panel">
  <label><input type="checkbox" id="lSea" checked>海面</label>
  <label><input type="checkbox" id="lLake" checked>湖泽</label>
  <label><input type="checkbox" id="lCoast" checked>海岸线</label>
  <label><input type="checkbox" id="lRiver" checked>河网</label>
  <label><input type="checkbox" id="lEdge" checked>边界线</label>
  <label><input type="checkbox" id="lFill" checked>疆域填充</label>
  <label><input type="checkbox" id="lCity" checked>城邑</label>
  <label><input type="checkbox" id="lName" checked>城名</label>
</div>

<div id="side" class="panel">
  <h2>边界线</h2>
  <div id="edgeBox"><div class="hint">用「画边界」画线。每条线的两端必须落在<b>海岸线 / 河流 / 湖泊 / 其他边界线</b>上。</div></div>
  <h2>疆域</h2>
  <div id="realmBox"><div class="hint">选中若干边界线后点「生成疆域」，系统会用周围水系自动补全缺口。</div></div>
  <h2>疆域清单</h2>
  <div id="listBox"><div class="hint">还没有疆域。</div></div>
</div>

<div id="mgr"><div id="mgrBox">
  <h2>国家</h2>
  <div class="hint" style="padding:0 0 8px">
    国号 = 齐、赵、魏（地图上标的名字）；国家 = 姜氏齐国、田氏齐国（同一国号的不同政权，各用各的数据）；
    颜色 = 地图疆域配色。
  </div>
  <div id="mgrNations"></div>
  <div class="mrow" style="margin-top:10px"><button id="bAddNation">＋ 新增国家</button></div>
  <div class="mfoot"><button id="bMgrClose">关闭</button></div>
</div></div>

<div id="status" class="panel">
  边界 <b id="sEdge">0</b> · 疆域 <b id="sRealm">0</b> · 选中 <b id="sSel">0</b> ·
  缩放 <b id="sZoom">—</b> · <span id="sSave">—</span>
</div>
<div id="toast"></div>

<script>
const DATA = __DATA__;
const W = W_PX, H = H_PX;

let edges  = (DATA.borders.edges  || []).map(e => Object.assign({}, e));
let realms = (DATA.borders.realms || []).map(r => Object.assign({}, r));
const PALETTE = DATA.palette || ['#c0392b','#2980b9','#27ae60','#8e44ad','#d35400'];
let nations = (DATA.nations || []).map(n => ({
  id: n.id, name: n.name || n.id, state: n.state || '', color: n.color || '#7a6248'
}));
let selRealmNation = null;   // 当前选中地块所属国家（同国一起高亮）
const cities = DATA.cities;
let owner = {};
for (const k in DATA.owner) owner[k] = { n: DATA.owner[k], f: '' };

const S = {
  mode:'sel', selEdge:new Set(), selRealm:null,
  layers:{sea:1,lake:1,coast:1,river:1,edge:1,fill:1,city:1,name:1},
  V:{sea:[],rivers:[],lakes:[],coasts:[]},
  scale:0.15, tx:0, ty:0, drag:null, box:null, cursor:null,
  draft:null, drawTarget:null
};

const cv = document.getElementById('cv');
const ctx = cv.getContext('2d');
const $ = id => document.getElementById(id);
let dpr = Math.min(2, window.devicePixelRatio || 1);
let vw = 0, vh = 0;

/* ================= 视图 ================= */
function resize(){ vw = cv.clientWidth; vh = cv.clientHeight;
  cv.width = Math.round(vw*dpr); cv.height = Math.round(vh*dpr); draw(); }
function w2s(x,y){ return [x*S.scale + S.tx, y*S.scale + S.ty]; }
function s2w(x,y){ return [(x - S.tx)/S.scale, (y - S.ty)/S.scale]; }
function fit(){ S.scale = Math.min(vw/W, vh/H)*0.96;
  S.tx = (vw - W*S.scale)/2; S.ty = (vh - H*S.scale)/2; draw(); }
function center(x,y,sc){ if (sc) S.scale = sc;
  S.tx = vw/2 - x*S.scale; S.ty = vh/2 - y*S.scale; draw(); }

/* ================= 图形数据 → 网络图 =================
   把海岸线、河流、湖泊边界、边界线都当成图的边；
   距离很近的端点自动焊接，于是"补全"就是在这张图上找最短路。 */
function flatten(a){ return (a.length && Array.isArray(a[0])) ? a.flat() : a; }
function flatToPts(f){ const p=[]; for(let i=0;i<f.length;i+=2) p.push([f[i],f[i+1]]); return p; }

let NET = null;

/* 把端点"焊"到网络上：在每条折线上插入端点投影点，再把折线拆成图边。
   extra 是必须先落到网络上的点（边界线的两端）。 */
function buildNet(extra, exclude){
  exclude = exclude || new Set();
  // 所有边界线的端点都要焊到水系上：之前只焊"选中的那几条"，
  // 于是别的边界线端点离水 0.04px 也连不上，补全自然找不到路。
  const weld = (extra || []).slice();
  for (const e of edges){
    if (!e.pts || e.pts.length < 2) continue;
    weld.push(e.pts[0], e.pts[e.pts.length - 1]);
  }
  extra = weld;
  const nodes = [], adj = [], grid = new Map();
  const CELL = 24;
  function idx(p){
    const cx = Math.floor(p[0]/CELL), cy = Math.floor(p[1]/CELL);
    let best = -1, bd = 1e9;
    for (let dx=-1; dx<=1; dx++) for (let dy=-1; dy<=1; dy++){
      const cell = grid.get((cx+dx)+','+(cy+dy));
      if (!cell) continue;
      for (const i of cell){
        const d = Math.hypot(nodes[i][0]-p[0], nodes[i][1]-p[1]);
        if (d < bd){ bd = d; best = i; }
      }
    }
    if (best >= 0 && bd <= 1.5) return best;
    const i = nodes.length; nodes.push([p[0], p[1]]); adj.push([]);
    const k = cx+','+cy;
    if (!grid.has(k)) grid.set(k, []);
    grid.get(k).push(i);
    return i;
  }
  function addLine(pts){
    // 先算出这条折线上要插入的投影点
    const ins = [];
    for (let i=0;i+1<pts.length;i++){
      const [x1,y1] = pts[i], [x2,y2] = pts[i+1];
      const dx = x2-x1, dy = y2-y1, L2 = dx*dx + dy*dy;
      if (L2 < 1e-9) continue;
      for (const q of extra){
        let t = ((q[0]-x1)*dx + (q[1]-y1)*dy) / L2;
        if (t <= 0.0001 || t >= 0.9999) continue;
        const px = x1+t*dx, py = y1+t*dy;
        const d = Math.hypot(px-q[0], py-q[1]);
        if (d <= 6) ins.push({i, t, pt:[px,py]});
      }
    }
    const out = [];
    for (let i=0;i+1<pts.length;i++){
      out.push(pts[i]);
      const here = ins.filter(x => x.i === i).sort((a,b) => a.t - b.t);
      for (const x of here) out.push(x.pt);
    }
    out.push(pts[pts.length-1]);

    const ids = out.map(idx);
    for (let i=0;i+1<ids.length;i++){
      const a = ids[i], b = ids[i+1];
      if (a === b) continue;
      const w = Math.hypot(nodes[a][0]-nodes[b][0], nodes[a][1]-nodes[b][1]);
      adj[a].push({to:b,w}); adj[b].push({to:a,w});
    }
  }
  for (const e of S.V.rivers) addLine(flatToPts(e.slice(1)));
  for (const c of S.V.coasts) addLine(flatToPts(c.pts));
  for (const l of S.V.lakes)  addLine(flatToPts(l.pts));
  // 选中的边界线不参与补全，否则补线就是那条线本身
  for (const e of edges) if (!exclude.has(e.id) && e.pts && e.pts.length > 1) addLine(e.pts);
  NET = {nodes, adj, idx};
  return NET;
}

function dijkstra(a, b){
  const {nodes, adj} = NET;
  const n = nodes.length;
  const dist = new Float64Array(n).fill(Infinity);
  const prev = new Int32Array(n).fill(-1);
  const done = new Uint8Array(n);
  dist[a] = 0;
  const pq = [[0, a]];
  const push = (d,i) => { pq.push([d,i]); let k=pq.length-1;
    while(k>0){ const p=(k-1)>>1; if(pq[p][0]<=pq[k][0]) break; [pq[p],pq[k]]=[pq[k],pq[p]]; k=p; } };
  const pop = () => { const top=pq[0], last=pq.pop();
    if (pq.length){ pq[0]=last; let k=0;
      for(;;){ let l=2*k+1, r=l+1, m=k;
        if(l<pq.length&&pq[l][0]<pq[m][0]) m=l;
        if(r<pq.length&&pq[r][0]<pq[m][0]) m=r;
        if(m===k) break; [pq[m],pq[k]]=[pq[k],pq[m]]; k=m; } }
    return top; };
  while (pq.length){
    const [d,u] = pop();
    if (done[u]) continue;
    done[u] = 1;
    if (u === b) break;
    for (const e of adj[u]){
      if (dist[u] + e.w < dist[e.to]){ dist[e.to] = dist[u] + e.w; prev[e.to] = u; push(dist[e.to], e.to); }
    }
  }
  if (!isFinite(dist[b])) return null;
  const path = []; let cur = b;
  while (cur !== -1){ path.push(nodes[cur]); cur = prev[cur]; }
  return {pts: path.reverse(), len: dist[b]};
}

/* 端点吸附：必须落在海岸线/河流/湖泊/其他边界线上 */
function snapTarget(wx, wy, tolPx, excludeEdgeId){
  const tol = tolPx / S.scale;
  let best = null;
  const consider = (kind, id, pts) => {
    for (let i=0;i<pts.length;i++){
      const d = Math.hypot(pts[i][0]-wx, pts[i][1]-wy);
      if (d <= tol && (!best || d < best.d)) best = {kind, id, idx:i, d, x:pts[i][0], y:pts[i][1]};
    }
    // 线段上（不是顶点）也可以
    for (let i=0;i+1<pts.length;i++){
      const [x1,y1]=pts[i], [x2,y2]=pts[i+1];
      const dx=x2-x1, dy=y2-y1, L2=dx*dx+dy*dy;
      if (!L2) continue;
      let t = ((wx-x1)*dx + (wy-y1)*dy) / L2;
      t = Math.max(0, Math.min(1, t));
      const px = x1+t*dx, py = y1+t*dy;
      const d = Math.hypot(px-wx, py-wy);
      if (d <= tol && (!best || d < best.d)) best = {kind, id, idx:i, t, d, x:px, y:py, onSeg:true};
    }
  };
  for (const c of S.V.coasts) consider('coast', c.id, flatToPts(c.pts));
  for (const l of S.V.lakes)  consider('lake',  l.id, flatToPts(l.pts));
  for (let i=0;i<S.V.rivers.length;i++) consider('river', 'r'+i, flatToPts(S.V.rivers[i].slice(1)));
  for (const e of edges){
    if (e.id === excludeEdgeId) continue;      // 别吸到自己身上
    consider('edge', e.id, e.pts);
  }
  return best;
}

/* ================= 疆域生成 =================
   1) 选中的边界线两两比较端点；
   2) 端点之间用网络最短路补全（缺口靠海岸/河流/湖泊）；
   3) 形成一个环：边界线 → 补线 → 边界线 → … → 回到起点。 */
function buildRealm(edgeIds){
  const sel = edges.filter(e => edgeIds.includes(e.id) && e.pts && e.pts.length > 1);
  if (!sel.length) return {error:'没有可用的边界线'};
  const extra = [];
  for (const e of sel){ extra.push(e.pts[0]); extra.push(e.pts[e.pts.length-1]); }
  NET = buildNet(extra, new Set(sel.map(e => e.id)));

  // 端点节点集
  const ends = [];
  for (const e of sel){
    const a = e.pts[0], b = e.pts[e.pts.length-1];
    ends.push({edge:e.id, side:0, pt:a, node:NET.idx(a)});
    ends.push({edge:e.id, side:1, pt:b, node:NET.idx(b)});
  }
  // 端点两两最短路（不同边界线之间，或同一线两端=闭环）
  const pairs = [];
  for (let i=0;i<ends.length;i++){
    for (let j=i+1;j<ends.length;j++){
      if (ends[i].edge === ends[j].edge && sel.length > 1) continue;
      const r = dijkstra(ends[i].node, ends[j].node);
      if (r) pairs.push({i, j, len:r.len, pts:r.pts});
    }
  }
  pairs.sort((a,b) => a.len - b.len);

  // 贪心匹配：每个端点只用一次
  const used = new Array(ends.length).fill(false);
  const link = new Array(ends.length).fill(null);
  for (const p of pairs){
    if (used[p.i] || used[p.j]) continue;
    used[p.i] = used[p.j] = true;
    link[p.i] = {other:p.j, pts:p.pts};
    link[p.j] = {other:p.i, pts:p.pts.slice().reverse()};
  }
  S.dbg = { ends: ends.map(e => ({edge:e.edge, side:e.side, node:e.node})), pairs: pairs.length,
            linked: link.filter(Boolean).length, bestLen: pairs[0] && pairs[0].len };
  const lonely = ends.filter((e,i) => !used[i]);
  if (lonely.length) return {error:'有 ' + lonely.length + ' 个端点无法与任何线相连（附近没有水系？）'};

  // 沿环走：边 → 补线 → 边 … → 回到起点
  const byId = {}; for (const e of sel) byId[e.id] = e;
  const idxOf = (edgeId, side) => ends.findIndex(x => x.edge === edgeId && x.side === side);
  const ring = [];
  const visited = new Set();
  let curEdge = sel[0], curEnd = 0;
  for (let guard = 0; guard <= sel.length + 1; guard++){
    const pts = curEnd === 0 ? curEdge.pts : curEdge.pts.slice().reverse();
    for (const p of pts) ring.push(p);
    visited.add(curEdge.id);

    const bEnd = idxOf(curEdge.id, 1 - curEnd);
    const L = link[bEnd];
    if (!L) return {error:'边界线未能闭合成环'};
    for (let i=1;i<L.pts.length;i++) ring.push(L.pts[i]);

    const next = ends[L.other];
    if (!next) return {error:'补线端点丢失'};
    if (next.edge === sel[0].id && next.side === 0) break;   // 回到起点，闭环
    if (visited.has(next.edge)) return {error:'边界线成环时提前重复，可能是两条线互相补成了同一条路'};
    curEdge = byId[next.edge]; curEnd = next.side;
    if (!curEdge) return {error:'找不到下一条边界线'};
  }
  if (ring.length < 4) return {error:'生成的环太小'};

  // 闭合与面积
  const first = ring[0], last = ring[ring.length-1];
  if (Math.hypot(first[0]-last[0], first[1]-last[1]) > 1) ring.push([first[0], first[1]]);
  let area = 0;
  for (let i=0;i+1<ring.length;i++) area += ring[i][0]*ring[i+1][1] - ring[i+1][0]*ring[i][1];
  area = Math.abs(area)/2;
  if (area < 500) return {error:'面积太小（' + Math.round(area) + ' px²），可能没围出区域'};
  return {ring, area, used:sel.map(e => e.id)};
}

function pointInPoly(p, poly){
  let c = false;
  for (let i=0, j=poly.length-1; i<poly.length; j=i++){
    const [x1,y1]=poly[i], [x2,y2]=poly[j];
    if (((y1>p[1]) !== (y2>p[1])) && (p[0] < (x2-x1)*(p[1]-y1)/(y2-y1) + x1)) c = !c;
  }
  return c;
}

/* ================= 绘制 ================= */
const COL = { sea:'#b2c4cb', lake:'#8ec3d8', lakeEdge:'#3e7ca6', coast:'#40606f', river:'#2e7fb0',
              edge:'#7a2e1e', city:'#6b4a2f' };
function pathOf(a){ const f = flatten(a); const p = new Path2D();
  p.moveTo(f[0], f[1]); for (let i=2;i<f.length;i+=2) p.lineTo(f[i], f[i+1]); return p; }

let bgCanvas = null, bgKey = '';
function bgState(){ return [S.scale,S.tx,S.ty,vw,vh,
  S.layers.sea?1:0,S.layers.lake?1:0,S.layers.coast?1:0,S.layers.river?1:0].join('|'); }
function drawBg(){
  const key = bgState();
  if (bgCanvas && key === bgKey){ ctx.setTransform(dpr,0,0,dpr,0,0);
    ctx.drawImage(bgCanvas,0,0,vw,vh); return; }
  bgKey = key;
  if (!bgCanvas) bgCanvas = document.createElement('canvas');
  bgCanvas.width = Math.round(vw*dpr); bgCanvas.height = Math.round(vh*dpr);
  const g = bgCanvas.getContext('2d');
  g.setTransform(dpr,0,0,dpr,0,0); g.fillStyle = '#e9dbb8'; g.fillRect(0,0,vw,vh);
  g.setTransform(dpr*S.scale,0,0,dpr*S.scale,dpr*S.tx,dpr*S.ty);
  if (S.layers.sea) for (const f of S.V.sea){ g.fillStyle = COL.sea; g.fill(pathOf(f)); }
  if (S.layers.lake){ g.strokeStyle = COL.lakeEdge; g.lineWidth = 2.2/S.scale; g.fillStyle = COL.lake;
    for (const l of S.V.lakes){ const p = pathOf(l.pts); p.closePath(); g.fill(p); g.stroke(p); } }
  if (S.layers.coast){ g.strokeStyle = COL.coast; g.lineWidth = Math.max(1,4/S.scale); g.lineCap='round';
    for (const c of S.V.coasts){ const p = pathOf(c.pts); if (c.closed) p.closePath(); g.stroke(p); } }
  if (S.layers.river){ g.strokeStyle = COL.river; g.lineJoin='round';
    for (const e of S.V.rivers){ const p = new Path2D(); p.moveTo(e[1],e[2]);
      for (let i=3;i<e.length;i+=2) p.lineTo(e[i],e[i+1]);
      g.lineWidth = Math.max(1.2/S.scale, e[0]); g.stroke(p); } }
  ctx.setTransform(dpr,0,0,dpr,0,0); ctx.drawImage(bgCanvas,0,0,vw,vh);
}

function draw(){
  S.draws = (S.draws||0)+1;
  drawBg();

  // 疆域填充
  if (S.layers.fill){
    ctx.setTransform(dpr*S.scale,0,0,dpr*S.scale,dpr*S.tx,dpr*S.ty);
    for (const r of realms){
      if (!r.ring || r.ring.length < 3) continue;
      const nat = nations.find(n => n.id === r.nation);
      const p = pathOf(r.ring); p.closePath();
      const sameNation = r.nation && selRealmNation && r.nation === selRealmNation;
      ctx.fillStyle = (nat ? nat.color : '#7a6248') + (sameNation ? '3d' : '2e');
      ctx.fill(p);
      ctx.strokeStyle = (nat ? nat.color : '#7a6248'); ctx.lineWidth = 2.5/S.scale; ctx.stroke(p);
    }
  }

  // 边界线
  ctx.setTransform(dpr,0,0,dpr,0,0);
  if (S.layers.edge){
    for (const e of edges){
      const sel = S.selEdge.has(e.id);
      ctx.beginPath();
      for (let i=0;i<e.pts.length;i++){
        const [sx,sy] = w2s(e.pts[i][0], e.pts[i][1]);
        i ? ctx.lineTo(sx,sy) : ctx.moveTo(sx,sy);
      }
      ctx.strokeStyle = sel ? '#d35400' : COL.edge;
      if (e.closed) ctx.closePath();
      ctx.lineWidth = sel ? 5.5 : 3.8; ctx.lineCap='round'; ctx.lineJoin='round'; ctx.stroke();
      if (sel){
        for (const pt of e.pts){
          const [vx,vy] = w2s(pt[0], pt[1]);
          ctx.beginPath(); ctx.arc(vx,vy,3.2,0,6.283);
          ctx.fillStyle = '#fff8e6'; ctx.fill();
          ctx.strokeStyle = '#d35400'; ctx.lineWidth = 1.6; ctx.stroke();
        }
      }
      for (const at of (e.ends || [])){
        const [sx,sy] = w2s(at.x, at.y);
        ctx.beginPath(); ctx.arc(sx,sy,3.4,0,6.283);
        ctx.fillStyle = at.ok ? '#3f8f6a' : '#b0503c'; ctx.fill();
      }
    }
  }

  // 草稿线：已确定的顶点连线 + 光标预览
  if (S.draft && S.draft.pts.length){
    ctx.beginPath();
    for (let i=0;i<S.draft.pts.length;i++){
      const [sx,sy] = w2s(S.draft.pts[i][0], S.draft.pts[i][1]);
      i ? ctx.lineTo(sx,sy) : ctx.moveTo(sx,sy);
    }
    ctx.strokeStyle = 'rgba(211,84,0,.9)'; ctx.lineWidth = 2.2; ctx.stroke();
    // 顶点
    for (const pt of S.draft.pts){
      const [sx,sy] = w2s(pt[0], pt[1]);
      ctx.beginPath(); ctx.arc(sx,sy,3,0,6.283); ctx.fillStyle = '#d35400'; ctx.fill();
    }
    // 到光标的预览
    const cur = S.draft.cursor;
    if (cur){
      const [ax,ay] = w2s(S.draft.pts[S.draft.pts.length-1][0], S.draft.pts[S.draft.pts.length-1][1]);
      const [bx,by] = w2s(cur[0], cur[1]);
      ctx.beginPath(); ctx.moveTo(ax,ay); ctx.lineTo(bx,by);
      ctx.setLineDash([5,5]); ctx.strokeStyle = 'rgba(211,84,0,.6)';
      ctx.lineWidth = 1.6; ctx.stroke(); ctx.setLineDash([]);
    }
  }
  // 吸附点提示
  if (S.drawTarget){
    const [sx,sy] = w2s(S.drawTarget.x, S.drawTarget.y);
    ctx.beginPath(); ctx.arc(sx,sy,5,0,6.283);
    ctx.strokeStyle = '#2d5d80'; ctx.lineWidth = 1.8; ctx.stroke();
  }

  // 城邑
  if (S.layers.city){
    const showName = S.layers.name && S.scale > 0.32;
    ctx.font = '11px "Songti SC","SimSun",serif'; ctx.textBaseline='middle';
    for (const c of cities){
      const [sx,sy] = w2s(c.x, c.y);
      if (sx<-20||sy<-20||sx>vw+20||sy>vh+20) continue;
      const ow = owner[c.id];
      const nat = ow && ow.n ? nations.find(n => n.id === ow.n) : null;
      ctx.beginPath(); ctx.arc(sx,sy, c.kind==='都'?3.6:2.4, 0, 6.283);
      ctx.fillStyle = nat ? nat.color : COL.city; ctx.fill();
      if (showName){
        ctx.lineWidth = 3; ctx.strokeStyle = 'rgba(246,238,216,.9)';
        ctx.strokeText(c.name, sx+5, sy+1);
        ctx.fillStyle = 'rgba(60,45,30,.9)'; ctx.fillText(c.name, sx+5, sy+1);
      }
    }
  }

  if (S.box){
    const x = Math.min(S.box.x0,S.box.x1), y = Math.min(S.box.y0,S.box.y1);
    const w = Math.abs(S.box.x1-S.box.x0), h = Math.abs(S.box.y1-S.box.y0);
    ctx.fillStyle = 'rgba(45,93,128,.12)'; ctx.fillRect(x,y,w,h);
    ctx.strokeStyle = 'rgba(45,93,128,.85)'; ctx.lineWidth = 1; ctx.strokeRect(x,y,w,h);
  }
  updateStatus();
}

/* ================= 交互 ================= */
function polyArea(ring){
  let a = 0;
  for (let i=0;i+1<ring.length;i++) a += ring[i][0]*ring[i+1][1] - ring[i+1][0]*ring[i][1];
  return Math.abs(a)/2;
}
function isClosedRing(pts){
  return pts.length >= 4 && Math.hypot(pts[0][0]-pts[pts.length-1][0], pts[0][1]-pts[pts.length-1][1]) <= 2;
}
// 顶点命中：选中的边界线优先
function vertexAt(wx, wy, px){
  const tol = (px||8)/S.scale;
  let best = null;
  const scan = (e) => {
    for (let i=0;i<e.pts.length;i++){
      const d = Math.hypot(e.pts[i][0]-wx, e.pts[i][1]-wy);
      if (d <= tol && (!best || d < best.d)) best = {edge:e, idx:i, d};
    }
  };
  for (const e of edges) if (S.selEdge.has(e.id)) scan(e);
  for (const e of edges) if (!S.selEdge.has(e.id)) scan(e);
  return best;
}

// 边界线改动后：受影响疆域重算几何 + 城邑归属
async function syncRealmsForEdge(edgeId){
  const e = edges.find(x => x.id === edgeId);
  if (!e) return;
  let touched = [], wrote = false;
  for (const r of realms){
    if (!r.edges || !r.edges.includes(edgeId)) continue;
    const oldRing = r.ring;
    if (r.edges.length === 1 && isClosedRing(e.pts)){
      r.ring = e.pts.slice();
      r.area = polyArea(r.ring);
    }else{
      const res = buildRealm(r.edges);
      if (res.error){ toast('疆域「' + (r.name || r.id) + '」重算失败：' + res.error); continue; }
      r.ring = res.ring; r.area = res.area;
    }
    touched.push(r);
    if (r.nation){
      for (const c of cities){
        const wasIn = oldRing ? pointInPoly([c.x, c.y], oldRing) : false;
        const nowIn = pointInPoly([c.x, c.y], r.ring);
        if (nowIn) { owner[c.id] = { n: r.nation, f:'' }; wrote = true; }
        else if (wasIn && owner[c.id] && owner[c.id].n === r.nation) { delete owner[c.id]; wrote = true; }
      }
    }
  }
  if (touched.length){
    draw(); renderSel(); renderList(); scheduleSave(); bgKey = '';
    if (wrote){
      const ok = await saveOwnership();
      if (ok === true) toast('疆域与城邑归属已跟随更新');
      else toast('疆域已更新，但归属写盘失败：' + ok);
    }
  }
}

function hitRealm(wx, wy){
  for (let i = realms.length-1; i >= 0; i--){
    const r = realms[i];
    if (r.ring && r.ring.length > 2 && pointInPoly([wx, wy], r.ring)) return r;
  }
  return null;
}
function hitEdge(wx, wy, px){
  const tol = (px||8)/S.scale;
  for (let i=edges.length-1;i>=0;i--){
    const e = edges[i];
    for (let k=0;k+1<e.pts.length;k++){
      const [x1,y1]=e.pts[k], [x2,y2]=e.pts[k+1];
      const dx=x2-x1, dy=y2-y1, L2=dx*dx+dy*dy || 1;
      let t = ((wx-x1)*dx + (wy-y1)*dy)/L2; t = Math.max(0,Math.min(1,t));
      if (Math.hypot(x1+t*dx-wx, y1+t*dy-wy) <= tol) return e;
    }
  }
  return null;
}

cv.addEventListener('contextmenu', e => e.preventDefault());
cv.addEventListener('pointerdown', e => {
  try{ cv.setPointerCapture(e.pointerId); }catch(_){}
  const r = cv.getBoundingClientRect();
  const mx = e.clientX-r.left, my = e.clientY-r.top;
  const [wx,wy] = s2w(mx,my);

  if (e.button === 1 || e.button === 2 || e.code === 'Space'){ S.drag = {type:'pan', mx, my, tx:S.tx, ty:S.ty}; return; }

  if (S.mode === 'loop'){
    if (!S.draft){
      const t = snapTarget(wx, wy, 16);
      S.draft = { pts:[[wx, wy]], loop:true, startSnap:t, cursor:null };
      draw(); return;
    }
    const first = S.draft.pts[0];
    const nearStart = Math.hypot(wx-first[0], wy-first[1]) <= 12/S.scale;
    if (S.draft.pts.length >= 3 && nearStart){ commitLoop(); return; }
    S.draft.pts.push([wx, wy]);
    S.draft.cursor = null;
    draw(); return;
  }

  if (S.mode === 'draw'){
    const t = snapTarget(wx, wy, 16);
    if (!S.draft){
      if (!t){ toast('起点必须落在海岸线 / 河流 / 湖泊 / 其他边界线上'); return; }
      S.draft = {pts:[[t.x, t.y]], start:t, end:null};
      draw(); return;
    }
    // 每点一次加一个顶点
    S.draft.pts.push(t ? [t.x, t.y] : [wx, wy]);
    S.draft.end = t || null;
    S.draft.cursor = null;
    draw(); return;
  }

  // 选择模式：顶点 → 边界线 → 疆域内部
  const v = vertexAt(wx, wy);
  if (v){
    snap();
    S.selEdge = new Set([v.edge.id]);
    S.selRealm = null;
    const n = v.edge.pts.length;
    const isEnd = !v.edge.closed && (v.idx === 0 || v.idx === n - 1);
    S.drag = { type:'vertex', edge:v.edge, idx:v.idx, moved:false,
               isEnd, orig:[v.edge.pts[v.idx][0], v.edge.pts[v.idx][1]] };
    renderSel(); draw(); return;
  }
  const ed = hitEdge(wx, wy);
  if (ed){
    if (e.shiftKey) S.selEdge.has(ed.id) ? S.selEdge.delete(ed.id) : S.selEdge.add(ed.id);
    else S.selEdge = new Set([ed.id]);
    S.selRealm = null;
    renderSel(); draw(); return;
  }
  const rp = hitRealm(wx, wy);
  if (rp){
    S.selEdge = new Set(rp.edges || []);
    S.selRealm = rp.id;
    renderSel(); renderList(); draw(); return;
  }
  S.box = {x0:mx, y0:my, x1:mx, y1:my}; S.selEdge = new Set(); S.selRealm = null;
  renderSel(); draw();
});

cv.addEventListener('pointermove', e => {
  const r = cv.getBoundingClientRect();
  const mx = e.clientX-r.left, my = e.clientY-r.top;
  const [wx,wy] = s2w(mx,my);
  S.cursor = [mx,my];
  if (S.drag && S.drag.type === 'pan'){
    S.tx = S.drag.tx + (mx - S.drag.mx); S.ty = S.drag.ty + (my - S.drag.my); draw(); return;
  }
  if (S.mode === 'loop'){
    if (S.draft) S.draft.cursor = [wx, wy];
    draw(); return;
  }
  if (S.mode === 'draw'){
    const t = snapTarget(wx, wy, 16);
    S.drawTarget = t;
    if (S.draft){ S.draft.cursor = t ? [t.x, t.y] : [wx, wy]; }
    draw(); return;
  }
  if (S.drag && S.drag.type === 'vertex'){
    const e = S.drag.edge;
    if (S.drag.isEnd){
      // 端点：只能落在水系/其他边界线上
      const t = snapTarget(wx, wy, 26, S.drag.edge.id);
      S.drawTarget = t;
      S.drag.snap = t;
      e.pts[S.drag.idx] = t ? [t.x, t.y] : [wx, wy];
    }else{
      e.pts[S.drag.idx] = [Math.round(wx*10)/10, Math.round(wy*10)/10];
    }
    S.drag.moved = true;
    draw(); return;
  }
  if (S.box){ S.box.x1 = mx; S.box.y1 = my; draw(); }
});

cv.addEventListener('pointerup', () => {
  if (S.drag && S.drag.type === 'vertex'){
    const d = S.drag, e = d.edge;
    S.drag = null; S.drawTarget = null;

    if (e.closed){
      // 闭环：首尾是同一个点，拖哪头都同步，且不需要吸附
      const n = e.pts.length;
      if (d.idx === 0) e.pts[n-1] = e.pts[0].slice();
      if (d.idx === n-1) e.pts[0] = e.pts[n-1].slice();
    }else if (d.isEnd){
      if (!d.snap){
        e.pts[d.idx] = d.orig;                 // 没吸上 → 还原
        toast('端点必须落在海岸线 / 河流 / 湖泊 / 其他边界线上，已还原');
        draw(); renderSel();
        return;
      }
      // 更新端点记录
      const k = d.idx === 0 ? 0 : 1;
      e.ends = e.ends || [{}, {}];
      e.ends[k] = {kind:d.snap.kind, id:d.snap.id, idx:d.snap.idx,
                   x:e.pts[d.idx][0], y:e.pts[d.idx][1], ok:true};
    }
    if (d.moved) syncRealmsForEdge(e.id);
    else draw();
    return;
  }
  if (S.box){
    const [ax,ay] = s2w(Math.min(S.box.x0,S.box.x1), Math.min(S.box.y0,S.box.y1));
    const [bx,by] = s2w(Math.max(S.box.x0,S.box.x1), Math.max(S.box.y0,S.box.y1));
    S.selEdge = new Set(edges.filter(e => e.pts.some(p => p[0]>=ax&&p[0]<=bx&&p[1]>=ay&&p[1]<=by)).map(e => e.id));
    S.box = null; renderSel(); draw();
  }
  S.drag = null;
});

cv.addEventListener('wheel', e => {
  e.preventDefault();
  const r = cv.getBoundingClientRect();
  const mx = e.clientX-r.left, my = e.clientY-r.top;
  const [wx,wy] = s2w(mx,my);
  const k = Math.exp(-e.deltaY*0.0016);
  S.scale = Math.max(0.04, Math.min(6, S.scale*k));
  S.tx = mx - wx*S.scale; S.ty = my - wy*S.scale;
  bgKey = ''; draw();
}, {passive:false});

cv.addEventListener('dblclick', e => { if (S.mode === 'draw' && S.draft) commitDraft(); });

window.addEventListener('keydown', e => {
  const t = e.target;
  if (t && (t.tagName==='INPUT'||t.tagName==='SELECT')) return;
  if (e.key === 'Escape'){ S.draft = null; S.selEdge = new Set(); S.selRealm = null; renderSel(); draw(); }
  if (e.key === 'Enter' && S.draft){ S.mode === 'loop' ? commitLoop() : commitDraft(); }
  if (e.key === 'Backspace' && S.draft){
    e.preventDefault();
    if (S.draft.pts.length > 1){ S.draft.pts.pop(); S.draft.end = null; }
    else { S.draft = null; }
    draw();
  }
  if ((e.ctrlKey||e.metaKey) && e.key.toLowerCase()==='z'){ e.preventDefault(); undo(); }
  if (e.key === '0') fit();
});

/* ================= 草稿 ================= */
function commitDraft(){
  const d = S.draft;
  if (!d || d.pts.length < 2){ toast('至少要两个点'); return; }
  if (!d.start){ toast('起点没有吸附到水系上'); return; }
  if (!d.end){ toast('终点必须吸附到海岸线 / 河流 / 湖泊 / 其他边界线上'); return; }
  if (d.pts.length < 2) return;
  snap();
  const id = 'b' + String(edges.length + 1).padStart(3,'0');
  edges.push({ id, pts:d.pts.map(p => [Math.round(p[0]*10)/10, Math.round(p[1]*10)/10]),
               ends:[{kind:d.start.kind, id:d.start.id, idx:d.start.idx, x:d.start.x, y:d.start.y, ok:true},
                     {kind:d.end.kind, id:d.end.id, idx:d.end.idx, x:d.end.x, y:d.end.y, ok:true}] });
  S.draft = null; scheduleSave(); renderSel(); draw();
}

// 闭环工具：首尾自己咬上就成环；起点如果落在已知点上，拒绝生成
function commitLoop(){
  const d = S.draft;
  if (!d || d.pts.length < 3){ toast('闭环至少要三个点'); return; }
  if (d.startSnap){
    toast('起点落在已知点（' + d.startSnap.kind + '）上，请改用「画边界」');
    S.draft = null; draw(); return;
  }
  const ring = d.pts.concat([[d.pts[0][0], d.pts[0][1]]]).map(
    p => [Math.round(p[0]*10)/10, Math.round(p[1]*10)/10]);
  const area = polyArea(ring);
  if (area < 500){ toast('这个环太小（' + Math.round(area) + ' px²）'); return; }
  snap();
  const id = 'b' + String(edges.length + 1).padStart(3,'0');
  edges.push({ id, closed:true, pts:ring, ends:[] });
  S.draft = null;
  scheduleSave(); renderSel(); draw();
  toast('闭环边界线已生成：' + Math.round(area).toLocaleString() + ' px²');
}

/* ================= 侧栏 ================= */
function renderSel(){
  const box = $('edgeBox');
  const ids = [...S.selEdge];
  $('sSel').textContent = ids.length;
  $('bRealm').disabled = ids.length < 1;
  if (!ids.length){
    box.innerHTML = '<div class="hint">用「画边界」画线。每条线的两端必须落在<b>海岸线 / 河流 / 湖泊 / 其他边界线</b>上。<br>画完可框选多条线，再点「生成疆域」。</div>';
    renderRealmBox();
    return;
  }
  box.innerHTML = ids.map(id => {
    const e = edges.find(x => x.id === id);
    const a = e.ends ? e.ends[0] : null, b = e.ends ? e.ends[1] : null;
    const lab = x => x ? (x.kind === 'river' ? '河' : x.kind === 'coast' ? '岸' : x.kind === 'lake' ? '湖' : '界') : '—';
    return '<div class="erow" data-id="' + id + '"><span class="tag">' + id + '</span>' +
      '长 ' + Math.round(polyLen(e.pts)) + 'px · ' + (e.closed ? '闭环' : ('两端 ' + lab(a) + '/' + lab(b))) +
      '<span class="x">✕</span></div>';
  }).join('') +
  '<div class="fld"><button id="bDelEdge" style="flex:1">删除选中的 ' + ids.length + ' 条边界线</button></div>';
  box.querySelectorAll('.erow').forEach(row => {
    row.querySelector('.x').onclick = () => {
      snap(); edges = edges.filter(e => e.id !== row.dataset.id);
      S.selEdge.delete(row.dataset.id); scheduleSave(); renderSel(); draw();
    };
  });
  $('bDelEdge').onclick = () => {
    snap(); edges = edges.filter(e => !S.selEdge.has(e.id));
    S.selEdge = new Set(); scheduleSave(); renderSel(); draw();
  };
  renderRealmBox();
}
function polyLen(pts){ let s=0; for(let i=0;i+1<pts.length;i++) s += Math.hypot(pts[i+1][0]-pts[i][0], pts[i+1][1]-pts[i][1]); return s; }

function renderRealmBox(){
  const box = $('realmBox');
  const ids = [...S.selEdge];
  if (S.selRealm){
    const r = realms.find(x => x.id === S.selRealm);
    if (!r){ S.selRealm = null; return renderRealmBox(); }
    box.innerHTML =
      '<div class="fld"><span>名称</span><input id="rName" value="' + esc(r.name||'') + '"></div>' +
      '<div class="fld"><span>国家</span><input id="rNation" list="natList" placeholder="选或直接输入国名"' +
        ' value="' + esc((nations.find(n => n.id === r.nation) || {}).name || '') + '"></div>' +
      '<datalist id="natList">' + nations.map(n =>
        '<option value="' + esc(n.name) + '">' + esc(n.state || '') + '</option>').join('') + '</datalist>' +
      '<div class="fld"><span>地方</span><input id="rFaction" value="' + esc(r.faction||'') + '" placeholder="留空 = 中央直辖"></div>' +
      '<div class="fld"><span>面积</span><span class="tag">' + Math.round(r.area||0).toLocaleString() + ' px²</span></div>' +
      '<div class="fld"><span>城邑</span><span id="rCount" class="tag">—</span></div>' +
      '<div class="fld"><span></span><button id="bApply">应用归属</button><button id="bDelRealm">删除疆域</button></div>';
    $('rName').oninput = e => { r.name = e.target.value; scheduleSave(); renderList(); };
    $('rNation').onchange = e => {
      const txt = (e.target.value || '').trim();
      if (!txt){ r.nation = ''; }
      else {
        let hit = nations.find(n => n.name === txt || n.state === txt || n.id === txt);
        if (!hit){
          hit = { id: 'N' + Date.now().toString(36), name: txt, state: '',
                  color: PALETTE[nations.length % PALETTE.length] };
          nations.push(hit);
          toast('已新建国家「' + txt + '」，可在「国家…」里补全称');
          if ($('mgr').classList.contains('on')) renderMgr();
        }
        r.nation = hit.id;
      }
      scheduleSave(); draw(); renderList(); fillRealmCount(r);
      renderRealmBox();
    };
    $('rFaction').oninput = e => { r.faction = e.target.value; scheduleSave(); };
    $('bApply').onclick = () => applyRealm(r);
    $('bDelRealm').onclick = () => {
      if (!confirm('删除疆域？里面的城邑会变回无归属。')) return;
      dropRealm(r);
    };
    fillRealmCount(r);
    return;
  }
  if (!ids.length){ box.innerHTML = '<div class="hint">选中若干边界线后点「生成疆域」，系统会用周围水系自动补全缺口。</div>'; return; }
  box.innerHTML = '<div class="hint">已选 <b>' + ids.length + '</b> 条边界线。点顶部「生成疆域」自动补全缺口。</div>';
}
function fillRealmCount(r){
  const el = $('rCount'); if (!el || !r.ring) return;
  const n = cities.filter(c => pointInPoly([c.x,c.y], r.ring)).length;
  el.textContent = n + ' 城';
}
function renderList(){
  const box = $('listBox');
  if (!realms.length){ box.innerHTML = '<div class="hint">还没有疆域。</div>'; return; }
  box.innerHTML = realms.map(r => {
    const nat = nations.find(n => n.id === r.nation);
    const label = nat ? (nat.state ? (nat.name + '·' + nat.state) : nat.name) : '未定';
    return '<div class="erow" data-id="' + r.id + '">' +
      '<span class="tag">' + label + '</span> ' + (r.name || r.id) +
      ' <span class="tag">' + (r.edges ? r.edges.length : 0) + ' 段</span>' +
      '<span class="x">✕</span></div>';
  }).join('');
  box.querySelectorAll('.erow').forEach(row => {
    row.onclick = ev => {
      if (ev.target.classList.contains('x')) return;
      S.selRealm = row.dataset.id;
      const r = realms.find(x => x.id === S.selRealm);
      if (r && r.ring) center(r.ring[0][0], r.ring[0][1], Math.max(S.scale, 0.5));
      renderSel(); draw();
    };
    row.querySelector('.x').onclick = () => {
      const r = realms.find(x => x.id === row.dataset.id);
      if (r && confirm('删除疆域「' + (r.name || r.id) + '」？里面的城邑会变回无归属。')) dropRealm(r);
    };
  });
}

/* ================= 生成 & 应用 ================= */
function doBuildRealm(){
  const ids = [...S.selEdge];
  if (!ids.length){ toast('先选中边界线'); return; }

  // 单条自身闭合的边界线：直接当疆域，不需要补全
  if (ids.length === 1){
    const e = edges.find(x => x.id === ids[0]);
    const a0 = e.pts[0], a1 = e.pts[e.pts.length-1];
    if (e.pts.length >= 4 && (e.closed || Math.hypot(a0[0]-a1[0], a0[1]-a1[1]) <= 2)){
      const ring = e.pts.slice();
      let area = 0;
      for (let i=0;i+1<ring.length;i++) area += ring[i][0]*ring[i+1][1] - ring[i+1][0]*ring[i][1];
      area = Math.abs(area)/2;
      if (area < 500){ toast('这个环太小（' + Math.round(area) + ' px²）'); return; }
      snap();
      const id = 'q' + (realms.length + 1);
      realms.push({ id, name:'新疆域', nation:'', edges:[e.id], ring, area });
      S.selRealm = id;
      toast('闭合边界线已转为疆域：' + Math.round(area).toLocaleString() + ' px²');
      scheduleSave(); renderSel(); renderList(); draw();
      return;
    }
  }

  const r = buildRealm(ids);
  if (r.error){ toast(r.error); return; }
  snap();
  const id = 'q' + (realms.length + 1);
  const realm = { id, name:'新疆域', nation:'', edges:r.used, ring:r.ring, area:r.area };
  realms.push(realm);
  S.selRealm = id;
  toast('疆域已生成：面积 ' + Math.round(r.area).toLocaleString() + ' px²');
  scheduleSave(); renderSel(); renderList(); draw();
}

async function saveOwnership(){
  try{
    const res = await fetch('/api/ownership/save', { method:'POST',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify({ owner }) });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return true;
  }catch(e){ return e.message; }
}

async function applyRealm(r){
  if (!r.nation){ toast('先指定国家'); return; }
  snap();
  let n = 0;
  for (const c of cities){
    if (pointInPoly([c.x, c.y], r.ring)){ owner[c.id] = { n: r.nation, f: r.faction || '' }; n++; }
  }
  const nm = (nations.find(x => x.id === r.nation) || {}).name || r.nation;
  draw();
  const ok = await saveOwnership();
  toast(ok === true ? (n + ' 个城邑已归入 ' + nm + '，ownership.csv 已更新')
                    : (n + ' 个城邑已归入 ' + nm + '（写盘失败：' + ok + '）'));
}

// 删疆域 → 里面的城池变无归属
async function dropRealm(r){
  snap();
  let n = 0;
  for (const c of cities){
    if (pointInPoly([c.x, c.y], r.ring) && owner[c.id] && owner[c.id].n === r.nation){
      delete owner[c.id]; n++;
    }
  }
  realms = realms.filter(x => x !== r);
  if (S.selRealm === r.id) S.selRealm = null;
  draw(); renderSel(); renderList(); scheduleSave();
  const ok = await saveOwnership();
  toast(ok === true ? ('疆域已删除，' + n + ' 个城邑改为无归属')
                    : ('疆域已删除，' + n + ' 城改无归属（写盘失败：' + ok + '）'));
}

/* ================= 存盘 ================= */
let saveTimer=null, saving=false, lastSave='';
function scheduleSave(){ clearTimeout(saveTimer); saveTimer = setTimeout(pushSave, 700); }
async function pushSave(){
  if (saving) return; saving = true;
  try{
    const body = JSON.stringify({version:1, canvas:[W,H], edges, realms, nations});
    const r = await fetch('/api/borders/save', {method:'POST',
      headers:{'Content-Type':'application/json'}, body});
    if (!r.ok) throw new Error('HTTP ' + r.status);
    lastSave = new Date().toLocaleTimeString();
  }catch(e){ lastSave = '存盘失败：' + e.message; }
  finally{ saving = false; updateStatus(); }
}

/* ================= 撤销 ================= */
const hist = [], fut = [];
function snap(){ hist.push(JSON.stringify({edges, realms})); if (hist.length>40) hist.shift(); fut.length = 0; }
function applyState(s){ const o = JSON.parse(s); edges = o.edges; realms = o.realms; draw(); renderSel(); renderList(); scheduleSave(); }
function undo(){ if(!hist.length) return; fut.push(JSON.stringify({edges,realms})); applyState(hist.pop()); }
function redo(){ if(!fut.length) return; hist.push(JSON.stringify({edges,realms})); applyState(fut.pop()); }

/* ================= 国家管理 ================= */
function renderMgr(){
  const box = $('mgrNations');
  if (!nations.length){
    box.innerHTML = '<div class="hint">还没有国家，点下面新增。</div>';
    return;
  }
  box.innerHTML = '<div class="mhead"><span></span><span>国号</span><span>国家</span><span></span></div>' +
    nations.map(n =>
      '<div class="mrow" data-id="' + n.id + '">' +
        '<input type="color" value="' + n.color + '">' +
        '<input type="text" value="' + esc(n.name) + '" placeholder="齐">' +
        '<input type="text" value="' + esc(n.state || '') + '" placeholder="田氏齐国">' +
        '<span class="x" title="删除">✕</span>' +
      '</div>').join('');
  box.querySelectorAll('.mrow').forEach(row => {
    const n = nations.find(x => x.id === row.dataset.id);
    const [c, nm, st] = row.querySelectorAll('input');
    c.oninput = () => { n.color = c.value; draw(); scheduleSave(); };
    nm.oninput = () => { n.name = nm.value; scheduleSave(); if (S.selRealm) renderSel(); };
    st.oninput = () => { n.state = st.value; scheduleSave(); if (S.selRealm) renderSel(); };
    row.querySelector('.x').onclick = () => {
      if (!confirm('删除国家「' + (n.state || n.name) + '」？相关地块会变成未定。')) return;
      snap();
      nations = nations.filter(x => x !== n);
      for (const r of realms) if (r.nation === n.id) r.nation = '';
      renderMgr(); renderSel(); renderList(); draw(); scheduleSave();
    };
  });
}
$('bNations').onclick = () => { renderMgr(); $('mgr').classList.add('on'); };
$('bMgrClose').onclick = () => $('mgr').classList.remove('on');
$('mgr').onclick = e => { if (e.target.id === 'mgr') $('mgr').classList.remove('on'); };
$('bAddNation').onclick = () => {
  snap();
  nations.push({ id:'N' + Date.now().toString(36), name:'新国号', state:'新国家',
                 color: PALETTE[nations.length % PALETTE.length] });
  renderMgr(); scheduleSave();
};

/* ================= 杂项 ================= */
function toast(msg){ const t = $('toast'); t.textContent = msg; t.classList.add('on');
  clearTimeout(t._t); t._t = setTimeout(() => t.classList.remove('on'), 2200); }
function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;'); }
function updateStatus(){
  $('sEdge').textContent = edges.length;
  $('sRealm').textContent = realms.length;
  $('sZoom').textContent = Math.round(S.scale*100) + '%';
  $('sSave').textContent = lastSave ? ('已存盘 ' + lastSave) : '未存盘';
}

/* ================= 启动 ================= */
document.querySelectorAll('#rail .mode').forEach(b => {
  b.onclick = () => {
    S.mode = b.dataset.m;
    if (S.mode === 'draw' && S.draft){ S.draft = null; }
    document.querySelectorAll('#rail .mode').forEach(x => x.classList.toggle('on', x===b));
    cv.style.cursor = S.mode==='draw' ? 'crosshair' : 'default';
    if (S.mode !== 'draw'){ S.draft = null; }
    draw();
  };
});
$('bFit').onclick = fit;
$('bLayers').onclick = () => $('layers').classList.toggle('on');
$('bUndo').onclick = undo;
$('bRedo').onclick = redo;
$('bRealm').onclick = doBuildRealm;
$('bSave').onclick = pushSave;
const LM = {lSea:'sea',lLake:'lake',lCoast:'coast',lRiver:'river',lEdge:'edge',lFill:'fill',lCity:'city',lName:'name'};
for (const [id,key] of Object.entries(LM)){
  const el = $(id); if (!el) continue;
  el.checked = !!S.layers[key];
  el.onchange = () => { S.layers[key] = el.checked; bgKey=''; draw(); };
}
$('q').addEventListener('keydown', e => {
  if (e.key === 'Enter'){
    const q = e.target.value.trim(); if (!q) return;
    const c = cities.find(x => x.name === q) || cities.find(x => x.name.includes(q));
    if (!c){ toast('没找到「' + q + '」'); return; }
    center(c.x, c.y, Math.max(S.scale, 0.8));
  }
});
window.addEventListener('resize', resize);

window.__BORDER_EDITOR__ = {
  S, draw, fit, center, w2s, s2w, snapTarget, buildRealm, buildNet, pointInPoly, dijkstra, commitDraft,
  doBuildRealm, applyRealm, dropRealm, commitLoop, hitRealm, syncRealmsForEdge, vertexAt, polyArea, isClosedRing, undo, redo,
  get edges(){ return edges; }, get realms(){ return realms; }, get owner(){ return owner; },
  get cities(){ return cities; }, get nations(){ return nations; },
  setVector(V){ S.V = V; bgKey = ''; },
  setEdges(list){ edges = list; },
  snap(){ hist.push(JSON.stringify({edges, realms})); fut.length = 0; }
};

(async function init(){
  resize(); fit();
  try{
    const r = await fetch('/api/vector', {cache:'no-store'});
    if (r.ok){
      const V = await r.json();
      S.V = {sea:V.sea||[], rivers:V.rivers||[], lakes:V.lakes||[], coasts:V.coasts||[]};
      bgKey = ''; draw();
    }
  }catch(e){}
  try{
    const r = await fetch('/api/ownership/load', {cache:'no-store'});
    if (r.ok){ const o = await r.json(); if (o && o.owner){ owner = o.owner; draw(); } }
  }catch(e){}
  try{
    const r = await fetch('/api/borders/load', {cache:'no-store'});
    if (r.ok){
      const b = await r.json();
      if (b && Array.isArray(b.edges)){
        edges = b.edges; realms = b.realms || [];
        if (Array.isArray(b.nations) && b.nations.length) nations = b.nations;
        lastSave = '已从服务端恢复';
      }
    }
  }catch(e){}
  renderSel(); renderList(); draw();
})();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
