// tools/smoke_river_editor.js — 用最小 DOM 桩跑描迹器核心流程（node 直接运行）
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const htmlPath = path.join(__dirname, '..', 'dist', 'river-editor', 'river_editor.html');
const html = fs.readFileSync(htmlPath, 'utf8');
const m = [...html.matchAll(/<script(?![^>]*src)[^>]*>([\s\S]*?)<\/script>/g)];
const script = m[m.length - 1][1];

const listeners = {};   // listeners.cv = {pointerdown, ...} / listeners.__win = {keydown}
const els = {};         // 按 id 缓存的元素

function classList(){
  const s = new Set();
  return {
    add: c => s.add(c), remove: c => s.delete(c),
    contains: c => s.has(c),
    toggle: (c, on) => { if (on === undefined) { s.has(c) ? s.delete(c) : s.add(c); } else if (on) s.add(c); else s.delete(c); }
  };
}

function ctx2d(){
  const calls = {};
  const target = {
    canvas: { width: 1200, height: 800 },
    save(){}, restore(){}, beginPath(){}, closePath(){}, moveTo(){}, lineTo(){},
    arc(){}, rect(){}, fill(){}, stroke(){}, clip(){}, translate(){}, rotate(){}, scale(){},
    setTransform(){}, resetTransform(){}, clearRect(){}, fillRect(){}, strokeRect(){},
    fillText(){}, strokeText(){}, drawImage(){}, setLineDash(){}, quadraticCurveTo(){}, bezierCurveTo(){},
    measureText: () => ({ width: 12 }),
    createLinearGradient: () => ({ addColorStop(){} }),
    createRadialGradient: () => ({ addColorStop(){} }),
    createPattern: () => ({}),
    getImageData: () => ({ data: new Uint8ClampedArray(4) }),
    putImageData(){}
  };
  return new Proxy(target, {
    get(t, k){
      if (k in t) return t[k];
      return (...a) => { calls[k] = (calls[k] || 0) + 1; };
    },
    set(t, k, v){ t[k] = v; return true; },
    has(){ return true; }
  });
}

function mkEl(tag, id){
  const el = {
    tagName: (tag || 'div').toUpperCase(),
    id: id || '',
    style: {}, className: '', textContent: '', innerHTML: '', value: '',
    checked: false, disabled: false, children: [],
    dataset: {},
    classList: classList(),
    width: 1200, height: 800,
    clientWidth: 1200, clientHeight: 800,
    appendChild(c){ this.children.push(c); return c; },
    removeChild(c){ this.children = this.children.filter(x => x !== c); },
    remove(){},
    addEventListener(ev, fn){
      const key = this.id === 'cv' ? 'cv' : (this.id ? this.id : '__el');
      (listeners[key] = listeners[key] || {})[ev] = fn;
    },
    removeEventListener(){},
    getBoundingClientRect(){ return { left: 0, top: 0, right: 1200, bottom: 800, width: 1200, height: 800 }; },
    setPointerCapture(){}, releasePointerCapture(){}, focus(){}, blur(){},
    getContext(){ return this._ctx || (this._ctx = ctx2d()); },
    querySelectorAll(){ return []; },
    querySelector(){ return null; },
    closest(){ return null; },
    insertBefore(n){ this.children.push(n); },
    contains(){ return false; }
  };
  return el;
}

const doc = {
  getElementById(id){ return els[id] || (els[id] = mkEl(id === 'cv' ? 'canvas' : 'div', id)); },
  createElement(tag){ return mkEl(tag); },
  createElementNS(ns, tag){ return mkEl(tag); },
  querySelectorAll(sel){
    if (sel.indexOf('rank') >= 0) return [];
    return [];
  },
  querySelector(){ return null; },
  body: mkEl('body'),
  documentElement: mkEl('html'),
  addEventListener(ev, fn){ (listeners.__doc = listeners.__doc || {})[ev] = fn; },
  activeElement: null
};

const store = {};
const sandbox = {
  console,
  document: doc,
  window: {
    devicePixelRatio: 1,
    innerWidth: 1200, innerHeight: 800,
    addEventListener(ev, fn){ (listeners.__win = listeners.__win || {})[ev] = fn; },
    removeEventListener(){},
    requestAnimationFrame(fn){ return setTimeout(() => fn(Date.now()), 0); },
    cancelAnimationFrame(id){ clearTimeout(id); },
    matchMedia(){ return { matches: false, addListener(){}, removeListener(){} }; }
  },
  localStorage: {
    getItem: k => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: k => { delete store[k]; }
  },
  performance: { now: () => Date.now() },
  requestAnimationFrame: fn => setTimeout(() => fn(Date.now()), 0),
  cancelAnimationFrame: id => clearTimeout(id),
  setTimeout, clearTimeout, setInterval, clearInterval,
  Image: class { constructor(){ this.complete = false; this.naturalWidth = 0; this.width = 0; this.height = 0; }
                  set src(v){ this._src = v; } get src(){ return this._src; }
                  addEventListener(){} },
  Path2D: class { constructor(){} addPath(){} moveTo(){} lineTo(){} closePath(){} },
  performance_now: null,
  Math, JSON, Date, Map, Set, Array, Object, String, Number, Boolean, Error, Infinity, NaN,
  alert: () => {}, confirm: () => true, prompt: () => null
};
sandbox.window.document = doc;
sandbox.globalThis = sandbox;
sandbox.self = sandbox.window;

