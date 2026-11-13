// tools/smoke_city_editor.js — 城池编辑器的冒烟测试（node 直接跑）
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const htmlPath = path.join(__dirname, '..', 'dist', 'map-review', 'city_editor.html');
const html = fs.readFileSync(htmlPath, 'utf8');
const m = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
const script = m[m.length - 1][1];

const listeners = {};
const els = {};
const calls = {};

function classList(){
  const s = new Set();
  return { add:c=>s.add(c), remove:c=>s.delete(c), contains:c=>s.has(c),
    toggle:(c,on)=>{ if (on === undefined) s.has(c)?s.delete(c):s.add(c); else if (on) s.add(c); else s.delete(c); } };
}
function ctx2d(){
  const target = {
    canvas:{width:1200,height:800},
    setTransform(){}, save(){}, restore(){}, beginPath(){}, closePath(){},
    moveTo(){}, lineTo(){}, arc(){}, rect(){}, fill(){}, stroke(){}, clip(){},
    fillRect(){}, clearRect(){}, strokeRect(){}, fillText(){}, strokeText(){},
    measureText:()=>({width:20}),
    createLinearGradient:()=>({addColorStop(){}}),
    createRadialGradient:()=>({addColorStop(){}}),
    createPattern:()=>({})
  };
  return new Proxy(target, {
    get(t,k){ if (k in t) return t[k]; return (...a)=>{ calls[k]=(calls[k]||0)+1; }; },
    set(t,k,v){ t[k]=v; return true; }
  });
}
function mkEl(tag, id){
  const el = {
    tagName:(tag||'div').toUpperCase(), id:id||'',
    style:{}, dataset:{}, className:'', innerHTML:'', textContent:'', value:'',
    checked:false, children:[], classList:classList(),
    clientWidth:1200, clientHeight:800,
    appendChild(c){ this.children.push(c); return c; },
    addEventListener(ev, fn){ (this._ev = this._ev || {})[ev] = fn;
      if (this.id === 'cv'){ (listeners['cv'] = listeners['cv'] || {})[ev] = fn; } },
    removeEventListener(){},
    getBoundingClientRect(){ return {left:0, top:0, right:1200, bottom:800, width:1200, height:800}; },
    setPointerCapture(){}, releasePointerCapture(){}, focus(){},
    getContext(){ return this._ctx || (this._ctx = ctx2d()); },
    querySelectorAll(){ return []; },
    querySelector(){ return null; },
    closest(){ return null; }
  };
  return el;
}
const doc = {
  getElementById(id){ return els[id] || (els[id] = mkEl(id === 'cv' ? 'canvas' : 'div', id)); },
  createElement(tag){ return mkEl(tag); },
  querySelectorAll(sel){
    if (sel.indexOf('#rail .mode') >= 0){
      return ['sel','add','paint'].map(k => {
        const e = els['mode_' + k] || (els['mode_' + k] = mkEl('button', 'mode_' + k));
        e.dataset.m = k;
        return e;
      });
    }
    return [];
  },
  querySelector(){ return null; },
  addEventListener(ev, fn){ (listeners.__doc = listeners.__doc || {})[ev] = fn; },
  activeElement: null
};
const sandbox = {
  console, document: doc,
  window: { devicePixelRatio:1, innerWidth:1200, innerHeight:800,
    addEventListener(ev, fn){ (listeners.__win = listeners.__win || {})[ev] = fn; },
    removeEventListener(){} },
  localStorage: { getItem:()=>null, setItem(){}, removeItem(){} },
  performance: { now: () => Date.now() },
  setTimeout, clearTimeout, setInterval, clearInterval,
  requestAnimationFrame: fn => setTimeout(() => fn(Date.now()), 0),
  fetch: () => Promise.reject(new Error('no server in test')),
  Path2D: class { constructor(){} moveTo(){} lineTo(){} closePath(){} },
  Blob: class {}, URL: { createObjectURL: () => 'blob:x', revokeObjectURL(){} },
  alert: () => {}, confirm: () => true,
  Math, JSON, Date, Map, Set, Array, Object, String, Number, Boolean, Error, Promise
};
sandbox.globalThis = sandbox;
sandbox.window.document = doc;
vm.createContext(sandbox);
vm.runInContext(script, sandbox, { filename: htmlPath });

const api = sandbox.window.__CITY_EDITOR__;
function check(cond, msg){ if (!cond){ console.error('FAIL: ' + msg); process.exit(1); } }

check(!!api, '没有暴露 __CITY_EDITOR__');
check(api.items.length === 1094, '城池+部族应为 1094，实际 ' + api.items.length);
check(api.items.filter(i => i.t === 0).length === 1040, '城邑应为 1040');
check(api.pops.length === 1094, '人口行应为 1094');
check(api.S.scale > 0, '初始缩放未设置');
check(api.S && typeof api.owner === 'object', '归属表未初始化');

// 命中测试
const first = api.items.find(i => i.t === 0);
check(api.hit(first.x, first.y, 9) && api.hit(first.x, first.y, 9).id === first.id, '点不中第一个城邑');

// 拖动移动
const ev = (x, y) => ({ button:0, clientX:x, clientY:y, shiftKey:false, pointerId:1,
  preventDefault(){}, code:'', key:'' });
const [sx, sy] = api.w2s(first.x, first.y);
const pd = listeners['cv'].pointerdown, pm = listeners['cv'].pointermove, pu = listeners['cv'].pointerup;
const x0 = first.x, y0 = first.y;

// 第一次点：只选中，不动
pd(ev(sx, sy)); pu(ev(sx, sy));
check(api.S.sel.has(first.id), '点击没有选中');
check(api.items.find(i => i.id === first.id).x === x0, '第一次点击不应移动');

// 微小抖动（2px）也不应移动
pd(ev(sx, sy)); pm(ev(sx + 2, sy + 1)); pu(ev(sx + 2, sy + 1));
check(api.items.find(i => i.id === first.id).x === x0, '2px 抖动不应移动');

// 明确拖动才动
pd(ev(sx, sy)); pm(ev(sx + 40, sy + 25)); pu(ev(sx + 40, sy + 25));
const moved = api.items.find(i => i.id === first.id);
check(Math.abs(moved.x - x0) > 1 || Math.abs(moved.y - y0) > 1,
      '拖动没有移动：' + moved.x + ',' + moved.y);

// 撤销应回到原位
api.undo();
const back = api.items.find(i => i.id === first.id);
check(Math.abs(back.x - x0) < 0.11 && Math.abs(back.y - y0) < 0.11,
      '撤销没有恢复坐标：' + back.x + ',' + back.y);

// 归属刷：点一下就上色
api.S.mode = 'paint';
els['paintNation'].value = api.nations[0].id;
const target = api.items.find(i => i.t === 0);
const [tx2, ty2] = api.w2s(target.x, target.y);
pd(ev(tx2, ty2)); pu(ev(tx2, ty2));
check(api.owner[target.id] === api.nations[0].id,
      '归属刷没生效：' + JSON.stringify(api.owner[target.id]));
api.S.mode = 'sel';

// 渲染与导出不抛异常
api.renderSel();
api.draw();
const csv = api.csvMap();
check(csv.split('\r\n').length === api.items.length + 1, '地图 CSV 行数不对');
check(api.csvOwn().split('\r\n').length === 1041, '归属 CSV 行数不对');

console.log('PASS  城池编辑器：DATA/命中/拖动/撤销/导出 ·',
  api.items.length + ' 项，人口行 ' + api.pops.length + '，归属 ' + Object.keys(api.owner).length);
process.exit(0);
