// tools/smoke/smoke_border_editor.js — 国界绘制器冒烟测试
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const htmlPath = path.join(__dirname, '..', '..', 'dist', 'map-review', 'border_editor.html');
const html = fs.readFileSync(htmlPath, 'utf8');
const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].pop()[1];

const els = {}, listeners = {};
function classList(){
  const s = new Set();
  return { add:c=>s.add(c), remove:c=>s.delete(c), contains:c=>s.has(c),
    toggle:(c,on)=>{ if (on===undefined) s.has(c)?s.delete(c):s.add(c); else if(on) s.add(c); else s.delete(c); } };
}
function ctx2d(){
  const t = { canvas:{width:1200,height:800}, setTransform(){}, save(){}, restore(){},
    beginPath(){}, closePath(){}, moveTo(){}, lineTo(){}, arc(){}, rect(){}, fill(){}, stroke(){},
    fillRect(){}, clearRect(){}, strokeRect(){}, fillText(){}, strokeText(){}, setLineDash(){},
    drawImage(){}, measureText:()=>({width:10}), createLinearGradient:()=>({addColorStop(){}}) };
  return new Proxy(t, { get:(o,k)=> (k in o ? o[k] : ()=>{}), set:(o,k,v)=>{o[k]=v;return true;} });
}
function mkEl(tag, id){
  return {
    tagName:(tag||'div').toUpperCase(), id:id||'', style:{}, dataset:{}, className:'',
    innerHTML:'', textContent:'', value:'', checked:false, disabled:false, children:[],
    classList:classList(), clientWidth:1200, clientHeight:800,
    appendChild(c){ this.children.push(c); return c; },
    addEventListener(ev,fn){ (this._ev=this._ev||{})[ev]=fn; if (this.id==='cv'){ (listeners.cv=listeners.cv||{})[ev]=fn; } },
    removeEventListener(){}, setPointerCapture(){},
    getBoundingClientRect(){ return {left:0,top:0,right:1200,bottom:800,width:1200,height:800}; },
    getContext(){ return this._ctx || (this._ctx = ctx2d()); },
    querySelectorAll(){ return []; }, querySelector(){ return null; }, focus(){}, closest(){ return null; }
  };
}
const doc = {
  getElementById(id){ return els[id] || (els[id] = mkEl(id==='cv'?'canvas':'div', id)); },
  createElement(t){ return mkEl(t); },
  querySelectorAll(sel){
    if (sel.indexOf('#rail .mode') >= 0){
      return ['sel','draw'].map(k => {
        const e = els['m_'+k] || (els['m_'+k] = mkEl('button','m_'+k)); e.dataset.m = k; return e;
      });
    }
    return [];
  },
  querySelector(){ return null; }, addEventListener(){}, activeElement:null
};
const sandbox = {
  console, document: doc,
  window:{ devicePixelRatio:1, innerWidth:1200, innerHeight:800,
    addEventListener(ev,fn){ (listeners.win=listeners.win||{})[ev]=fn; }, removeEventListener(){} },
  localStorage:{ getItem:()=>null, setItem(){}, removeItem(){} },
  performance:{ now:()=>Date.now() }, setTimeout, clearTimeout, setInterval, clearInterval,
  requestAnimationFrame:fn=>setTimeout(()=>fn(0),0),
  fetch:()=>Promise.reject(new Error('no server')),
  Path2D: class { moveTo(){} lineTo(){} closePath(){} },
  Blob: class {}, URL:{createObjectURL:()=>'blob:', revokeObjectURL(){}},
  alert:()=>{}, confirm:()=>true,
  Math, JSON, Date, Map, Set, Array, Object, String, Number, Boolean, Error, Promise, Float64Array, Int32Array, Uint8Array
};
sandbox.globalThis = sandbox;
sandbox.window.document = doc;
vm.createContext(sandbox);
vm.runInContext(script, sandbox, { filename: htmlPath });