vm.createContext(sandbox);
vm.runInContext(script, sandbox, { filename: htmlPath });

const calls = {};

// 模拟：画一条五点折线 → 收笔 → 命名 → 分段 → 各段设水量 → 改等级
try {
  const pd = listeners['cv'] && listeners['cv'].pointerdown;
  if (!pd) throw new Error('没绑定 pointerdown');
  const ev = (x, y) => ({ button: 0, clientX: x, clientY: y, shiftKey: false, pointerId: 1, preventDefault() {} });
  pd(ev(400, 300));
  pd(ev(500, 360));
  pd(ev(620, 420));
  pd(ev(700, 500));
  pd(ev(780, 560));
  pd(ev(780, 561));   // 同一位置再点一次 = 收笔
} catch (e) {
  console.error('FAIL: 交互路径抛异常 ->', e && e.stack || e);
  process.exit(1);
}

const api = sandbox.window.__RIVER_EDITOR__;
if (!api) { console.error('FAIL: 没有暴露 __RIVER_EDITOR__'); process.exit(1); }

function check(cond, msg) { if (!cond) { console.error('FAIL: ' + msg); process.exit(1); } }

function allRiverVerts(){
  const s = new Set();
  for (const sg of api.S.segs) for (const pp of sg.pts) s.add(pp[0].toFixed(1) + ',' + pp[1].toFixed(1));
  return s;
}

let segs = api.S.segs;
check(segs.length === 1, '期望 1 段，实际 ' + segs.length);
check(segs[0].pts.length === 5, '期望 5 个点，实际 ' + segs[0].pts.length);
check(segs[0].river && segs[0].water === 3, '新段应带 river 且水量默认 3');
const riverA = segs[0].river;

// 河名（整条河共用）
api.S.sel = segs[0].id;
api.setSegField('name', '长江');
check(segs[0].name === '长江', '河名设置失败');

// 段名（单段）
api.setSegField('section', '金沙江段');
check(segs[0].section === '金沙江段', '段名设置失败');

// 在中间顶点切成两段
api.splitAt(segs[0].id, 2);
segs = api.S.segs;
check(segs.length === 2, '切分后期望 2 段，实际 ' + segs.length);
check(segs[0].river === riverA && segs[1].river === riverA, '两段应同属一条河');
check(segs[0].pts.length === 3 && segs[1].pts.length === 3, '切点应共享：3 + 3 点');
check(segs[0].name === '长江' && segs[1].name === '长江', '分段后河名应保留');
check(segs[0].section === '金沙江段' && segs[1].section === '', '前半段保留段名，后半段段名为空');

// 水量（只影响线宽）与等级
check(api.S.sel === segs[1].id, '切分后应选中后半段');
api.setSegWater(1);
api.setSegRank(4);
check(segs[1].water === 1, '水量设置失败');
check(api.classify(segs[1]).kind === 'canal', '运河判定失败');
check(segs[0].water === 3 && api.classify(segs[0]).kind !== 'canal', '前半段不应被连带修改');

// 画一条支流并挂到长江上 → 自动成为一级支流
const pd = listeners['cv'].pointerdown;
const ev = (x, y) => ({ button: 0, clientX: x, clientY: y, shiftKey: false, pointerId: 1, preventDefault() {} });
pd(ev(300, 700)); pd(ev(380, 760)); pd(ev(380, 761));
segs = api.S.segs;
check(segs.length === 3, '支流未生成，实际 ' + segs.length);
const trib = segs[2];
const mainSeg = segs[0];
const target = mainSeg.pts[1];
api.attachEnd(trib.id, api.mouthIndex(trib), mainSeg.id, target[0], target[1]);
check(trib.parent && trib.parent.river === riverA, '父子关系未建立');
check(Array.isArray(trib.links) && trib.links.length === 1, 'links 未建立');
check(trib.links[0].kind === 'mouth', '汇入端 kind 应为 mouth');
check(api.classify(trib).kind === 'trib' && api.classify(trib).level === 1,
      '支流类型应为一级，实际 ' + api.kindLabel(trib));
const linkAt = trib.links[0].at === 0 ? 0 : trib.pts.length - 1;
check(Math.hypot(trib.pts[linkAt][0]-target[0], trib.pts[linkAt][1]-target[1]) < 1,
  '连接端未吸附到上级接点');
check(api.depthOf(riverA) === 0 && api.depthOf(trib.river) === 1, 'depthOf 不对');

// 父动子动：移动干流的交汇顶点，支流连接端应跟着走
const before = trib.pts[linkAt].slice();
mainSeg.pts[1] = [target[0] + 120, target[1] + 60];
api.syncChildren();
const after = trib.pts[linkAt];
check(Math.abs(after[0] - mainSeg.pts[1][0]) < 0.6 && Math.abs(after[1] - mainSeg.pts[1][1]) < 0.6,
  '干流交汇点移动后支流端点未跟随：' + JSON.stringify(after));
check(before[0] !== after[0] || before[1] !== after[1], '支流端点根本没动，测试无效');

