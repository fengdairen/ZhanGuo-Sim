# -*- coding: utf-8 -*-
"""由矢量化结果生成独立的矢量地图 HTML（不依赖任何位图、不依赖服务器）。

输入 data/map/vector/*.json + data/map/nodes.csv + regions.csv
输出 dist/map-vector/map.html

关于「边界线」：底图里的棕/深色线经实测是河道描边（与红线零重叠、
100% 落在红线 2px 内），不是独立的国界层，因此不单独成层，
改为绘制河流时套一层描边，还原参考图的观感。
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
VEC = ROOT / "data" / "map" / "vector"
OUTDIR = ROOT / "dist" / "map-vector"
OUT = OUTDIR / "map.html"


def load(name):
    return json.loads((VEC / name).read_text(encoding="utf-8"))


rivers = load("rivers_w.json")
river_labels = load("river_labels.json") if (VEC / "river_labels.json").exists() else []
coast_drawn = load("coast_drawn.json") if (VEC / "coast_drawn.json").exists() else []
lakes_drawn = load("lakes_drawn.json") if (VEC / "lakes_drawn.json").exists() else []
lakes = load("lakes.json")
coast = load("coast.json")           # 旧位图海岸线：只留文件，地图不再使用
sea_polys = load("sea_from_coast.json") if (VEC / "sea_from_coast.json").exists() else coast["sea"]

cities = []
for r in csv.DictReader(open(ROOT / "data" / "map" / "nodes.csv", encoding="utf-8-sig")):
    cities.append([r["id"], r["name"], r["kind"], round(float(r["x"]), 1), round(float(r["y"]), 1),
                   round(float(r["pop"] or 0), 2)])

# 国界疆域
PALETTE = ["#c0392b","#2980b9","#27ae60","#8e44ad","#d35400",
           "#16a085","#2c3e50","#c2185b","#7f8c8d","#f39c12",
           "#5d6d7e","#a04000","#1abc9c","#9b59b6","#e67e22"]
nation_color, nation_name, nation_state = {}, {}, {}
try:
    _st = json.loads((ROOT / "data" / "state.json").read_text(encoding="utf-8"))
    for _i, _n in enumerate(_st.get("nations", [])):
        nation_color[_n["id"]] = PALETTE[_i % len(PALETTE)]
        nation_name[_n["id"]] = _n.get("name") or _n["id"]
except Exception:
    pass

realms = []
_fc = ROOT / "data" / "map" / "faces.json"
if _fc.exists():
    try:
        _fd = json.loads(_fc.read_text(encoding="utf-8-sig"))
        for _f in (_fd.get("faces") or []):
            ring = _f.get("ring") or []
            if len(ring) < 4:
                continue
            flat = []
            for _p in ring:
                flat.append(round(_p[0], 1)); flat.append(round(_p[1], 1))
            realms.append({
                "name": "", "note": _f.get("note") or "",
                "color": nation_color.get(_f.get("nation"), "#7a6248"),
                "nation": _f.get("nation") or "",
                "nationName": nation_name.get(_f.get("nation"), ""),
                "nationState": nation_state.get(_f.get("nation"), ""),
                "faction": _f.get("faction") or "",
                "area": _f.get("area") or 0,
                "holes": [ [round(v,1) for q in h for v in q] for h in (_f.get("holes") or []) ], "cities": 0, "edges": 0, "pts": flat,
            })
    except Exception as _e:
        print("faces.json 读取失败：", _e)

_bp = ROOT / "data" / "map" / "borders.json"
if _bp.exists() and not realms:
    try:
        _b = json.loads(_bp.read_text(encoding="utf-8-sig"))
        # 国界编辑器里自定义的国家（含现场新建的）也认
        for _n in (_b.get("nations") or []):
            if _n.get("id"):
                nation_name.setdefault(_n["id"], _n.get("name") or _n["id"])
                nation_color.setdefault(_n["id"], _n.get("color") or "#7a6248")
                if _n.get("state"):
                    nation_state[_n["id"]] = _n["state"]
        for _r in _b.get("realms", []):
            ring = _r.get("ring") or []
            if len(ring) < 4:
                continue
            flat = []
            for _p in ring:
                flat.append(round(_p[0], 1)); flat.append(round(_p[1], 1))
            # 圈内城邑数（用环直接判，和编辑器口径一致）
            _ring = [tuple(_p) for _p in ring]
            def _in(p, poly=_ring):
                c = False
                n2 = len(poly)
                for k in range(n2):
                    x1, y1 = poly[k]; x2, y2 = poly[(k + 1) % n2]
                    if ((y1 > p[1]) != (y2 > p[1])) and                        (p[0] < (x2 - x1) * (p[1] - y1) / ((y2 - y1) or 1e-9) + x1):
                        c = not c
                return c
            _holes = []
            for _h in (_r.get("holes") or []):
                _hf = []
                for _p in _h:
                    _hf.append(round(_p[0], 1)); _hf.append(round(_p[1], 1))
                _holes.append(_hf)
            def _inPatch(p2):
                if not _in(p2): return False
                for _h in (_r.get("holes") or []):
                    if len(_h) > 2 and _in(p2, [tuple(x) for x in _h]): return False
                return True
            _cnt = sum(1 for _c in cities if _inPatch((_c[3], _c[4])))
            realms.append({
                "name": _r.get("name") or "",
                "color": nation_color.get(_r.get("nation"), "#7a6248"),
                "nation": _r.get("nation") or "",
                "nationName": nation_name.get(_r.get("nation"), ""),
                "nationState": nation_state.get(_r.get("nation"), ""),
                "faction": _r.get("faction") or "",
                "holes": _holes,
                "cities": _cnt,
                "edges": len(_r.get("edges") or []),
                "pts": flat,
            })
    except Exception as _e:
        print("borders.json 读取失败：", _e)

regions = []
for r in csv.DictReader(open(ROOT / "data" / "map" / "regions.csv", encoding="utf-8-sig")):
    regions.append([r["id"], r["name"], round(float(r["x"]), 1), round(float(r["y"]), 1),
                    round(float(r["pop"] or 0), 2)])

def flat(poly):
    """[[x,y],...] -> [x1,y1,x2,y2,...]；前端 pathOf 只认扁平数组。"""
    out = []
    for p in poly:
        out.append(round(float(p[0]), 1))
        out.append(round(float(p[1]), 1))
    return out


data = {
    "meta": {"canvas": [9101, 8509], "source": "底图河道湖泊.png / 底图海岸线.png"},
    "sea": [flat(p) for p in sea_polys],
    "islands": [],
    "coast": [],
    "lakes": [],
    "rivers": rivers,
    "realms": realms,
    "riverLabels": river_labels,
    "coastDrawn": coast_drawn,
    "lakesDrawn": lakes_drawn,
    "cities": cities,
    "regions": regions,
}

payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)

HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>战国演义 · 矢量舆图 BC 390</title>
<style>
  :root{
    --paper:#f2e7cb; --ink:#33241a;
    --sea:#b8c6cc; --sea-edge:#8ca0aa;
    --river:#3e7ca6; --river-case:#8a6a48; --lake:#7fb0c9;
  }
  *{box-sizing:border-box}
  html,body{margin:0;height:100%;overflow:hidden;background:#54483a;
    font-family:"Songti SC","STSong","SimSun","Noto Serif CJK SC",serif;color:var(--ink)}
  #cv{display:block;width:100%;height:100%;cursor:grab;touch-action:none}
  #cv.drag{cursor:grabbing}
  .panel{position:fixed;background:rgba(250,244,229,.94);border:1px solid rgba(120,90,56,.35);
    border-radius:10px;box-shadow:0 6px 22px rgba(80,55,30,.14);backdrop-filter:blur(6px)}
  #hud{top:14px;left:14px;width:236px;padding:12px 13px 11px;font-size:13px}
  #hud h1{margin:0 0 2px;font-size:16px;letter-spacing:2px;font-weight:600}
  #hud .sub{font-size:11px;color:#7a6a55;margin-bottom:9px;letter-spacing:.5px}
  .row{display:flex;align-items:center;gap:7px;margin:5px 0;cursor:pointer;user-select:none}
  .row input{accent-color:#8b6a3f;margin:0}
  .sw{display:inline-block;width:13px;height:3px;border-radius:2px;flex:none}
  .sw.sea{background:var(--sea)}
  .sw.lake{background:var(--lake)}
  .sw.river{background:var(--river)}
  .sw.auto{background:#b9c4c9}
  .sw.coast{background:#5d7280}
  .sw.city{background:#8b2e1e;height:7px;width:7px;border-radius:50%}
  .sw.region{background:#a2543a;height:7px;width:7px;border-radius:50%;opacity:.75}
  .legend{display:flex;gap:14px;margin:9px 0 2px;font-size:12px;color:#5b4a37;align-items:center}
  .legend i.m{display:inline-block;border-radius:50%;margin-right:4px;vertical-align:middle}
  .legend i.du{width:9px;height:9px;background:#8b2e1e;box-shadow:0 0 0 2px rgba(139,46,30,.25)}
  .legend i.cheng{width:6px;height:6px;background:#6b4a2f}
  .legend i.yi{width:4px;height:4px;background:#7a6248}
  #q{width:100%;padding:5px 7px;margin-top:8px;border:1px solid rgba(120,90,56,.35);
    border-radius:6px;background:#fffdf6;font:inherit;font-size:12px;color:inherit}
  #q:focus{outline:2px solid rgba(139,46,30,.25);outline-offset:1px}
  #hits{font-size:11px;color:#7a6a55;margin-top:5px;min-height:14px;line-height:1.5}
  #foot{bottom:14px;left:14px;padding:8px 11px;font-size:11.5px;color:#6d5c47;letter-spacing:.3px}
  #zoom{bottom:14px;right:14px;padding:7px 10px;font-size:11.5px;color:#6d5c47;font-variant-numeric:tabular-nums}
  #tip{position:fixed;pointer-events:none;padding:5px 9px;font-size:12px;background:rgba(48,33,20,.92);
    color:#f6eeda;border-radius:6px;transform:translate(-50%,-165%);opacity:0;transition:opacity .12s;
    white-space:nowrap;z-index:9}
#rinfo{position:fixed;right:14px;top:64px;width:230px;background:rgba(250,243,226,.97);
  border:1px solid rgba(120,90,56,.35);border-radius:8px;box-shadow:0 8px 26px rgba(40,26,12,.3);
  padding:12px 14px 10px;display:none;z-index:20;font-family:"Songti SC","SimSun",serif;color:#33241a}
#rinfo.on{display:block}
#rinfo .rn{font-size:26px;font-weight:700;letter-spacing:4px;line-height:1.2}
#rinfo .rr{font-size:11.5px;color:#8a7350;margin:2px 0 10px}
#rinfo .rl{display:flex;justify-content:space-between;font-size:12.5px;color:#6b5940;
  padding:3px 0;border-top:1px solid rgba(120,90,56,.14)}
#rinfo .rl b{font-weight:600;color:#33241a}
#rinfo .rx{margin-top:10px;font-size:11.5px;color:#2d5d80;cursor:pointer;text-align:right}
  .btn{position:fixed;right:14px;top:14px;display:flex;gap:6px;z-index:5}
  .btn button{padding:6px 11px;font:inherit;font-size:12px;color:#4a3524;cursor:pointer;
    background:rgba(250,244,229,.94);border:1px solid rgba(120,90,56,.35);border-radius:8px}
  .btn button:hover{background:#fffdf6}
</style>
</head>
<body>
<canvas id="cv"></canvas>

<div id="hud" class="panel">
  <h1>战国演义 · 舆图</h1>
  <div class="sub">BC 390 · 矢量版（无底图）</div>
  <label class="row"><input type="checkbox" id="lSea" checked><span class="sw sea"></span>海岸与海域</label>
  <label class="row"><input type="checkbox" id="lRiver" checked><span class="sw river"></span>河流（描迹）</label>
  <label class="row"><input type="checkbox" id="lRName" checked>河名</label>
  <label class="row"><input type="checkbox" id="lCoastDrawn" checked><span class="sw coast"></span>海岸线（描迹）</label>
  <label class="row"><input type="checkbox" id="lLakesDrawn" checked><span class="sw lake"></span>湖泽（描迹）</label>
  <label class="row"><input type="checkbox" id="lCity" checked><span class="sw city"></span>城邑</label>
  <label class="row"><input type="checkbox" id="lLabel" checked>地名标注</label>
  <label class="row"><input type="checkbox" id="lRegion"><span class="sw region"></span>部族</label>
  <div class="legend"><span><i class="m du"></i>都</span><span><i class="m cheng"></i>城</span><span><i class="m yi"></i>邑</span></div>
  <input id="q" placeholder="搜地名，回车定位">
  <div id="hits"></div>
</div>

<div class="btn">
  <button id="bFit">全图</button>
  <button id="bIn">＋</button>
  <button id="bOut">－</button>
</div>
<div id="foot" class="panel"></div>
<a href="../index.html" class="panel" id="home" style="bottom:58px;left:12px;padding:6px 12px;text-decoration:none;color:#2d5d80;font-size:12.5px">← 数据台</a>
<div id="zoom" class="panel">—</div>
<div id="tip"></div>
<div id="rinfo">
  <div class="rn" id="rName">—</div>
  <div class="rr" id="rSub"></div>
  <div class="rl"><span>疆域</span><b id="rRealm">—</b></div>
  <div class="rl"><span>城邑</span><b id="rCities">—</b></div>
  <div class="rl"><span>地方</span><b id="rEdges">—</b></div>
  <div class="rl"><span>面积</span><b id="rArea">—</b></div>
  <div class="rx" id="rClose">关闭</div>
</div>

<script>
const DATA = __DATA__;
const CW = 9101, CH = 8509;
const cv = document.getElementById('cv');
const ctx = cv.getContext('2d');
const tip = document.getElementById('tip');
const zoomEl = document.getElementById('zoom');

const COL = {
  sea:'#b8c6cc', seaEdge:'#8ca0aa', coast:'#6d7f8c',
  river:'#3e7ca6', riverCase:'rgba(122,90,58,.55)',
  lake:'#7fb0c9', lakeEdge:'#3e7ca6',
  du:'#8b2e1e', cheng:'#6b4a2f', yi:'#7a6248',
  halo:'rgba(246,238,216,.92)', region:'#a2543a'
};

let dpr = Math.min(2.5, window.devicePixelRatio || 1);
let cw = 0, ch = 0;
const V = { scale: 0.15, tx: 0, ty: 0 };

function resize(){
  cw = cv.clientWidth; ch = cv.clientHeight;
  cv.width = Math.round(cw*dpr); cv.height = Math.round(ch*dpr);
  draw();
}
const FRAME_MAT = 220;              // 与 draw() 里的装裱边宽一致

function centerAt(x, y, sc){
  V.scale = sc; V.tx = cw/2 - x*sc; V.ty = ch/2 - y*sc; draw();
}
// 深链：#n0231 定位城池；#x,y,z 定位坐标与缩放
function deepLink(){
  if (typeof location === 'undefined') return;
  const h = (location.hash || '').slice(1);
  if (!h) return;
  const rl = G.realms.find(r => r.name === h || (r.nation && r.nation === h));
  if (rl){
    const sameNation = selRealm && rl.nation && rl.nation === selRealm.nation;
    if (rl.faction && sameNation && selFaction !== rl.faction){
      selFaction = rl.faction; selFactionNation = rl.nation;
      showFaction(rl.faction, rl.nation, rl);
    } else {
      selFaction = null; selFactionNation = null;
      selRealm = rl; showRealm(rl);
    }
    centerAt(rl.center[0], rl.center[1], 0.28); draw(); return;
  }
  const c = CITIES.find(c2 => c2.id === h);
  if (c){ centerAt(c.x, c.y, 0.9); hoverCity = c; return; }
  const p2 = h.split(',').map(Number);
  if (p2.length >= 2 && p2.every(n => !isNaN(n))) centerAt(p2[0], p2[1], p2[2] || 0.6);
}
window.addEventListener('hashchange', deepLink);

function fit(){
  // 连装裱一起放进画面，否则绫边会被裁掉
  const s = Math.min(cw/(CW + FRAME_MAT*2), ch/(CH + FRAME_MAT*2)) * 0.97;
  V.scale = s; V.tx = (cw - CW*s)/2; V.ty = (ch - CH*s)/2;
  draw();
}
const w2s = (x,y) => [x*V.scale + V.tx, y*V.scale + V.ty];

function pathOf(poly, close){
  const p = new Path2D();
  for (let i=0;i<poly.length;i+=2){
    if (i===0) p.moveTo(poly[i], poly[i+1]); else p.lineTo(poly[i], poly[i+1]);
  }
  if (close) p.closePath();
  return p;
}

// 地方势力色：在本国颜色上做小幅色相/明度偏移，表示"同国但另一股势力"
function factionColor(hex, name){
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  const dh = ((h % 25) - 12) * 1.0;          // -12° ~ +12°
  let r = parseInt(hex.slice(1,3),16)/255, g = parseInt(hex.slice(3,5),16)/255, b2 = parseInt(hex.slice(5,7),16)/255;
  const mx = Math.max(r,g,b2), mn = Math.min(r,g,b2);
  let hh = 0, ss = 0, ll = (mx+mn)/2;
  if (mx !== mn){
    const d = mx - mn;
    ss = ll > 0.5 ? d/(2-mx-mn) : d/(mx+mn);
    hh = mx === r ? ((g-b2)/d + (g < b2 ? 6 : 0)) : mx === g ? ((b2-r)/d + 2) : ((r-g)/d + 4);
    hh *= 60;
  }
  hh = (hh + dh + 360) % 360;
  ss = Math.min(1, ss * 1.15 + 0.06);
  ll = Math.min(0.85, ll + 0.06);
  const c = (1 - Math.abs(2*ll-1)) * ss;
  const x2 = c * (1 - Math.abs((hh/60) % 2 - 1));
  const m = ll - c/2;
  let rr, gg, bb;
  if (hh < 60){ rr=c; gg=x2; bb=0; } else if (hh < 120){ rr=x2; gg=c; bb=0; }
  else if (hh < 180){ rr=0; gg=c; bb=x2; } else if (hh < 240){ rr=0; gg=x2; bb=c; }
  else if (hh < 300){ rr=x2; gg=0; bb=c; } else { rr=c; gg=0; bb=x2; }
  const to = v => Math.round((v+m)*255).toString(16).padStart(2,'0');
  return '#' + to(rr) + to(gg) + to(bb);
}

function shade(hex, k){          // 混入墨色，让国界线与河网区分开（返回 hex）
  const h = hex.replace('#','');
  const n = parseInt(h.length === 3 ? h.split('').map(c=>c+c).join('') : h, 16);
  const r = Math.round(((n>>16)&255) * (1-k) + 58 * k);
  const g = Math.round(((n>>8)&255) * (1-k) + 40 * k);
  const b2 = Math.round((n&255) * (1-k) + 28 * k);
  return '#' + [r,g,b2].map(v => v.toString(16).padStart(2,'0')).join('');
}
function rgba(hex, a){
  const h = hex.replace('#','');
  const n = parseInt(h.length === 3 ? h.split('').map(c=>c+c).join('') : h, 16);
  return 'rgba(' + ((n>>16)&255) + ',' + ((n>>8)&255) + ',' + (n&255) + ',' + a + ')';
}
const G = { sea:new Path2D(), islands:new Path2D(), lakes:new Path2D(),
            coast:new Path2D(), riverBuckets:[] };
for (const poly of DATA.sea) G.sea.addPath(pathOf(poly, true));
for (const poly of DATA.islands) G.islands.addPath(pathOf(poly, true));
for (const poly of DATA.lakes) G.lakes.addPath(pathOf(poly, true));
for (const line of DATA.coast) G.coast.addPath(pathOf(line, false));
// 描迹海岸线：开放线做描边，闭合环按岛处理（填陆地色）
G.coastDrawnLine = new Path2D();
G.islandDrawn = new Path2D();
G.lakesDrawn = new Path2D();
for (const l of (DATA.lakesDrawn || [])) G.lakesDrawn.addPath(pathOf(l.pts, true));
G.realms = (DATA.realms || []).map(r => {
  const ring = [];
  for (let i=0;i<r.pts.length;i+=2) ring.push([r.pts[i], r.pts[i+1]]);
  let bb = [1e9, 1e9, -1e9, -1e9];
  for (const p of ring){
    if (p[0] < bb[0]) bb[0] = p[0];
    if (p[1] < bb[1]) bb[1] = p[1];
    if (p[0] > bb[2]) bb[2] = p[0];
    if (p[1] > bb[3]) bb[3] = p[1];
  }
  let a = 0, cx = 0, cy = 0;
  for (let i=0;i+1<ring.length;i++){
    const cr = ring[i][0]*ring[i+1][1] - ring[i+1][0]*ring[i][1];
    a += cr; cx += (ring[i][0]+ring[i+1][0])*cr; cy += (ring[i][1]+ring[i+1][1])*cr;
  }
  a = a/2;
  const c = Math.abs(a) > 1 ? [cx/(6*a), cy/(6*a)] : [
    ring.reduce((s,p)=>s+p[0],0)/ring.length, ring.reduce((s,p)=>s+p[1],0)/ring.length];
  const holesPts = (r.holes || []).map(h => pathOf(h, true));
  return { name:r.name, color:r.color, nationName:r.nationName || '',
           nationState:r.nationState || '', holes:holesPts,
           nation:r.nation || '', faction:r.faction || '',
           cities:r.cities|0, edges:r.edges|0,
           path:pathOf(r.pts, true), area:Math.abs(a), center:c, bb, ring };
});
for (const c of (DATA.coastDrawn || [])){
  if (c.closed) G.islandDrawn.addPath(pathOf(c.pts, true));
  else G.coastDrawnLine.addPath(pathOf(c.pts, false));
}

// 自动提取的河网：只做淡色底衬，提示"这些还没描"
window.__MAP__ = { get realms(){ return G.realms; }, realmAt, selRealm: () => selRealm };

(function(){
  const p = new Path2D();
  for (const e of (DATA.auto || [])){
    p.moveTo(e[1], e[2]);
    for (let i=3;i<e.length;i+=2) p.lineTo(e[i], e[i+1]);
  }
  G.auto = p;
})();

(function(){
  const buckets = new Map();
  for (const e of DATA.rivers){
    const key = Math.round(e[0]*2)/2;
    if (!buckets.has(key)) buckets.set(key, new Path2D());
    const p = buckets.get(key);
    p.moveTo(e[1], e[2]);
    for (let i=3;i<e.length;i+=2) p.lineTo(e[i], e[i+1]);
  }
  G.riverBuckets = [...buckets.entries()].sort((a,b)=>a[0]-b[0]);
})();

const CITIES = DATA.cities.map(c => ({id:c[0], name:c[1], kind:c[2], x:c[3], y:c[4], pop:c[5]}));

// 几何规模：用于性能读数
const GEOM_POINTS = (() => {
  let n = 0;
  for (const p of DATA.coast) n += p.length / 2;
  for (const p of DATA.sea) n += p.length / 2;
  for (const p of DATA.lakes) n += p.length / 2;
  for (const e of DATA.rivers) n += (e.length - 1) / 2;
  for (const c of (DATA.coastDrawn || [])) n += c.pts.length / 2;
  return Math.round(n);
})();
const REGIONS = DATA.regions.map(r => ({id:r[0], name:r[1], x:r[2], y:r[3], pop:r[4]}));

const el = id => document.getElementById(id);
const state = () => ({
  sea: el('lSea').checked, river: el('lRiver').checked, rname: el('lRName').checked,
  coastDrawn: el('lCoastDrawn').checked, lakesDrawn: el('lLakesDrawn').checked,
  city: el('lCity').checked, label: el('lLabel').checked, region: el('lRegion').checked
});
let hoverCity = null, flash = null;

let perfOn = false, drawMs = 0;

function draw(){
  const t0 = performance.now();
  const L = state();
  ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.clearRect(0,0,cw,ch);

  // 桌面
  ctx.fillStyle = '#54483a';
  ctx.fillRect(0,0,cw,ch);

  // 装裱：绫边 + 双框 + 纸面
  const MAT = 220;                       // 绫边宽度（世界像素）
  ctx.setTransform(dpr*V.scale,0,0,dpr*V.scale,dpr*V.tx,dpr*V.ty);

  ctx.save();
  ctx.shadowColor = 'rgba(18,10,4,.55)';
  ctx.shadowBlur = 34 / V.scale;
  ctx.shadowOffsetY = 10 / V.scale;
  ctx.fillStyle = '#c9b389';
  ctx.fillRect(-MAT, -MAT, CW + MAT*2, CH + MAT*2);
  ctx.restore();

  ctx.strokeStyle = '#7a5c3a'; ctx.lineWidth = Math.max(2, 8 / V.scale);
  ctx.strokeRect(-MAT, -MAT, CW + MAT*2, CH + MAT*2);
  ctx.strokeStyle = 'rgba(226,211,173,.9)'; ctx.lineWidth = Math.max(1, 2.5 / V.scale);
  ctx.strokeRect(-MAT + 10/V.scale, -MAT + 10/V.scale,
                 CW + MAT*2 - 20/V.scale, CH + MAT*2 - 20/V.scale);

  ctx.fillStyle = '#f3e8cf';
  ctx.fillRect(0, 0, CW, CH);
  const pg = ctx.createRadialGradient(CW/2, CH*0.45, Math.min(CW,CH)*0.12,
                                      CW/2, CH*0.55, Math.max(CW,CH)*0.78);
  pg.addColorStop(0, 'rgba(255,250,235,.55)');
  pg.addColorStop(1, 'rgba(190,165,120,.35)');
  ctx.fillStyle = pg;
  ctx.fillRect(0, 0, CW, CH);
  ctx.strokeStyle = 'rgba(120,90,56,.45)'; ctx.lineWidth = Math.max(1, 2/V.scale);
  ctx.strokeRect(0, 0, CW, CH);

  ctx.setTransform(dpr*V.scale,0,0,dpr*V.scale,dpr*V.tx,dpr*V.ty);

  // ---- 疆域地块：并集轮廓 + 内侧渐变 ----
  if (G.realms.length){
    const byNation = new Map();
    for (const r of G.realms){
      const key = r.nation || ('_' + r.id);
      if (!byNation.has(key)) byNation.set(key, []);
      byNation.get(key).push(r);
    }
    for (const [key, list] of byNation){
      const on = list.some(r => selNation && selNation === key);
      const color = list[0].color;

      // 1) 面
      for (const r of list){
        ctx.fillStyle = rgba(color, on ? 0.20 : 0.075);
        ctx.fill(r.path, 'evenodd');
      }

      // 1.2) 地方势力：同国底色上叠一层偏移色，不画边界线
      for (const r of list){
        if (!r.faction) continue;
        const fc = factionColor(color, r.faction);
        const hot = selFaction && r.faction === selFaction && key === selFactionNation;
        ctx.fillStyle = rgba(fc, hot ? 0.30 : 0.13);
        ctx.fill(r.path, 'evenodd');
        if (hot){
          ctx.save();
          ctx.setLineDash([6 / V.scale, 5 / V.scale]);
          ctx.strokeStyle = rgba(shade(fc, 0.35), 0.55);
          ctx.lineWidth = 1.6 / V.scale;
          ctx.stroke(r.path);
          ctx.restore();
        }
      }

      // 2) 内侧渐变：栅格遮罩（先填并集，再减去模糊后的自己 → 紧贴国界向内淡出）
      drawInnerFade(list, color, 0.16, key);

      // 3) 国界线：整组描边后擦掉内部 → 只剩合起来的轮廓，宽度恒定
      if (!off) off = document.createElement('canvas');
      if (off.width !== cv.width || off.height !== cv.height){
        off.width = cv.width; off.height = cv.height;
      }
      const g = off.getContext('2d');
      g.setTransform(1,0,0,1,0,0);
      g.clearRect(0,0,off.width,off.height);
      g.setTransform(dpr*V.scale,0,0,dpr*V.scale,dpr*V.tx,dpr*V.ty);
      g.lineJoin = 'round'; g.lineCap = 'round';
      g.strokeStyle = rgba(shade(color, on ? 0.55 : 0.45), on ? 1 : 0.95);
      g.lineWidth = (on ? 9.2 : 6.0) / V.scale;
      for (const r of list) g.stroke(r.path);
      g.globalCompositeOperation = 'destination-out';
      for (const r of list) g.fill(r.path, 'evenodd');
      g.globalCompositeOperation = 'source-over';
      ctx.setTransform(1,0,0,1,0,0);
      ctx.drawImage(off, 0, 0);
      ctx.setTransform(dpr*V.scale,0,0,dpr*V.scale,dpr*V.tx,dpr*V.ty);
    }
  }


  if (L.sea){
    ctx.fillStyle = COL.sea; ctx.fill(G.sea, 'evenodd');
    ctx.strokeStyle = COL.seaEdge; ctx.lineWidth = 1.2/V.scale; ctx.stroke(G.sea);
    if (DATA.islands.length){
      ctx.fillStyle = '#efe2c2'; ctx.fill(G.islands, 'evenodd');
      ctx.strokeStyle = COL.coast; ctx.lineWidth = Math.max(0.7/V.scale, 1); ctx.stroke(G.islands);
    }
  }

  if (L.river){
    ctx.lineJoin = 'round'; ctx.lineCap = 'round';
    // 先描边（深），再压主色，还原参考图的「深色裹边」观感
    ctx.strokeStyle = COL.riverCase;
    for (const [w, p] of G.riverBuckets){
      ctx.lineWidth = Math.max(1.0/V.scale, w + 1.5);
      ctx.stroke(p);
    }
    ctx.strokeStyle = COL.river;
    for (const [w, p] of G.riverBuckets){
      ctx.lineWidth = Math.max(0.8/V.scale, w);
      ctx.stroke(p);
    }
  }

  if (L.lakesDrawn && (DATA.lakesDrawn || []).length){
    // 填色与描边在下面；名字单独一趟（在 drawRiverNames 里统一画）
    ctx.fillStyle = '#8ec3d8';
    ctx.fill(G.lakesDrawn, 'evenodd');
    ctx.strokeStyle = '#3e7ca6';
    ctx.lineWidth = Math.max(0.9/V.scale, 2.2);
    ctx.stroke(G.lakesDrawn);
  }
  if (L.coastDrawn){
    if (DATA.coastDrawn && DATA.coastDrawn.some(c => c.closed)){
      ctx.fillStyle = '#efe2c2';
      ctx.fill(G.islandDrawn, 'evenodd');
    }
    ctx.strokeStyle = '#40606f';
    // 海岸线要比河流显得"重"：至少 1 屏幕像素，放大时保持 5.5 世界像素
    ctx.lineWidth = Math.max(1.0/V.scale, 5.5);
    ctx.stroke(G.islandDrawn);
    ctx.stroke(G.coastDrawnLine);
  }


  ctx.setTransform(dpr,0,0,dpr,0,0);

  if (L.region){
    ctx.font = '12px "Songti SC","SimSun",serif';
    ctx.textBaseline = 'middle';
    for (const r of REGIONS){
      const [sx,sy] = w2s(r.x, r.y);
      if (sx < -60 || sy < -20 || sx > cw+60 || sy > ch+20) continue;
      ctx.globalAlpha = .75;
      ctx.beginPath(); ctx.arc(sx, sy, 3.0, 0, 6.283);
      ctx.fillStyle = COL.region; ctx.fill();
      ctx.globalAlpha = 1;
      ctx.fillStyle = 'rgba(120,66,44,.85)';
      ctx.fillText(r.name, sx+7, sy+1);
    }
  }

  if (L.city){
    for (const c of CITIES){
      const [sx,sy] = w2s(c.x, c.y);
      if (sx < -10 || sy < -10 || sx > cw+10 || sy > ch+10) continue;
      const k = Math.min(2.0, Math.max(1, V.scale / 0.22));   // 放大时城池点跟着变大
      if (c.kind === '都'){
        ctx.beginPath(); ctx.arc(sx, sy, 3.4*k, 0, 6.283);
        ctx.fillStyle = COL.du; ctx.fill();
        ctx.beginPath(); ctx.arc(sx, sy, 5.2*k, 0, 6.283);
        ctx.strokeStyle = 'rgba(139,46,30,.5)'; ctx.lineWidth = 0.9*k; ctx.stroke();
      } else if (c.kind === '城'){
        ctx.beginPath(); ctx.arc(sx, sy, 2.4*k, 0, 6.283);
        ctx.fillStyle = COL.cheng; ctx.fill();
        ctx.strokeStyle = 'rgba(246,238,216,.85)'; ctx.lineWidth = .7*k; ctx.stroke();
      } else {
        ctx.beginPath(); ctx.arc(sx, sy, 1.4*k, 0, 6.283);
        ctx.fillStyle = COL.yi; ctx.globalAlpha = .92; ctx.fill(); ctx.globalAlpha = 1;
      }
    }
  }

  labelReset();
  if (L.label) drawLabels(L);
  if (L.rname && DATA.riverLabels) drawRiverNames();

  if (hoverCity){
    const [sx,sy] = w2s(hoverCity.x, hoverCity.y);
    ctx.beginPath(); ctx.arc(sx, sy, 8.5, 0, 6.283);
    ctx.strokeStyle = 'rgba(139,46,30,.8)'; ctx.lineWidth = 1.6; ctx.stroke();
  }
  if (flash){
    const [sx,sy] = w2s(flash.x, flash.y);
    const t = (performance.now() - flash.t) / 1000;
    if (t < 1){
      ctx.beginPath(); ctx.arc(sx, sy, 10 + 30*t, 0, 6.283);
      ctx.strokeStyle = 'rgba(139,46,30,' + (0.8*(1-t)).toFixed(3) + ')';
      ctx.lineWidth = 2; ctx.stroke();
      requestAnimationFrame(draw);
    } else flash = null;
  }
  drawMs = drawMs ? drawMs * 0.8 + (performance.now() - t0) * 0.2 : (performance.now() - t0);
  zoomEl.textContent = '缩放 ' + (V.scale*100).toFixed(0) + '%' +
    (perfOn ? ('  ·  ' + drawMs.toFixed(1) + ' ms  ·  ' + (GEOM_POINTS/1000).toFixed(1) + 'k 点') : '');
}

function drawRiverNames(){
  const list = DATA.riverLabels || [];
  if (!list.length && !(DATA.lakesDrawn || []).length) return;
  // 湖名
  if (el('lLakesDrawn').checked){
    ctx.font = 'italic 13px "Songti SC","SimSun",serif';
    ctx.textBaseline = 'middle';
    ctx.textAlign = 'center';
    for (const l of (DATA.lakesDrawn || [])){
      if (!l.name) continue;
      const [sx, sy] = w2s(l.cx, l.cy);
      if (sx < -80 || sy < -20 || sx > cw + 80 || sy > ch + 20) continue;
      ctx.font = 'italic 13px "Songti SC","SimSun",serif';
      const lw = ctx.measureText(l.name).width;
      if (!labelTry(sx - lw/2, sy - 8, lw, 16, 3)) continue;
      ctx.lineWidth = 3.4;
      ctx.strokeStyle = 'rgba(246,238,216,.9)';
      ctx.strokeText(l.name, sx, sy);
      ctx.fillStyle = '#2f6f8f';
      ctx.fillText(l.name, sx, sy);
    }
    ctx.textAlign = 'left';
  }
  if (!list.length) return;
  // 低缩放只保留大河名，避免满屏河名
  const sc = V.scale;
  const maxN = sc > 0.6 ? 999 : sc > 0.35 ? 90 : sc > 0.2 ? 40 : 16;
  const ranked = list.slice().sort((a, b) =>
    ((b.water || 0) - (a.water || 0)) || ((b.len || 0) - (a.len || 0)));
  const picked = ranked.slice(0, maxN);
  if (sc < 0.12) return;
  ctx.font = '13px "Songti SC","SimSun",serif';
  ctx.textBaseline = 'middle';
  ctx.textAlign = 'center';
  ctx.font = '13px "Songti SC","SimSun",serif';
  ctx.textBaseline = 'middle';
  ctx.textAlign = 'center';
  for (const r of picked){
    const [sx, sy] = w2s(r.x, r.y);
    if (sx < -80 || sy < -20 || sx > cw + 80 || sy > ch + 20) continue;
    const rw = ctx.measureText(r.name).width;
    if (!labelTry(sx - rw/2, sy - 8, rw, 16, 4)) continue;
    ctx.lineWidth = 3.4;
    ctx.strokeStyle = 'rgba(246,238,216,.9)';
    ctx.strokeText(r.name, sx, sy);
    ctx.fillStyle = '#2d5d80';
    ctx.fillText(r.name, sx, sy);
  }
  ctx.textAlign = 'left';
}

let LB = null;                       // 每帧重建的标注占位表
function labelReset(){
  LB = { cell:110, grid:new Map() };
}
function labelTry(x, y, w, h, pad){
  pad = pad || 0;
  x -= pad; y -= pad; w += pad*2; h += pad*2;
  const C = LB.cell;
  const gx = Math.floor(x/C), gy = Math.floor(y/C);
  for (let i=gx-1;i<=gx+1;i++) for (let j=gy-1;j<=gy+1;j++){
    const arr = LB.grid.get(i+'|'+j); if (!arr) continue;
    for (const b of arr) if (x < b[0]+b[2] && x+w > b[0] && y < b[1]+b[3] && y+h > b[1]) return false;
  }
  const k = Math.floor(x/C)+'|'+Math.floor(y/C);
  if (!LB.grid.has(k)) LB.grid.set(k, []);
  LB.grid.get(k).push([x,y,w,h]);
  return true;
}

function drawLabels(L){
  const sc = V.scale;
  // 缩放决定"看到哪一层"：越小越只显示大城
  const showCheng = sc > 0.20;
  const showYi    = sc > 0.46;
  const fs = sc > 1.1 ? 15 : sc > 0.55 ? 13 : 12;
  ctx.font = fs + 'px "Songti SC","SimSun",serif';
  ctx.textBaseline = 'middle';
  const rank = {'都':0, '城':1, '邑':2};
  const list = CITIES.slice().sort((a,b)=> (rank[a.kind]-rank[b.kind]) || (b.pop-a.pop));
  for (const c of list){
    if (c.kind === '城' && !showCheng) continue;
    if (c.kind === '邑' && !showYi) continue;
    const [sx,sy] = w2s(c.x, c.y);
    if (sx < -70 || sy < -24 || sx > cw+10 || sy > ch+24) continue;
    const pad = c.kind === '都' ? 6 : 8;
    const w = ctx.measureText(c.name).width;
    const h = fs + 2;
    const x = sx + pad, y = sy - h/2;
    if (!labelTry(x, y, w, h, 2)) continue;
    ctx.lineWidth = 3.2;
    ctx.strokeStyle = COL.halo;
    ctx.strokeText(c.name, x, sy);
    ctx.fillStyle = c.kind === '都' ? '#571c12' : (c.kind === '城' ? '#3b2918' : '#6b5940');
    ctx.fillText(c.name, x, sy);
  }
}

// ---- 疆域点选 ----
let selRealm = null;
let selNation = null;
let selFaction = null, selFactionNation = null;
let off = null;
function pointInRing(x, y, ring){
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++){
    const [x1, y1] = ring[i], [x2, y2] = ring[j];
    if (((y1 > y) !== (y2 > y)) && (x < (x2 - x1) * (y - y1) / ((y2 - y1) || 1e-9) + x1)) inside = !inside;
  }
  return inside;
}
// 内侧渐变：栅格法
// A = 并集填充；B = A 的模糊版；A 减去 B → 只剩贴边的一圈，且由边向内淡出
let _fadeA = null, _fadeB = null;
// 渐变的计算结果缓存：同一个 (国家, 视角) 只算一次，之后直接贴图
const _fadeCache = new Map();
function fadeKeyOf(key, color){
  return [key, color, V.scale.toFixed(4), Math.round(V.tx), Math.round(V.ty), cw, ch, dpr,
          G.realms.length].join('|');
}
function drawInnerFade(list, color, alpha, cacheKey){
  const ck = cacheKey ? fadeKeyOf(cacheKey, color) : null;
  if (ck && _fadeCache.has(ck)){ 
    ctx.setTransform(1,0,0,1,0,0);
    ctx.drawImage(_fadeCache.get(ck), 0, 0);
    ctx.setTransform(dpr*V.scale,0,0,dpr*V.scale,dpr*V.tx,dpr*V.ty);
    return;
  }
  const w = cv.width, h = cv.height;
  if (!w || !h) return;
  if (!_fadeA){ _fadeA = document.createElement('canvas'); _fadeB = document.createElement('canvas'); }
  for (const c of [_fadeA, _fadeB]){
    if (c.width !== w || c.height !== h){ c.width = w; c.height = h; }
  }
  const R = 9 * dpr;                            // 渐变带宽度（屏幕像素 × dpr）
  const ga = _fadeA.getContext('2d');
  ga.setTransform(1,0,0,1,0,0); ga.clearRect(0,0,w,h);
  ga.setTransform(dpr*V.scale,0,0,dpr*V.scale,dpr*V.tx,dpr*V.ty);
  ga.fillStyle = '#fff';
  for (const r of list) ga.fill(r.path, 'evenodd');

  const gb = _fadeB.getContext('2d');
  gb.setTransform(1,0,0,1,0,0); gb.clearRect(0,0,w,h);
  gb.filter = 'blur(' + R + 'px)';
  gb.drawImage(_fadeA, 0, 0);
  gb.filter = 'none';

  ga.setTransform(1,0,0,1,0,0);
  ga.globalCompositeOperation = 'destination-out';
  ga.drawImage(_fadeB, 0, 0);
  ga.globalCompositeOperation = 'source-in';
  ga.fillStyle = rgba(color, Math.min(0.55, alpha * 2));
  ga.fillRect(0, 0, w, h);
  ga.globalCompositeOperation = 'source-over';

  if (ck){
    const cp = document.createElement('canvas');
    cp.width = w; cp.height = h;
    cp.getContext('2d').drawImage(_fadeA, 0, 0);
    _fadeCache.set(ck, cp);
    if (_fadeCache.size > 16){ _fadeCache.delete(_fadeCache.keys().next().value); }
  }
  ctx.setTransform(1,0,0,1,0,0);
  ctx.drawImage(_fadeA, 0, 0);
  ctx.setTransform(dpr*V.scale,0,0,dpr*V.scale,dpr*V.tx,dpr*V.ty);
}

function pathOfPairs(pairs, close){
  const p = new Path2D();
  if (!pairs.length) return p;
  p.moveTo(pairs[0][0], pairs[0][1]);
  for (let i=1;i<pairs.length;i++) p.lineTo(pairs[i][0], pairs[i][1]);
  if (close) p.closePath();
  return p;
}

// 同国多块地的并集轮廓
// 共享边不一定完全重合（两块地分两次画，顶点采样可能不同），
// 所以按"线段中点是否落在别的同国地块内部"来判定，而不是比对端点。
let _unionCache = new Map();
function unionRings(patches){
  if (!patches || !patches.length) return [];
  const ck = patches.map(r => r.length + ':' + (r[0] ? r[0][0].toFixed(1) + ',' + r[0][1].toFixed(1) : '')).join('|');
  if (_unionCache.has(ck)) return _unionCache.get(ck);

  const key = p => p[0].toFixed(1) + ',' + p[1].toFixed(1);
  const segs = [];
  for (const ring of patches){
    for (let i = 0; i + 1 < ring.length; i++){
      const a = ring[i], b = ring[i+1];
      if (a[0] === b[0] && a[1] === b[1]) continue;
      segs.push({ a, b, ring, k: key(a) + '|' + key(b) });
    }
  }

  // 精确重合的共享边（两块地引用同一批顶点）→ 直接剔除
  const cnt = new Map();
  for (const sg of segs){
    const k2 = sg.k.split('|').sort().join('|');
    cnt.set(k2, (cnt.get(k2) || 0) + 1);
  }
  const keep = [];
  for (const sg of segs){
    const k2 = sg.k.split('|').sort().join('|');
    if (cnt.get(k2) > 1) continue;               // 共享边
    const mx = (sg.a[0] + sg.b[0]) / 2, my = (sg.a[1] + sg.b[1]) / 2;
    let insideOther = false;
    for (const ring of patches){
      if (ring === null) continue;
      if (ring === sg.ring) continue;
      // 落在别的同国地块内部，或贴着它的边（共享边但顶点不重合）→ 都不算国界
      if (pointInRing(mx, my, ring) || distToRingPx(mx, my, ring) < 2.5){ insideOther = true; break; }
    }
    if (!insideOther) keep.push(sg);
  }

  // 串环：从任一段出发，找端点最近的下一段
  const used = new Array(keep.length).fill(false);
  const grid = new Map();
  const CELL = 16;
  keep.forEach((sg, i) => {
    const gx = Math.floor(sg.a[0]/CELL), gy = Math.floor(sg.a[1]/CELL);
    const k = gx + ',' + gy;
    if (!grid.has(k)) grid.set(k, []);
    grid.get(k).push(i);
  });
  const nearStart = (p) => {
    let best = -1, bd = 30;
    const gx = Math.floor(p[0]/CELL), gy = Math.floor(p[1]/CELL);
    for (let dx=-1; dx<=1; dx++) for (let dy=-1; dy<=1; dy++){
      const arr = grid.get((gx+dx)+','+(gy+dy));
      if (!arr) continue;
      for (const i of arr){
        if (used[i]) continue;
        const d = Math.hypot(keep[i].a[0]-p[0], keep[i].a[1]-p[1]);
        if (d < bd){ bd = d; best = i; }
      }
    }
    return best;
  };
  const out = [];
  for (let i = 0; i < keep.length; i++){
    if (used[i]) continue;
    const loop = [];
    let cur = i;
    let guard = 0;
    while (cur >= 0 && guard++ < keep.length + 8){
      used[cur] = true;
      loop.push(keep[cur].a);
      const next = nearStart(keep[cur].b);
      if (next < 0){
        // 接回起点则闭合
        const d0 = Math.hypot(keep[cur].b[0]-loop[0][0], keep[cur].b[1]-loop[0][1]);
        if (d0 < 30) loop.push(loop[0]);
        break;
      }
      cur = next;
    }
    if (loop.length >= 4) out.push(loop);
  }
  _unionCache.set(ck, out);
  return out;
}
function distToRingPx(x, y, ring){
  let best = 1e9;
  for (let i=0;i+1<ring.length;i++){
    const x1 = ring[i][0], y1 = ring[i][1], x2 = ring[i+1][0], y2 = ring[i+1][1];
    const dx = x2-x1, dy = y2-y1, L2 = dx*dx+dy*dy || 1e-9;
    let t = ((x-x1)*dx + (y-y1)*dy)/L2; t = Math.max(0, Math.min(1, t));
    best = Math.min(best, Math.hypot(x1+t*dx-x, y1+t*dy-y));
  }
  return best;
}

function realmAt(x, y){
  let best = null;
  for (const r of G.realms){
    if (!r.ring || !pointInRing(x, y, r.ring)) continue;
    let inHole = false;
    for (const h of (r.holes || [])) if (pointInRing(x, y, h)) inHole = true;
    if (inHole) continue;
    if (!best || (r.area || 0) < (best.area || 0)) best = r;   // 被包住的小地块优先
  }
  return best;
}
// 地方势力信息：同一股势力可能横跨多个地块，一起统计与高亮
function showFaction(fac, nation, anchor){
  const box = el('rinfo');
  const group = G.realms.filter(x => x.faction === fac && (x.nation || '') === (nation || ''));
  const cities = group.reduce((s2, x) => s2 + (x.cities || 0), 0);
  const area = group.reduce((s2, x) => s2 + (x.area || 0), 0);
  el('rName').textContent = fac;
  el('rSub').textContent = '地方势力 · 隶属' + ((anchor && anchor.nationName) || '');
  el('rRealm').textContent = group.length + ' 块' + (group.length > 1 ? '（跨地块）' : '');
  el('rCities').textContent = cities ? (cities + ' 城') : '—';
  el('rArea').textContent = Math.round(area).toLocaleString() + ' px²';
  el('rFac').textContent = (group.map(x => x.note || x.id).slice(0, 6).join('、') || '—');
  el('rEdges').textContent = '同国其他区域不在高亮范围';
  box.classList.add('on');
}

function showRealm(r){
  const box = el('rinfo');
  if (!r){ box.classList.remove('on'); return; }
  const key = r.nation || ('_' + r.id);
  const group = G.realms.filter(x => (x.nation || ('_' + x.id)) === key);
  const cities = group.reduce((s, x) => s + (x.cities || 0), 0);
  const area = group.reduce((s, x) => s + (x.area || 0), 0);
  const facs = [...new Set(group.map(x => x.faction).filter(Boolean))];
  el('rName').textContent = r.nationName || r.name || '地块';
  el('rSub').textContent = r.nationState ? (r.nationState)
    : (r.nationName ? '疆域' : '未指定国家');
  el('rRealm').textContent = group.length + ' 块' + (group.length > 1 ? '（含飞地）' : '');
  el('rCities').textContent = cities ? (cities + ' 城') : '—';
  el('rEdges').textContent = facs.length ? facs.join('、') : '中央直辖';
  el('rArea').textContent = Math.round(area).toLocaleString() + ' px²';
  box.classList.add('on');
}
el('rClose').onclick = () => { selRealm = null; selNation = null; selFaction = null; selFactionNation = null; showRealm(null); draw(); };

let dragging = false, last = null;
cv.addEventListener('pointerdown', e => {
  dragging = true; last = [e.clientX, e.clientY];
  cv.classList.add('drag');
  try { cv.setPointerCapture(e.pointerId); } catch(_){}
});
cv.addEventListener('pointerup', e => {
  const wasDrag = dragging && last && (Math.abs(e.clientX - last[0]) + Math.abs(e.clientY - last[1]) > 0);
  dragging = false; cv.classList.remove('drag');
  const r0 = cv.getBoundingClientRect();
  const mx = e.clientX - r0.left, my = e.clientY - r0.top;
  const [wx, wy] = [ (mx - V.tx)/V.scale, (my - V.ty)/V.scale ];
  const hit = realmAt(wx, wy);
  if (!wasDrag){
    const sameNation = hit && selRealm && hit.nation && hit.nation === selRealm.nation;
    if (hit && hit.faction && sameNation && selFaction !== hit.faction){
      selFaction = hit.faction; selFactionNation = hit.nation;
      showFaction(hit.faction, hit.nation, hit);
      requestAnimationFrame(() => draw());     // 面板更新后强制再刷一帧
    } else {
      selFaction = null; selFactionNation = null;
      selRealm = hit;
      selNation = hit ? (hit.nation || ('_' + hit.id)) : null;
      showRealm(hit);
    }
    draw();
    requestAnimationFrame(() => draw());
  }
  last = null;
});
cv.addEventListener('pointerleave', () => { tip.style.opacity = 0; hoverCity = null; draw(); });

cv.addEventListener('pointermove', e => {
  if (dragging && last){
    V.tx += e.clientX - last[0]; V.ty += e.clientY - last[1];
    last = [e.clientX, e.clientY];
    draw(); return;
  }
  const r = cv.getBoundingClientRect();
  const mx = e.clientX - r.left, my = e.clientY - r.top;
  let best = null, bd = 9;
  for (const c of CITIES){
    const [sx,sy] = w2s(c.x,c.y);
    const d = Math.hypot(sx-mx, sy-my);
    if (d < bd){ bd = d; best = c; }
  }
  if (best !== hoverCity){ hoverCity = best; draw(); }
  if (best){
    const [sx,sy] = w2s(best.x, best.y);
    tip.style.opacity = 1;
    tip.style.left = (r.left + sx) + 'px';
    tip.style.top = (r.top + sy) + 'px';
    tip.textContent = best.name + ' · ' + best.kind + ' · ' + best.pop + ' 万';
  } else tip.style.opacity = 0;
});

cv.addEventListener('wheel', e => {
  e.preventDefault();
  const r = cv.getBoundingClientRect();
  const mx = e.clientX - r.left, my = e.clientY - r.top;
  zoomAt(mx, my, Math.exp(-e.deltaY * 0.0016));
}, {passive:false});

cv.addEventListener('dblclick', e => {
  const r = cv.getBoundingClientRect();
  zoomAt(e.clientX - r.left, e.clientY - r.top, 1.7);
});

function zoomAt(mx, my, k){
  const wx = (mx - V.tx)/V.scale, wy = (my - V.ty)/V.scale;
  V.scale = Math.max(0.05, Math.min(9, V.scale * k));
  V.tx = mx - wx*V.scale; V.ty = my - wy*V.scale;
  draw();
}

function flyTo(c){
  V.scale = Math.max(V.scale, 0.6);
  V.tx = cw/2 - c.x*V.scale; V.ty = ch/2 - c.y*V.scale;
  flash = {x:c.x, y:c.y, t:performance.now()};
  draw();
}

el('bFit').onclick = fit;
el('bIn').onclick = () => zoomAt(cw/2, ch/2, 1.35);
el('bOut').onclick = () => zoomAt(cw/2, ch/2, 1/1.35);
for (const id of ['lSea','lRiver','lRName','lCoastDrawn','lLakesDrawn','lCity','lLabel','lRegion'])
  el(id).addEventListener('change', draw);

const q = el('q'), hits = el('hits');
q.addEventListener('keydown', e => {
  if (e.key !== 'Enter') return;
  const kw = q.value.trim();
  if (!kw){ hits.textContent = ''; return; }
  const fc = CITIES.filter(c => c.name.indexOf(kw) >= 0);
  const fr = REGIONS.filter(r => r.name.indexOf(kw) >= 0);
  const all = fc.concat(fr);
  if (!all.length){ hits.textContent = '无匹配'; return; }
  hits.textContent = '命中 ' + all.length + '：' + all.slice(0,6).map(c=>c.name).join('、');
  flyTo(all[0]);
});

window.addEventListener('keydown', e => {
  if (e.target === q) return;
  if (e.key === '+' || e.key === '=') zoomAt(cw/2, ch/2, 1.35);
  if (e.key === '-') zoomAt(cw/2, ch/2, 1/1.35);
  if (e.key === '0') fit();
  if (e.key === 'p' || e.key === 'P'){ perfOn = !perfOn; draw(); }
});
/* 源数据变了就自动刷新（服务端 /api/version） */
let _stamp = null;
setInterval(async () => {
  if (document.visibilityState !== 'visible') return;
  try{
    const r = await fetch('/api/version', {cache:'no-store'});
    if (!r.ok) return;
    const j = await r.json();
    if (_stamp === null){ _stamp = j.stamp; return; }
    if (j.stamp > _stamp + 0.001) location.reload();
  }catch(e){}
}, 3000);

window.addEventListener('resize', resize);

resize(); fit(); deepLink();
el('foot').textContent =
  '河 ' + DATA.rivers.length + ' 段 · 湖 ' + (DATA.lakesDrawn || []).length + ' 处 · 城邑 ' + CITIES.length +
  ' 座 · 部族 ' + REGIONS.length + '　｜　滚轮缩放 · 拖拽平移 · 双击放大 · P 看性能';
</script>
</body>
</html>
"""

OUTDIR.mkdir(parents=True, exist_ok=True)
OUT.write_text(HTML.replace("__DATA__", payload), encoding="utf-8")
print(f"written {OUT}  {OUT.stat().st_size/1024:.0f} KB")
