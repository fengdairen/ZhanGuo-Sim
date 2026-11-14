/* arrangement.js —— 平面划分（planar arrangement）与面提取
 *
 * 输入：若干条折线（边界线、河流、海岸、湖泊）
 * 输出：这张线网切出来的所有"面"（face），每个面是一圈点 + 面积 + 内部代表点
 *
 * 做法：
 *   1. 线段按网格索引，只和邻近线段求交
 *   2. 交点处互相打断，得到"子线段"
 *   3. 节点按 0.1px 取整合并
 *   4. 每个节点上的出边按极角排序，用半边规则走面
 *
 * 用法：Arrangement.build(polylines, {minArea}) → {faces, stats}
 */
(function (global) {
  'use strict';

  const EPS = 1e-9;

  function area(ring) {
    let a = 0;
    for (let i = 0; i + 1 < ring.length; i++) {
      a += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1];
    }
    return a / 2;
  }

  // 两线段交点（不含共线重叠），返回参数 t,u 与交点
  function segX(p1, p2, p3, p4) {
    const d1x = p2[0] - p1[0], d1y = p2[1] - p1[1];
    const d2x = p4[0] - p3[0], d2y = p4[1] - p3[1];
    const den = d1x * d2y - d1y * d2x;
    if (Math.abs(den) < EPS) return null;
    const t = ((p3[0] - p1[0]) * d2y - (p3[1] - p1[1]) * d2x) / den;
    const u = ((p3[0] - p1[0]) * d1y - (p3[1] - p1[1]) * d1x) / den;
    if (t < -EPS || t > 1 + EPS || u < -EPS || u > 1 + EPS) return null;
    return { t, u, x: p1[0] + t * d1x, y: p1[1] + t * d1y };
  }

  function rdp(pts, eps) {
    if (pts.length < 3) return pts;
    // 闭合环首尾同点，RDP 会退化（基线长度为 0），直接不简化
    const a0 = pts[0], aN = pts[pts.length - 1];
    if (Math.abs(a0[0] - aN[0]) < 1e-6 && Math.abs(a0[1] - aN[1]) < 1e-6) return pts;
    const keep = new Uint8Array(pts.length);
    keep[0] = keep[pts.length - 1] = 1;
    const stack = [[0, pts.length - 1]];
    while (stack.length) {
      const [i, j] = stack.pop();
      let best = -1, bd = eps;
      const a = pts[i], b = pts[j];
      const vx = b[0] - a[0], vy = b[1] - a[1];
      const L = Math.hypot(vx, vy) || 1e-9;
      for (let k = i + 1; k < j; k++) {
        const p = pts[k];
        const d = Math.abs((p[0] - a[0]) * vy - (p[1] - a[1]) * vx) / L;
        if (d > bd) { bd = d; best = k; }
      }
      if (best > 0) { keep[best] = 1; stack.push([i, best], [best, j]); }
    }
    const out = [];
    for (let i = 0; i < pts.length; i++) if (keep[i]) out.push(pts[i]);
    return out;
  }

  function build(polylines, opts) {
    opts = opts || {};
    const minArea = opts.minArea == null ? 100 : opts.minArea;
    const t0 = Date.now();

    const simp = opts.simplify == null ? 1.0 : opts.simplify;   // 不能大：会把河口/汇流点拉离原位，面就漏
    if (simp > 0) polylines = polylines.map(l => rdp(l, simp));

    // ---- 0. 贴线吸附：边界线的顶点贴到最近的水系线段上 ----
    // 否则「边界线离河 10px」会切出一条条细缝，面就碎了
    if (opts.snapTo && opts.snapTo.length){
      const tol = opts.snapTol == null ? 8 : opts.snapTol;
      const CELL0 = 64, grid0 = new Map();
      const g0 = (x, y) => x + ',' + y;
      for (const line of opts.snapTo){
        for (let i = 0; i + 1 < line.length; i++){
          const a = line[i], b = line[i + 1];
          const x0 = Math.floor(Math.min(a[0], b[0]) / CELL0), x1 = Math.floor(Math.max(a[0], b[0]) / CELL0);
          const y0 = Math.floor(Math.min(a[1], b[1]) / CELL0), y1 = Math.floor(Math.max(a[1], b[1]) / CELL0);
          for (let x = x0; x <= x1; x++) for (let y = y0; y <= y1; y++){
            const k = g0(x, y);
            if (!grid0.has(k)) grid0.set(k, []);
            grid0.get(k).push([a, b]);
          }
        }
      }
      const project = (pt) => {
        const cx = Math.floor(pt[0] / CELL0), cy = Math.floor(pt[1] / CELL0);
        let best = null, bd = tol;
        for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++){
          const arr = grid0.get(g0(cx + dx, cy + dy));
          if (!arr) continue;
          for (const [a, b] of arr){
            const vx = b[0] - a[0], vy = b[1] - a[1];
            const L2 = vx * vx + vy * vy || 1e-9;
            let t = ((pt[0] - a[0]) * vx + (pt[1] - a[1]) * vy) / L2;
            t = Math.max(0, Math.min(1, t));
            const px = a[0] + t * vx, py = a[1] + t * vy;
            const d = Math.hypot(px - pt[0], py - pt[1]);
            if (d < bd){ bd = d; best = [px, py]; }
          }
        }
        return best || pt;
      };
      polylines = polylines.map(line => line.map(project));
    }

    // ---- 1. 收集线段（先焊接：端点吸附到网格、去掉重复与碎段） ----
    const snap = opts.snap == null ? 0 : opts.snap;
    const snapP = snap > 0
      ? (p => [Math.round(p[0] / snap) * snap, Math.round(p[1] / snap) * snap])
      : (p => [p[0], p[1]]);
    const segSeen = new Set();
    const segs = [];
    for (const line of polylines) {
      if (!line || line.length < 2) continue;
      for (let i = 0; i + 1 < line.length; i++) {
        const a = snapP(line[i]), b = snapP(line[i + 1]);
        if (a[0] === b[0] && a[1] === b[1]) continue;
        if (snap > 0 && Math.hypot(a[0] - b[0], a[1] - b[1]) < snap) continue;   // 碎段
        const k = a[0] < b[0] || (a[0] === b[0] && a[1] < b[1])
          ? a + '|' + b : b + '|' + a;
        if (segSeen.has(k)) continue;                                 // 重复覆盖
        segSeen.add(k);
        segs.push([a, b]);
      }
    }

    // ---- 2. 网格索引 ----
    const CELL = opts.cell || 64;
    const grid = new Map();
    const gk = (x, y) => x + ',' + y;
    const segCells = new Array(segs.length);
    for (let i = 0; i < segs.length; i++) {
      const [a, b] = segs[i];
      const x0 = Math.floor(Math.min(a[0], b[0]) / CELL), x1 = Math.floor(Math.max(a[0], b[0]) / CELL);
      const y0 = Math.floor(Math.min(a[1], b[1]) / CELL), y1 = Math.floor(Math.max(a[1], b[1]) / CELL);
      const list = [];
      for (let x = x0; x <= x1; x++) for (let y = y0; y <= y1; y++) {
        const k = gk(x, y);
        if (!grid.has(k)) grid.set(k, []);
        grid.get(k).push(i);
        list.push(k);
      }
      segCells[i] = list;
    }

    // ---- 3. 求交、记录打断点 ----
    const cuts = segs.map(() => []);
    const tested = new Set();
    let hits = 0;
    for (const arr of grid.values()) {
      for (let ii = 0; ii < arr.length; ii++) {
        for (let jj = ii + 1; jj < arr.length; jj++) {
          const i = arr[ii], j = arr[jj];
          const kk = i < j ? i + ':' + j : j + ':' + i;
          if (tested.has(kk)) continue;
          tested.add(kk);
          const r = segX(segs[i][0], segs[i][1], segs[j][0], segs[j][1]);
          if (!r) continue;
          cuts[i].push({ t: r.t, x: r.x, y: r.y });
          cuts[j].push({ t: r.u, x: r.x, y: r.y });
          hits++;
        }
      }
    }

    // ---- 4. 打断成子线段，节点取整合并 ----
    // 节点焊接：容差内的点并成一个节点，否则河与河、河与边界之间的小缝会让面漏出去
    const WELD = opts.weld == null ? 6 : opts.weld;
    const nodes = [];
    const nGrid = new Map();
    const nCell = Math.max(4, WELD * 2);
    function nodeOf(p) {
      const cx = Math.floor(p[0] / nCell), cy = Math.floor(p[1] / nCell);
      if (WELD > 0){
        let best = -1, bd = WELD;
        for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++){
          const arr = nGrid.get((cx+dx)+','+(cy+dy));
          if (!arr) continue;
          for (const i of arr){
            const d = Math.hypot(nodes[i][0]-p[0], nodes[i][1]-p[1]);
            if (d < bd){ bd = d; best = i; }
          }
        }
        if (best >= 0) return best;
      }
      const i = nodes.length;
      nodes.push([Math.round(p[0]*10)/10, Math.round(p[1]*10)/10]);
      const k = cx + ',' + cy;
      if (!nGrid.has(k)) nGrid.set(k, []);
      nGrid.get(k).push(i);
      return i;
    }

    const edges = new Map();       // 'a|b' -> true
    const addEdge = (a, b) => {
      if (a === b) return;
      const k = a < b ? a + '|' + b : b + '|' + a;
      edges.set(k, [a, b]);
    };
    for (let i = 0; i < segs.length; i++) {
      const [a, b] = segs[i];
      const pts = [{ t: 0, x: a[0], y: a[1] }, { t: 1, x: b[0], y: b[1] }].concat(cuts[i]);
      pts.sort((p, q) => p.t - q.t);        // 必须整体排序，否则会生成跨越整条线的假边
      for (let k = 0; k + 1 < pts.length; k++) {
        const p = pts[k], q = pts[k + 1];
        if (Math.abs(p.t - q.t) < 1e-7) continue;
        addEdge(nodeOf([p.x, p.y]), nodeOf([q.x, q.y]));
      }
    }

    // ---- 5. 半边与面 ----
    const out = nodes.map(() => []);
    for (const [id, [a, b]] of edges) {
      out[a].push({ to: b, ang: Math.atan2(nodes[b][1] - nodes[a][1], nodes[b][0] - nodes[a][0]) });
      out[b].push({ to: a, ang: Math.atan2(nodes[a][1] - nodes[b][1], nodes[a][0] - nodes[b][0]) });
    }
    for (const list of out) list.sort((p, q) => p.ang - q.ang);

    const visited = new Set();
    const loops = [];
    const faces = [];
    const ekey = (a, b) => a + '>' + b;

    for (const [id, [a, b]] of edges) {
      for (const [u, v] of [[a, b], [b, a]]) {
        if (visited.has(ekey(u, v))) continue;
        const ring = [];
        let cu = u, cv = v, guard = 0;
        while (guard++ < 20000) {
          visited.add(ekey(cu, cv));
          ring.push([nodes[cu][0], nodes[cu][1]]);
          // 在 cv 的出边里找到 "cv→cu" 的位置，取它的逆时针前一条
          const list = out[cv];
          let idx = -1;
          for (let i = 0; i < list.length; i++) if (list[i].to === cu) { idx = i; break; }
          if (idx < 0) break;
          const nxt = list[(idx + 1) % list.length];
          cu = cv; cv = nxt.to;
          if (cu === u && cv === v) break;
        }
        if (ring.length < 3) continue;
        if (ring.length > 8000) continue;      // 走到上限的多半是坏环，丢掉
        ring.push([ring[0][0], ring[0][1]]);
        const ar = area(ring);
        if (Math.abs(ar) > minArea) loops.push({ ring, area: ar });
      }
    }

    // 有界面的环面积符号一致，外侧那个（包围全图的）符号相反 → 按多数决定保留哪一侧
    const pos = loops.filter(l => l.area > 0).length;
    const neg = loops.length - pos;
    const keepSign = pos >= neg ? 1 : -1;
    for (const l of loops){
      if (Math.sign(l.area) !== keepSign) continue;
      faces.push({ ring: keepSign > 0 ? l.ring : l.ring.slice().reverse(), area: Math.abs(l.area) });
    }

    return {
      faces,
      stats: {
        segs: segs.length, nodes: nodes.length, edges: edges.size,
        hits, faces: faces.length,
        ms: Date.now() - t0
      }
    };
  }

  // 点是否在面内（含边界）
  function contains(face, x, y) {
    const ring = face.ring;
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
      if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / ((yj - yi) || 1e-9) + xi)) inside = !inside;
    }
    return inside;
  }

  // 面的内部代表点：重心不在面内时，用边中点向内偏移
  function representative(face) {
    const ring = face.ring;
    let a = 0, cx = 0, cy = 0;
    for (let i = 0; i + 1 < ring.length; i++) {
      const cr = ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1];
      a += cr; cx += (ring[i][0] + ring[i + 1][0]) * cr; cy += (ring[i][1] + ring[i + 1][1]) * cr;
    }
    a /= 2;
    if (Math.abs(a) > 1e-6) {
      const c = [cx / (6 * a), cy / (6 * a)];
      if (contains(face, c[0], c[1])) return c;
    }
    // 退而求其次：边的中点朝内挪一点
    for (let i = 0; i + 1 < ring.length; i++) {
      const p = ring[i], q = ring[i + 1];
      const mx = (p[0] + q[0]) / 2, my = (p[1] + q[1]) / 2;
      const dx = q[1] - p[1], dy = -(q[0] - p[0]);
      const L = Math.hypot(dx, dy) || 1;
      for (const d of [2, 5, 10, 20]) {
        const x = mx + dx / L * d, y = my + dy / L * d;
        if (contains(face, x, y)) return [x, y];
      }
    }
    return [ring[0][0], ring[0][1]];
  }

  global.Arrangement = { build, contains, representative, area };
})(typeof window !== 'undefined' ? window : globalThis);

if (typeof module !== 'undefined' && module.exports) {
  module.exports = (typeof window !== 'undefined' ? window : globalThis).Arrangement;
}