// 流向：反向只翻方向，不动坐标；挂着的上级会被断开（否则父子关系不成立）
check(trib.flow === -1 || trib.flow === 1, 'flow 字段缺失');
const miBefore = api.mouthIndex(trib);
const ptsBefore = JSON.stringify(trib.pts);
api.S.sel = trib.id;
api.reverseFlow();
check(api.mouthIndex(trib) !== miBefore, '反向没有改变河口端');
check(JSON.stringify(trib.pts) === ptsBefore, '反向不应改动坐标（会把折线拽成闭环）');
check(trib.parent === null, '反向后河口端不再挂在河上，parent 应为空');
check(api.classify(trib).kind === 'dist', '反向后应成为岔流，实际 ' + api.kindLabel(trib));

// 反向后再接一次，验证接回流程仍然可用
api.attachEnd(trib.id, api.mouthIndex(trib), mainSeg.id, target[0], target[1]);
check(trib.parent && trib.parent.river === riverA, '重新接入失败');

// ---- 源头端：岔出（branch）不算父子；天然源头可自由拖动 ----
const mouthAtNow = trib.links.find(L => L.kind === 'mouth').at;
const srcAt = mouthAtNow === 0 ? trib.pts.length - 1 : 0;
const other2 = segs[1];
api.attachEnd(trib.id, srcAt, other2.id, other2.pts[0][0], other2.pts[0][1], 'branch');
const br = trib.links.find(L => L.kind === 'branch');
check(br && br.at === srcAt, '岔出端未记录为 branch');
check(trib.parent && trib.parent.river === riverA, '岔出不应改变父子关系（parent 仍应是汇入那条）');

// 断开岔出端 → 回到天然源头，坐标可以自由拖
api.unlinkEnd(trib.id, srcAt);
check(!trib.links.some(L => L.at === srcAt), '断开岔出端失败');
const freeBefore = trib.pts[srcAt].slice();
trib.pts[srcAt] = [freeBefore[0] + 50, freeBefore[1] + 30];
api.syncChildren();
check(Math.abs(trib.pts[srcAt][0] - (freeBefore[0] + 50)) < 0.5, '天然源头端被强行吸附了');

const pl = api.payload();
check(pl.version === 5, 'payload 版本应为 5，实际 ' + pl.version);
check(pl.segments.every(s => s.flow === 1 || s.flow === -1), 'payload 缺 flow');
check(pl.segments.length === 3, 'payload 段数不对');
check(pl.segments[1].water === 1 && pl.segments[1].nature === 'artificial', 'payload 字段丢失');
check(pl.segments[0].name === '长江' && pl.segments[0].section === '金沙江段', 'payload 名字不对');
check(pl.segments[2].parent && pl.segments[2].parent.river === riverA, 'payload parent 不对');

// ---- 运河：两端都要能挂 ----
const other = segs[1];                       // 长江的后半段，当作另一端的目标
api.S.sel = trib.id;
api.setSegRank(4);
api.syncChildren();
check(api.classify(trib).kind === 'canal', '未改成运河');
check(trib.parent === null, '运河不应有单一上级');

api.attachEnd(trib.id, 0, mainSeg.id, mainSeg.pts[0][0], mainSeg.pts[0][1]);
api.attachEnd(trib.id, trib.pts.length - 1, other.id, other.pts[0][0], other.pts[0][1]);
check((trib.links || []).length === 2, '运河应有两端连接，实际 ' + (trib.links || []).length);
check(trib.links[0].at === 0 && trib.links[1].at === trib.pts.length - 1, '运河两端不是各挂一条');
check(trib.parent === null, '运河的 parent 应保持为空（不进支流树）');

const pl2 = api.payload();
const cs = pl2.segments.find(s => s.id === trib.id);
check(cs.links.length === 2, 'payload 没带上运河的两端');
check(cs.parent === null, 'payload 里运河不该有 parent');

// 往返：payload → loadData 后 links 不能丢
api.loadData(pl2);
const c2 = api.S.segs.find(s => s.id === trib.id);
check(c2 && (c2.links || []).length === 2, 'links 往返丢失');
check(api.classify(c2).kind === 'canal' && c2.parent === null, '往返后运河属性丢失');

// ---- 海岸线 + 入海 ----
els['bCoast'].onclick();
const pd2 = listeners['cv'].pointerdown;
pd2(ev(120, 120)); pd2(ev(220, 160)); pd2(ev(320, 150)); pd2(ev(320, 151));
check(api.S.coasts.length === 1, '海岸线未生成');
check(api.S.coasts[0].pts.length === 3, '海岸线点数不对，实际 ' + api.S.coasts[0].pts.length);

const sh = api.S.segs[0];
api.S.sel = sh.id;
const cp = api.S.coasts[0].pts[1];          // 海岸线第 2 点（世界坐标）
api.attachSea(sh.id, api.mouthIndex(sh), api.S.coasts[0].id, cp[0], cp[1]);
const seaLink = (sh.links || []).find(L => L.kind === 'sea');
check(!!seaLink, '入海链接未建立');
check(Math.hypot(sh.pts[seaLink.at][0] - cp[0], sh.pts[seaLink.at][1] - cp[1]) < 1.5,
  '河口未吸附到海岸点');

