// 冒烟测试：用桩对象在 Node 里执行 map.html 的内嵌脚本，
// 验证 draw() 全流程不抛异常（沙箱内 headless 浏览器起不来，见 AGENTS.md）。
// 用法：node tools/smoke_vector_map.js
const fs = require('fs');
const path = require('path');

const html = fs.readFileSync(path.join(__dirname, '..', '..', 'dist', 'map-vector', 'map.html'), 'utf8');
const m = html.match(/<script>([\s\S]*?)<\/script>/);
if (!m) { console.error('FAIL: 找不到 script'); process.exit(1); }
let code = m[1];

// ---- canvas 2d 桩 ----
let calls = {};
const ctx = new Proxy({}, {
  get(t, k) {
    if (k === 'canvas') return { width: 1600, height: 1300 };
    if (k in t) return t[k];
    if (k === 'measureText') return (s) => ({ width: String(s).length * 12 });
    if (k === 'createRadialGradient' || k === 'createLinearGradient')
      return () => ({ addColorStop() {} });
    return (...args) => { calls[k] = (calls[k] || 0) + 1; };
  },
  set(t, k, v) { t[k] = v; return true; }
});

class Path2D {
  constructor() { this.n = 0; }
  moveTo() { this.n++; }
  lineTo() { this.n++; }
  closePath() { this.n++; }
  arc() { this.n++; }
  addPath(p) { this.n += p.n || 1; }
}

const listeners = {};
function mkEl(id) {
  return {
    id, checked: true, value: '', textContent: '',
    style: {}, classList: { add() {}, remove() {} },
    addEventListener(ev, fn) { (listeners[id] = listeners[id] || {})[ev] = fn; },
    getBoundingClientRect() { return { left: 0, top: 0, width: 1600, height: 1300 }; },
    getContext() { return ctx; },
    clientWidth: 1600, clientHeight: 1300, width: 1600, height: 1300,
    setPointerCapture() {},
    onclick: null
  };
}
const els = {};
global.document = {
  getElementById(id) { return els[id] || (els[id] = mkEl(id)); },
  createElement() { return mkEl('__off'); },     // 离屏画布桩
  addEventListener() {}
};
global.window = {
  devicePixelRatio: 1,
  addEventListener(ev, fn) { (listeners.__win = listeners.__win || {})[ev] = fn; }
};
global.Path2D = Path2D;
global.performance = { now: () => Date.now() };
global.requestAnimationFrame = (fn) => setTimeout(() => { try { fn(); } catch (e) { console.error('FAIL in raf:', e.message); process.exit(1); } }, 0);
global.setTimeout = setTimeout;
global.cancelAnimationFrame = () => {};

// 默认把 都/城/邑 全开，图层全开
try {
  eval(code);
} catch (e) {
  console.error('FAIL: 脚本执行抛异常 ->', e && e.stack || e);
  process.exit(1);
}

// 触发一次全图层重绘 + 交互路径
try {
  const cv = els['cv'];
  if (listeners['cv'] && listeners['cv'].change) {}
  // 直接调用内部函数不可行，改为触发 change 事件处理器
  for (const id of ['lSea','lLake','lRiver','lCity','lLabel','lRegion']) {
    const h = listeners[id] && listeners[id]['change'];
    if (h) h();
  }
  const wheel = listeners['cv'] && listeners['cv'].wheel;
  if (wheel) wheel({ preventDefault() {}, clientX: 800, clientY: 650, deltaY: -300 });
  const qk = listeners['q'] && listeners['q'].keydown;
  if (qk) { els['q'].value = '临淄'; qk({ key: 'Enter' }); }
} catch (e) {
  console.error('FAIL: 交互路径抛异常 ->', e && e.stack || e);
  process.exit(1);
}

console.log('PASS  调用统计:', JSON.stringify(calls));
process.exit(0);