const api = sandbox.window.__BORDER_EDITOR__;
function check(c, m){ if (!c){ console.error('FAIL: ' + m); process.exit(1); } }

check(!!api, '没有暴露 __BORDER_EDITOR__');
check(api.cities.length === 1040, '城邑数不对：' + api.cities.length);
check(api.nations.length === 9, '国家数不对：' + api.nations.length);

// ---- 造一个方形"水系"：100..900 的四条边 ----
const sq = [[100,100],[900,100],[900,900],[100,900],[100,100]];
const rivers = [];
for (let i=0;i<4;i++){
  const a = sq[i], b = sq[i+1];
  rivers.push([3.0, a[0], a[1], b[0], b[1]]);   // [宽度, x1,y1, x2,y2]
}
api.setVector({ sea:[], rivers, lakes:[], coasts:[] });

// ---- 1) 一条线横穿：应补成上半（面积 800*300） ----
api.setEdges([{ id:'b001', pts:[[100,400],[900,400]],
  ends:[{kind:'river',id:'r0',idx:0,x:100,y:400,ok:true},{kind:'river',id:'r2',idx:0,x:900,y:400,ok:true}] }]);
let r = api.buildRealm(['b001']);
check(!r.error, '单线闭环失败：' + r.error);
const expect1 = 800*300;
check(Math.abs(r.area - expect1)/expect1 < 0.02,
      '单线面积不对：' + Math.round(r.area) + ' vs ' + expect1);

// ---- 2) 两条线 + 两侧水系补全：应成 800×200 的带 ----
api.setEdges([
  { id:'b001', pts:[[100,300],[900,300]], ends:[] },
  { id:'b002', pts:[[100,500],[900,500]], ends:[] }
]);
r = api.buildRealm(['b001','b002']);
check(!r.error, '两线闭环失败：' + r.error);
const expect2 = 800*200;
check(Math.abs(r.area - expect2)/expect2 < 0.05,
      '两线面积不对：' + Math.round(r.area) + ' vs ' + expect2);

// ---- 3) 点在多边形内 ----
check(api.pointInPoly([500,400], r.ring) === true, '带内点应判为内部');
check(api.pointInPoly([500,100], r.ring) === false, '带外点应判为外部');

// ---- 4) 端点离网络太远 → 明确报错而不是生成鬼东西 ----
api.setEdges([{ id:'b009', pts:[[2000,2000],[2500,2500]], ends:[] }]);
const bad = api.buildRealm(['b009']);
check(!!bad.error, '悬空边界线应当报错');

// ---- 5) 应用归属：带内的城邑应改成该国家 ----
api.setEdges([
  { id:'b001', pts:[[100,300],[900,300]], ends:[] },
  { id:'b002', pts:[[100,500],[900,500]], ends:[] }
]);
r = api.buildRealm(['b001','b002']);
check(!r.error, '重建失败：' + r.error);
const nat = api.nations[0];
// 用一个真实的城邑造一个 100x100 的方框
const c0 = api.cities[10];
const box = [[c0.x-50,c0.y-50],[c0.x+50,c0.y-50],[c0.x+50,c0.y+50],[c0.x-50,c0.y+50],[c0.x-50,c0.y-50]];
api.realms.push({ id:'q1', name:'测试', nation:nat.id, edges:['b001','b002'], ring:box, area:10000 });
const before = Object.keys(api.owner).length;
api.applyRealm(api.realms[0]);
check((api.owner[c0.id]||{}).n === nat.id, '疆域内城邑没有改归属：' + JSON.stringify(api.owner[c0.id]));
const inside = api.cities.filter(c => api.pointInPoly([c.x,c.y], box));
check(inside.every(c => (api.owner[c.id]||{}).n === nat.id), '方框内还有城邑没改归属');
console.log('  方框内城邑', inside.length, '个 →', nat.name, '（原有归属', before, '个）');