const pl3 = api.payload();
check(Array.isArray(pl3.coasts) && pl3.coasts.length === 1, 'payload 缺 coasts');
check(pl3.segments.some(x => (x.links || []).some(L => L.kind === 'sea')), 'payload 缺 sea 链接');

// ---- 折叠：渲染不报错，汇总行存在 ----
api.S.collapsed.add(sh.river);
api.renderList();
check(api.S.collapsed.has(sh.river), '折叠状态未记录');
api.S.collapsed.clear();
api.renderList();

// ---- 湖泽：首尾落在河上 → 自动闭合 ----
const toScreen = (wx, wy) => [wx * api.V.s + api.V.tx, wy * api.V.s + api.V.ty];
els['bLake'].onclick();
const rv = api.S.segs[0].pts[2];
const c0 = toScreen(rv[0], rv[1]);
const at = (sx, sy) => pd2({ button: 0, clientX: sx, clientY: sy, shiftKey: false, pointerId: 1, preventDefault() {} });
at(c0[0], c0[1]);                 // 起点落在河道顶点上（应吸附）
at(c0[0] + 40, c0[1] - 30);
at(c0[0] + 20, c0[1] - 60);
at(c0[0] + 21, c0[1] - 61);       // 同位置再点 = 收笔
check(api.S.lakes.length === 1, '湖泽未生成，实际 ' + api.S.lakes.length);
const lk = api.S.lakes[0];
check(lk.pts[0][0] === rv[0] && lk.pts[0][1] === rv[1], '湖泽起点未借用河道顶点');
check(lk.pts[0][0] === lk.pts[lk.pts.length - 1][0] &&
      lk.pts[0][1] === lk.pts[lk.pts.length - 1][1], '湖泽没有闭合');
check((lk.onRivers || []).length >= 1, '湖泽没有记录接河位置');

// 湖泽②：完全离河、原地画一个闭合水体
els['bLake'].onclick();
const e0 = toScreen(1200, 1200);
at(e0[0], e0[1]);
at(e0[0] + 60, e0[1] + 10);
at(e0[0] + 70, e0[1] + 70);
at(e0[0] + 10, e0[1] + 80);
at(e0[0] + 11, e0[1] + 81);   // 收笔
check(api.S.lakes.length === 2, '离河湖泽未生成，实际 ' + api.S.lakes.length);
const lk2 = api.S.lakes[1];
check(lk2.pts[0][0] === lk2.pts[lk2.pts.length-1][0], '离河湖泽未闭合');
check(lk2.pts.length === 5, '离河湖泽点数应为 4+1 闭合，实际 ' + lk2.pts.length);
check((lk2.onRivers || []).length === 0, '离河湖泽不该有接河记录');

// 湖泽③：首尾借同一条河的两个顶点 → 闭合边应沿河道走
// 先画一条 8 点的河，专门用来测这个
els['bDraw'].onclick();
const bx = 120, by = 500;
for (let i = 0; i < 8; i++) at(bx + i * 30, by + (i % 2) * 20);
listeners.__win.keydown({ key: 'Enter', target: { tagName: 'CANVAS' } });
const segLong = api.S.segs[api.S.segs.length - 1];
check(segLong.pts.length === 8, '测试用河道应为 8 点，实际 ' + segLong.pts.length);
const segP = segLong.pts;
els['bLake'].onclick();
const v1 = toScreen(segP[1][0], segP[1][1]);
const v6 = toScreen(segP[6][0], segP[6][1]);
at(v1[0], v1[1]);
at(v1[0] + 50, v1[1] - 40);
at(v6[0] - 40, v6[1] - 30);
at(v6[0], v6[1]);
listeners.__win.keydown({ key: 'Enter', target: { tagName: 'CANVAS' } });
check(api.S.lakes.length === 3, '第三个湖泽未生成，实际 ' + api.S.lakes.length);
const lk3 = api.S.lakes[2];
let hits = 0;
for (let i = 2; i <= 5; i++){
  if (lk3.pts.some(p => p[0] === segP[i][0] && p[1] === segP[i][1])) hits++;
}
check(hits === 4, '闭合边没有沿河道走（河道点命中 ' + hits + '/4）');

// 湖泽命名
api.S.selLake = lk2.id;
api.setLakeName('大野泽');
check(lk2.name === '大野泽', '湖名未写入');

// 湖泽④：起点在河上时，终点 20px 内应吸回同一条河，闭合边走河道
els['bLake'].onclick();
const sp0 = toScreen(segP[0][0], segP[0][1]);
const sp3 = toScreen(segP[3][0], segP[3][1]);
at(sp0[0], sp0[1]);
at(sp0[0] + 40, sp0[1] - 50);
at(sp3[0] + 20, sp3[1] + 10);          // 离河道顶点 22 屏幕像素
listeners.__win.keydown({ key: 'Enter', target: { tagName: 'CANVAS' } });
const lk4 = api.S.lakes[api.S.lakes.length - 1];
check(!!lk4.arc && Array.isArray(lk4.arc.path), '终点没有吸回同一条河（arc 缺失）');
// arc 上的每个点都必须是某条河的顶点（可以跨河）
const netVerts = allRiverVerts();
check(lk4.arc.path.length >= 2, 'arc 点太少：' + lk4.arc.path.length);
check(lk4.arc.path.every(pp => netVerts.has(pp[0].toFixed(1) + ',' + pp[1].toFixed(1))),
  'arc 里混入了不是河道顶点的点');

