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

console.log('PASS  国界绘制器：网络补全/单线闭环/两线闭环/内外判定/悬空报错/归属应用');
process.exit(0);