// ---- 6) 画线是"一次次点"，不是跟着鼠标记点 ----
api.setVector({ sea:[], rivers, lakes:[], coasts:[] });
api.setEdges([]);
api.S.mode = 'draw';
const ev = (x,y) => ({ button:0, clientX:x, clientY:y, preventDefault(){}, code:'', key:'' });
const pd = listeners.cv.pointerdown, pm = listeners.cv.pointermove;
api.center(500, 500, 1);
const sp = (wx,wy) => api.w2s(wx,wy);
let p1 = sp(100, 400); pd(ev(p1[0], p1[1]));
check(api.S.draft && api.S.draft.pts.length === 1, '第一次点击应建立草稿起点');
for (let i=1;i<6;i++){ const q2 = sp(100 + i*40, 400); pm(ev(q2[0], q2[1])); }
check(api.S.draft.pts.length === 1, '鼠标移动不应增加顶点（实际 ' + api.S.draft.pts.length + '）');
const p2 = sp(900, 400); pd(ev(p2[0], p2[1]));
check(api.S.draft.pts.length === 2, '第二次点击才加顶点（实际 ' + api.S.draft.pts.length + '）');
check(!!api.S.draft.end, '终点应吸附到河上');

// 7) 拖顶点 → 疆域重算 → 归属跟随
(async () => {
  // 围绕一个真实城邑造水系方框，保证带子里有城
  const c0 = api.cities[10];
  const cx = c0.x, cy = c0.y;
  const q = [[cx-300,cy-300],[cx+300,cy-300],[cx+300,cy+300],[cx-300,cy+300],[cx-300,cy-300]];
  const rs = [];
  for (let i=0;i<4;i++) rs.push([3.0, q[i][0], q[i][1], q[i+1][0], q[i+1][1]]);
  api.setVector({ sea:[], rivers:rs, lakes:[], coasts:[] });

  const E1 = { id:'b001', pts:[[cx-300, cy-100],[cx+300, cy-100]], ends:[] };
  const E2 = { id:'b002', pts:[[cx-300, cy+100],[cx+300, cy+100]], ends:[] };
  api.setEdges([E1, E2]);
  const rr = api.buildRealm(['b001','b002']);
  check(!rr.error, '重建失败：' + rr.error);

  const nat2 = api.nations[1];
  api.realms.length = 0;
  api.realms.push({ id:'q1', name:'拖动测试', nation:nat2.id, edges:['b001','b002'],
                    ring:rr.ring, area:rr.area });
  await api.applyRealm(api.realms[0]);
  const a0 = api.realms[0].area;
  const inside0 = api.cities.filter(c => api.pointInPoly([c.x,c.y], api.realms[0].ring));
  check(inside0.length > 0, '拖动前带内没有城邑，无法验证');
  check(inside0.every(c => (api.owner[c.id]||{}).n === nat2.id), '拖动前归属未写入');

  // 把上边那条线往下拖到 cy+40：带子从 200 高收窄到 60
  api.setEdges([{ id:'b001', pts:[[cx-300, cy+40],[cx+300, cy+40]], ends:[] }, E2]);
  await api.syncRealmsForEdge('b001');
  const a1 = api.realms[0].area;
  check(a1 < a0, '疆域没有跟随顶点变化：' + Math.round(a0) + ' → ' + Math.round(a1));
  const expect = 600*60;
  check(Math.abs(a1 - expect)/expect < 0.06, '新面积不对：' + Math.round(a1) + ' 期望 ' + expect);

  const outside = inside0.filter(c => !api.pointInPoly([c.x,c.y], api.realms[0].ring));
  check(outside.length > 0, '没有城邑离开疆域，无法验证清理逻辑');
  check(outside.every(c => !api.owner[c.id] || !api.owner[c.id].n),
        '离开疆域的城邑仍保留归属');

console.log('PASS  国界绘制器：补全/闭环/内外判定/悬空报错/归属应用/拖点重算');
  process.exit(0);
})().catch(e => { console.error('FAIL: ' + e.message); process.exit(1); });