// 湖泽顶点可拖
els['bSelect'].onclick();
api.S.selLake = lk4.id;
const dv = toScreen(lk4.drawn[1][0], lk4.drawn[1][1]);
const before1 = lk4.drawn[1].slice();
listeners['cv'].pointerdown({ button: 0, clientX: dv[0], clientY: dv[1], shiftKey: false, pointerId: 1, preventDefault() {} });
listeners['cv'].pointermove({ button: 0, clientX: dv[0] + 30, clientY: dv[1] + 30, shiftKey: false, pointerId: 1, preventDefault() {} });
listeners['cv'].pointerup({});
check(lk4.drawn[1][0] !== before1[0] || lk4.drawn[1][1] !== before1[1], '湖泽顶点拖不动');
check(lk4.pts.length >= 4, '拖动后 pts 没重建');

// 湖泽⑤：起止分别落在同一条河的**两个分段**上 → arc 应跨段拼接
els['bDraw'].onclick();
for (let i = 0; i < 8; i++) at(400 + i * 25, 700 + (i % 2) * 15);
listeners.__win.keydown({ key: 'Enter', target: { tagName: 'CANVAS' } });
const longSeg2 = api.S.segs[api.S.segs.length - 1];
api.splitAt(longSeg2.id, 4);                       // 在第 5 个顶点处切成两段（共享该点）
const parts = api.S.segs.filter(s => s.river === longSeg2.river);
check(parts.length === 2, '切段后应有 2 段，实际 ' + parts.length);
const A2 = parts[0], B2 = parts[1];
check(Math.hypot(A2.pts[A2.pts.length-1][0] - B2.pts[0][0],
                 A2.pts[A2.pts.length-1][1] - B2.pts[0][1]) < 1, '两段应共享切点');

els['bLake'].onclick();
const qa = toScreen(A2.pts[0][0], A2.pts[0][1]);
const qb = toScreen(B2.pts[B2.pts.length - 1][0], B2.pts[B2.pts.length - 1][1]);
at(qa[0], qa[1]);
at(qa[0] + 60, qa[1] - 60);
at(qb[0] + 10, qb[1] + 10);
listeners.__win.keydown({ key: 'Enter', target: { tagName: 'CANVAS' } });
const lk5 = api.S.lakes[api.S.lakes.length - 1];
check(!!lk5.arc && lk5.arc.path.length >= 2, '跨段 arc 没生成：' + JSON.stringify(lk5.arc && lk5.arc.path.length));
const inA = lk5.arc.path.some(pp => A2.pts.some(v => v[0] === pp[0] && v[1] === pp[1]));
const inB = lk5.arc.path.some(pp => B2.pts.some(v => v[0] === pp[0] && v[1] === pp[1]));
check(inA && inB, 'arc 没有同时经过两个分段（A=' + inA + ' B=' + inB + '）');

// 湖泽⑥：起点在 A 河、终点在 B 河 → 边界必须沿河网连通（跨河）
const rA = api.S.segs[0];
// 造一条 B 河，并把它的河口接到 A 河上，保证两河连通
els['bDraw'].onclick();
for (let i = 0; i < 5; i++) at(860 + i * 22, 640 + (i % 2) * 16);
listeners.__win.keydown({ key: 'Enter', target: { tagName: 'CANVAS' } });
const rB = api.S.segs[api.S.segs.length - 1];
api.attachEnd(rB.id, api.mouthIndex(rB), rA.id, rA.pts[1][0], rA.pts[1][1]);
check(rB.parent && rB.parent.seg === rA.id, '测试前提：B 河应接到 A 河');

els['bLake'].onclick();
const cA = toScreen(rA.pts[0][0], rA.pts[0][1]);
const cB = toScreen(rB.pts[0][0], rB.pts[0][1]);
at(cA[0], cA[1]);
at(cA[0] + 80, cA[1] - 60);
at(cB[0] + 6, cB[1] + 5);
  'last=', JSON.stringify(api.S.draft.pts[api.S.draft.pts.length-1]), 'rB0=', JSON.stringify(rB.pts[0]),
  'V.s=', api.V.s.toFixed(4), 'distWorld=', Math.hypot(api.S.draft.pts[api.S.draft.pts.length-1][0]-rB.pts[0][0],
    api.S.draft.pts[api.S.draft.pts.length-1][1]-rB.pts[0][1]).toFixed(1),
listeners.__win.keydown({ key: 'Enter', target: { tagName: 'CANVAS' } });
const lk6 = api.S.lakes[api.S.lakes.length - 1];
check(!!lk6.arc && lk6.arc.path.length >= 2, '跨河 arc 没生成：' + JSON.stringify(lk6.arc && lk6.arc.path.length));
const usedRivers = new Set();
for (const pp of lk6.arc.path){
  for (const sg of api.S.segs){
    if (sg.pts.some(v => v[0] === pp[0] && v[1] === pp[1])) usedRivers.add(sg.river);
  }
}
check(usedRivers.size >= 2, '跨河边界只走了 ' + usedRivers.size + ' 条河');
const nv = allRiverVerts();
check(lk6.arc.path.every(pp => nv.has(pp[0].toFixed(1) + ',' + pp[1].toFixed(1))), '跨河 arc 混入了非河道点');

// 湖泽⑦：两河之间没有通路 → 不硬套 arc，但湖泽照样生成（直线闭合）
els['bDraw'].onclick();
for (let i = 0; i < 4; i++) at(60 + i * 18, 60 + (i % 2) * 12);
listeners.__win.keydown({ key: 'Enter', target: { tagName: 'CANVAS' } });
const rFar = api.S.segs[api.S.segs.length - 1];
els['bLake'].onclick();
const fA = toScreen(rA.pts[0][0], rA.pts[0][1]);
const fB = toScreen(rFar.pts[0][0], rFar.pts[0][1]);
at(fA[0], fA[1]);
at(fA[0] + 40, fA[1] - 40);
at(fB[0] + 6, fB[1] + 5);
const beforeN = api.S.lakes.length;
listeners.__win.keydown({ key: 'Enter', target: { tagName: 'CANVAS' } });
check(api.S.lakes.length === beforeN + 1, '无通路时湖泽应仍然生成');
const lk7 = api.S.lakes[api.S.lakes.length - 1];
check(lk7.arc === null, '无通路时不该硬套 arc');

// 湖泽⑧：河流端点可以直接用湖岸的点
const lkX = api.S.lakes[0];
const segX = api.S.segs[0];
const lv = lkX.pts[1];
api.attachLake(segX.id, api.mouthIndex(segX), lkX.id, lv[0], lv[1]);
const llink = (segX.links || []).find(L => L.lake === lkX.id);
check(!!llink, '河没有接到湖上');
check(Math.hypot(segX.pts[llink.at][0]-lv[0], segX.pts[llink.at][1]-lv[1]) < 0.01, '河端点没贴到湖岸顶点');

// 拖动湖岸顶点，河端点要跟着走
lkX.pts[llink.idx] = [lv[0] + 35, lv[1] + 25];
api.syncChildren();
check(Math.hypot(segX.pts[llink.at][0]-(lv[0]+35), segX.pts[llink.at][1]-(lv[1]+25)) < 0.01,
      '湖岸动了，河端点没跟随');

// 画河时起点落在湖岸 → 应自动吸附
els['bDraw'].onclick();
const lp = toScreen(lkX.pts[2][0], lkX.pts[2][1]);
at(lp[0] + 4, lp[1] + 3);
check(api.S.draft.snapAtStart && api.S.draft.snapAtStart.type === 'lake' &&
      api.S.draft.snapAtStart.id === lkX.id,
      '起笔没有吸附到湖岸：' + JSON.stringify(api.S.draft.snapAtStart));
at(lp[0] + 80, lp[1] + 80);
listeners.__win.keydown({ key: 'Enter', target: { tagName: 'CANVAS' } });
const segLake = api.S.segs[api.S.segs.length - 1];
check((segLake.links || []).some(L => L.lake === lkX.id), '自动生成的河没有记湖链接');

const pl4 = api.payload();
check(Array.isArray(pl4.lakes) && pl4.lakes.length === 7, 'payload 缺 lakes');
check(pl4.lakes[1].name === '大野泽', 'payload 湖名丢了');



// ---- 流畅度：收笔后自动进入选择模式 / 切模式取消草稿 ----
els['bLake'].onclick();
const m0 = toScreen(1200, 1600);
at(m0[0], m0[1]);
at(m0[0] + 40, m0[1] + 10);
at(m0[0] + 45, m0[1] + 50);
at(m0[0] + 5, m0[1] + 55);
at(m0[0] + 6, m0[1] + 56);
check(api.S.mode === 'select', '湖泽收笔后没切到选择模式：' + api.S.mode);

els['bDraw'].onclick();
at(200, 900); at(240, 930);
check(!!api.S.draft, '草稿没建立');
els['bSelect'].onclick();
check(api.S.draft === null, '切换模式没取消草稿');

// ---- 海岸线顶点可拖；挂在上面的河口跟随；运河端口也能接海岸 ----
const cst = api.S.coasts[0];
els['bSelect'].onclick();
api.S.selCoast = cst.id;
const cpx = toScreen(cst.pts[1][0], cst.pts[1][1]);
const cBefore = cst.pts[1].slice();
listeners['cv'].pointerdown({ button:0, clientX:cpx[0], clientY:cpx[1], shiftKey:false, pointerId:1, preventDefault(){} });
listeners['cv'].pointermove({ button:0, clientX:cpx[0]+25, clientY:cpx[1]+25, shiftKey:false, pointerId:1, preventDefault(){} });
listeners['cv'].pointerup({});
check(cst.pts[1][0] !== cBefore[0] || cst.pts[1][1] !== cBefore[1], '海岸顶点拖不动');

// 河口接在这条海岸上，拖动海岸点后河口要跟随
const segC = api.S.segs[0];
api.attachSea(segC.id, api.mouthIndex(segC), cst.id, cst.pts[1][0], cst.pts[1][1]);
const seaL = (segC.links || []).find(L => L.kind === 'sea');
check(!!seaL, '河口没接到海岸');
cst.pts[seaL.idx] = [cst.pts[seaL.idx][0] + 40, cst.pts[seaL.idx][1] + 30];
api.syncChildren();
check(Math.hypot(segC.pts[seaL.at][0]-cst.pts[seaL.idx][0],
                 segC.pts[seaL.at][1]-cst.pts[seaL.idx][1]) < 0.01, '海岸移动后河口没跟随');

// 运河端口接海岸
const canalSeg = api.S.segs.find(s => api.classify(s).kind === 'canal');
check(!!canalSeg, '测试前提：需要一条运河');
api.attachSea(canalSeg.id, 0, cst.id, cst.pts[2][0], cst.pts[2][1]);
check((canalSeg.links || []).some(L => L.kind === 'sea'), '运河端口接不了海岸');

// ---- 同一条河两岸两个湖：第二个湖起笔不能被第一个湖的岸抢走 ----
{
  const lkP = api.S.lakes.find(l => l.arc && l.arc.from);
  check(!!lkP, '测试前提：需要一个带沿河边界的湖');
  const segP2 = api.S.segs.find(s => s.id === lkP.arc.from.seg);
  check(!!segP2, '找不到湖岸对应的河段');
  const iA = lkP.arc.from.idx;
  const pA = segP2.pts[iA];
  const pB = segP2.pts[Math.min(segP2.pts.length - 1, iA + 6)];
  els['bLake'].onclick();
  const sA = toScreen(pA[0], pA[1]);
  at(sA[0] + 1, sA[1] + 1);
  check(api.S.draft.snapAtStart && api.S.draft.snapAtStart.type === 'river',
        '起笔被湖岸抢走了：' + JSON.stringify(api.S.draft.snapAtStart));
  at(sA[0] + 60, sA[1] + 60);
  const sB = toScreen(pB[0], pB[1]);
  at(sB[0] + 2, sB[1] + 2);
  listeners.__win.keydown({ key: 'Enter', target: { tagName: 'CANVAS' } });
  const lkQ = api.S.lakes[api.S.lakes.length - 1];
  check(!!lkQ.arc, '第二个湖没有形成沿河边界');
  check(lkQ.arc.from.seg === lkP.arc.from.seg, '第二个湖的边界挂错了河');
}

// ---- 以河为边界的湖泽：河岸顶点移动后边界必须重算 ----
{
  const lkA = api.S.lakes.find(l => l.arc && l.arc.path && l.arc.path.length >= 2);
  check(!!lkA, '测试前提：需要一个以河道为边界的湖泽');
  const oldP = lkA.arc.path[0];
  let hitSeg = null, hitIdx = -1;
  for (const sg of api.S.segs){
    const i = sg.pts.findIndex(p => p[0] === oldP[0] && p[1] === oldP[1]);
    if (i >= 0){ hitSeg = sg; hitIdx = i; break; }
  }
  check(!!hitSeg, '找不到湖岸对应的河道顶点');
  hitSeg.pts[hitIdx] = [oldP[0] + 77, oldP[1] + 33];
  api.syncChildren();
  const hasNew = lkA.pts.some(p => Math.abs(p[0]-(oldP[0]+77)) < 0.01 && Math.abs(p[1]-(oldP[1]+33)) < 0.01);
  check(hasNew, '河岸顶点移动后，湖的沿河边界没有重算');
}

// ---- 往返：接海岸 / 接湖的链接必须原样存回来 ----
{
  const segRT = api.S.segs[0];
  const cstRT = api.S.coasts[0];
  api.attachSea(segRT.id, api.mouthIndex(segRT), cstRT.id, cstRT.pts[0][0], cstRT.pts[0][1]);
  const lkRT = api.S.lakes[0];
  api.attachLake(api.S.segs[1].id, api.mouthIndex(api.S.segs[1]), lkRT.id, lkRT.pts[0][0], lkRT.pts[0][1]);
  const plRT = api.payload();
  api.loadData(plRT);
  const s0 = api.S.segs.find(s => s.id === segRT.id);
  const seaAfter = (s0.links || []).find(L => L.kind === 'sea');
  check(!!seaAfter, '往返后入海链接丢了');
  check(seaAfter.coast === cstRT.id, '往返后海岸 id 丢了：' + JSON.stringify(seaAfter));
  const s1 = api.S.segs[1];
  const lakeAfter = (s1.links || []).find(L => L.lake);
  check(!!lakeAfter, '往返后入湖链接丢了');
  check(lakeAfter.lake === lkRT.id, '往返后湖 id 丢了');
}

// ---- 选择模式：点湖体 / 海岸线就能选中（不必去列表里找） ----
els['bSelect'].onclick();
api.S.sel = null; api.S.selLake = null; api.S.selCoast = null;
const lkB = api.S.lakes[0];
let sx = 0, sy = 0;
for (const q2 of lkB.pts.slice(0, -1)){ sx += q2[0]; sy += q2[1]; }
const cnt = lkB.pts.length - 1;
const cb = toScreen(sx / cnt, sy / cnt);
at(cb[0], cb[1]);
check(api.S.selLake === lkB.id, '点湖体没选中湖泽，实际 ' + api.S.selLake);

api.S.sel = null; api.S.selLake = null; api.S.selCoast = null;
// 单独画一条远离河湖的海岸线，专门测"点选"
els['bCoast'].onclick();
at(60, 1200); at(140, 1250); at(90, 1290);
listeners.__win.keydown({ key: 'Enter', target: { tagName: 'CANVAS' } });
const cstB = api.S.coasts[api.S.coasts.length - 1];
check(!!cstB, '测试用海岸线没生成');
els['bSelect'].onclick();
api.S.sel = null; api.S.selLake = null; api.S.selCoast = null;
const cq = toScreen(cstB.pts[1][0], cstB.pts[1][1]);
at(cq[0] + 2, cq[1] + 2);
check(api.S.selCoast === cstB.id, '点海岸线没选中海岸，实际 ' + api.S.selCoast);

// ---- 真实数据回归：淮水被切成 r003/r011 两段，跨段湖泊必须能沿河闭合 ----
try {
  const fs = require('fs');
  const path = require('path');
  const real = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data/map/rivers/river_segments.json'), 'utf8'));
  api.loadData(real);
  // 多段边界的湖泽（大云梦泽）必须能正确重建
  const ym = api.S.lakes.find(l => l.name === '大云梦泽');
  if (ym){
    check(Array.isArray(ym.pieces) && ym.pieces.length >= 4, '大云梦泽应有多段边界，实际 ' + (ym.pieces || []).length);
    check(ym.pts.length > 40, '大云梦泽环点太少：' + ym.pts.length);
    const rb = ym.pieces.filter(p => p.kind === 'river');
    check(rb.length >= 2, '大云梦泽应有至少两段沿河边界，实际 ' + rb.length);
    check(rb.every(p => p.path && p.path.length >= 1), '沿河段没有算出路径');
  }

  const huai = api.S.segs.filter(s => s.name === '淮水');
  check(huai.length === 2, '真实数据里淮水应有 2 段，实际 ' + huai.length);
  const [h1, h2] = huai;
  // 取两段各自的端点，其中一个端点贴近另一段
  const cand = [];
  for (const pa of [h1.pts[0], h1.pts[h1.pts.length-1]])
    for (const pb of [h2.pts[0], h2.pts[h2.pts.length-1]])
      cand.push({ a: pa, b: pb, d: Math.hypot(pa[0]-pb[0], pa[1]-pb[1]) });
  cand.sort((x, y) => x.d - y.d);
  const pair = cand[0];                       // 两段的接缝

  els['bLake'].onclick();
  const A = toScreen(pair.a[0], pair.a[1]);
  const B = toScreen(pair.b[0], pair.b[1]);
  at(A[0], A[1]);
  at(A[0] + 50, A[1] - 50);
  at(B[0] + 14, B[1] + 9);                    // 终点落在另一段端点附近（~17 屏幕像素）
  listeners.__win.keydown({ key: 'Enter', target: { tagName: 'CANVAS' } });
  const lkR = api.S.lakes[api.S.lakes.length - 1];
  check(!!lkR.arc && lkR.arc.path.length >= 2, '真实数据：跨段 arc 未生成（' + (lkR.arc && lkR.arc.path.length) + '）');
  check(lkR.arc.from && lkR.arc.to, '真实数据：arc 缺少起止记录');

  // 同一段、同一条河：起点吸上后，落点必须"点得出来"
  const segH = h1;
  const i0 = 10;
  els['bLake'].onclick();
  const p0 = toScreen(segH.pts[i0][0], segH.pts[i0][1]);
  const pT = toScreen(segH.pts[40][0], segH.pts[40][1]);   // 同段第 41 个顶点
  at(p0[0], p0[1]);
  at(p0[0] + 70, p0[1] - 50);
  at(pT[0] + 8, pT[1] + 6);                 // 点在线旁 ~10 屏幕像素处
  const es = api.S.draft.snapAtEnd;
  const i0real = api.S.draft.snapAtStart.idx;
  check(!!es, '落点没吸到河道顶点');
  const ld = api.S.draft.pts[api.S.draft.pts.length - 1];
  const vs = api.S.segs.find(x => x.id === es.id).pts[es.idx];
  check(Math.hypot(ld[0]-vs[0], ld[1]-vs[1]) < 0.01, '落点坐标与吸附顶点不一致');
  listeners.__win.keydown({ key: 'Enter', target: { tagName: 'CANVAS' } });
  const lkS = api.S.lakes[api.S.lakes.length - 1];
  check(!!lkS.arc, '同段湖泊没有 arc');
  check(lkS.arc.path.length >= 2, '同段 arc 太短：' + lkS.arc.path.length);
  const verts = allRiverVerts();
  check(lkS.arc.path.every(pp => verts.has(pp[0].toFixed(1) + ',' + pp[1].toFixed(1))),
        'arc 混入了非河道顶点的点');
} catch (e) {
  console.error('FAIL: 脚本执行抛异常 ->', e && e.stack || e);
  process.exit(1);
}

console.log('PASS  河名/段名/水量/分段/认父/流向/运河两端/往返/岔出/海岸线/入海/折叠/湖泽 全部通过',
  '| ctx 调用', JSON.stringify(calls));
process.exit(0);
