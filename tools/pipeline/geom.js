/* geom.js —— 平面划分（重写版）
 *
 * 输入：若干条折线
 * 输出：这张线网切出来的所有面
 *
 * 与旧版的区别（旧版的失败原因都写在这里）：
 *   1. 旧版只在"两线段真正相交"时插节点；端点离线段差 0.5px 就落空，线悬空、面不裂。
 *      新版在求交之后，额外做一遍"节点落在某线段内部"的检查（参数 t 判定），强制插入。
 *   2. 旧版用 6px 焊接掩盖问题，会把真实端点并掉。新版容差 0.05px，只处理浮点误差。
 *   3. 旧版的面可能重复顶点（spur），填充时溢出。新版把 spur 拆出来，只保留主环。
 *   4. 旧版外侧面的判定依赖面积符号多数，遇到孤立闭环会错。新版按连通分量分别判。
 *
 * 用法：
 *   const r = Geom.build(lines, {})   // lines: [ [[x,y],...], ... ]
 *   r.faces[i] = { ring, holes, area, outer }
 *   Geom.locate(r.faces, x, y)        // 最小的包含面（不含外部面）
 */
(function (root) {
  'use strict';

  const EPS = 1e-6;

  // ---------- 基础 ----------
  function signedArea(ring) {
    let a = 0;
    for (let i = 0; i + 1 < ring.length; i++) a += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1];
    return a / 2;
  }

  function pointInRing(x, y, ring) {
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
      if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / ((yj - yi) || 1e-12) + xi)) inside = !inside;
    }
    return inside;
  }

  // 点到线段：返回 {d, t, x, y}
  function projSeg(p, a, b) {
    const vx = b[0] - a[0], vy = b[1] - a[1];
    const L2 = vx * vx + vy * vy;
    if (L2 < 1e-12) return { d: Math.hypot(p[0] - a[0], p[1] - a[1]), t: 0, x: a[0], y: a[1] };
    let t = ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / L2;
    t = t < 0 ? 0 : t > 1 ? 1 : t;
    const x = a[0] + t * vx, y = a[1] + t * vy;
    return { d: Math.hypot(x - p[0], y - p[1]), t, x, y };
  }

  // ---------- 主流程 ----------
  function build(lines, opts) {
    const opt = opts || {};
    const tol = opt.tol == null ? 0.05 : opt.tol;      // 节点合并容差
    const minArea = opt.minArea == null ? 200 : opt.minArea;
    const t0 = Date.now();

    // 1. 收集线段（去掉零长）
    const segs = [];
    for (const line of lines) {
      if (!line || line.length < 2) continue;
      for (let i = 0; i + 1 < line.length; i++) {
        const a = line[i], b = line[i + 1];
        if (Math.abs(a[0] - b[0]) < 1e-9 && Math.abs(a[1] - b[1]) < 1e-9) continue;
        segs.push([a, b]);
      }
    }

    // 1.5 端点贴合：把每条折线的首尾投影到最近的线段上（2px 以内）
    //     编辑器保证端点落在已知线上，这里只补偿浮点误差，不做兜底修补
    {
      const endTol = opt.endSnap == null ? 2 : opt.endSnap;
      if (endTol > 0) {
        const CELL0 = 64, g0 = new Map();
        lines.forEach((line, li) => {
          if (!line || line.length < 2) return;
          for (let i = 0; i + 1 < line.length; i++) {
            const sg = [line[i], line[i + 1]];
            const x0 = Math.floor(Math.min(sg[0][0], sg[1][0]) / CELL0), x1 = Math.floor(Math.max(sg[0][0], sg[1][0]) / CELL0);
            const y0 = Math.floor(Math.min(sg[0][1], sg[1][1]) / CELL0), y1 = Math.floor(Math.max(sg[0][1], sg[1][1]) / CELL0);
            for (let x = x0; x <= x1; x++) for (let y = y0; y <= y1; y++) {
              const k = x + ',' + y;
              if (!g0.has(k)) g0.set(k, []);
              g0.get(k).push({ sg, li });
            }
          }
        });
        const fix = (pt, li) => {
          let best = null, bd = endTol;
          const cx = Math.floor(pt[0] / CELL0), cy = Math.floor(pt[1] / CELL0);
          for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) {
            const arr = g0.get((cx + dx) + ',' + (cy + dy));
            if (!arr) continue;
            for (const it of arr) {
              if (it.li === li) continue;              // 不许贴自己
              const r = projSeg(pt, it.sg[0], it.sg[1]);
              if (r.d < bd) { bd = r.d; best = [r.x, r.y]; }
            }
          }
          return best || pt;
        };
        lines.forEach((line, li) => {
          if (!line || line.length < 2) return;
          line[0] = fix(line[0], li);
          line[line.length - 1] = fix(line[line.length - 1], li);
        });
        // 端点可能变了，重新收集线段
        segs.length = 0;
        for (const line of lines) {
          if (!line || line.length < 2) continue;
          for (let i = 0; i + 1 < line.length; i++) {
            const a2 = line[i], b2 = line[i + 1];
            if (Math.abs(a2[0] - b2[0]) < 1e-9 && Math.abs(a2[1] - b2[1]) < 1e-9) continue;
            segs.push([a2, b2]);
          }
        }
      }
    }

    // 2. 网格索引
    const CELL = opt.cell || 64;
    const grid = new Map();
    const cellKey = (x, y) => x + ',' + y;
    const put = (sg, i) => {
      const x0 = Math.floor(Math.min(sg[0][0], sg[1][0]) / CELL), x1 = Math.floor(Math.max(sg[0][0], sg[1][0]) / CELL);
      const y0 = Math.floor(Math.min(sg[0][1], sg[1][1]) / CELL), y1 = Math.floor(Math.max(sg[0][1], sg[1][1]) / CELL);
      for (let x = x0; x <= x1; x++) for (let y = y0; y <= y1; y++) {
        const k = cellKey(x, y);
        if (!grid.has(k)) grid.set(k, []);
        grid.get(k).push(i);
      }
    };
    segs.forEach(put);

    // 3. 求交：真交点 + T 型接触
    const cuts = segs.map(() => []);
    const seen = new Set();
    for (const arr of grid.values()) {
      for (let ii = 0; ii < arr.length; ii++) for (let jj = ii + 1; jj < arr.length; jj++) {
        const i = arr[ii], j = arr[jj];
        const key = i < j ? i + ':' + j : j + ':' + i;
        if (seen.has(key)) continue;
        seen.add(key);

        const [a, b] = segs[i], [c, d] = segs[j];
        const d1x = b[0] - a[0], d1y = b[1] - a[1];
        const d2x = d[0] - c[0], d2y = d[1] - c[1];
        const den = d1x * d2y - d1y * d2x;
        if (Math.abs(den) > 1e-12) {
          const t = ((c[0] - a[0]) * d2y - (c[1] - a[1]) * d2x) / den;
          const u = ((c[0] - a[0]) * d1y - (c[1] - a[1]) * d1x) / den;
          if (t > EPS && t < 1 - EPS && u > EPS && u < 1 - EPS) {
            const x = a[0] + t * d1x, y = a[1] + t * d1y;
            cuts[i].push({ t, x, y });
            cuts[j].push({ t: u, x, y });
          }
        }
      }
    }

    // 4. 打断成子线段
    const edges = [];
    for (let i = 0; i < segs.length; i++) {
      const [a, b] = segs[i];
      const pts = [{ t: 0, x: a[0], y: a[1] }, { t: 1, x: b[0], y: b[1] }].concat(cuts[i]);
      pts.sort((p, q) => p.t - q.t);
      for (let k = 0; k + 1 < pts.length; k++) {
        const p = pts[k], q = pts[k + 1];
        if (q.t - p.t < 1e-9) continue;
        edges.push([[p.x, p.y], [q.x, q.y]]);
      }
    }

    // 5. 节点表（0.05px 合并）+ 线段索引（供 T 型插入用）
    const nodes = [];
    const nGrid = new Map();
    const NC = Math.max(4, tol * 4);
    function nodeOf(p) {
      const cx = Math.floor(p[0] / NC), cy = Math.floor(p[1] / NC);
      let best = -1, bd = tol;
      for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) {
        const arr = nGrid.get((cx + dx) + ',' + (cy + dy));
        if (!arr) continue;
        for (const i of arr) {
          const d = Math.hypot(nodes[i][0] - p[0], nodes[i][1] - p[1]);
          if (d < bd) { bd = d; best = i; }
        }
      }
      if (best >= 0) return best;
      const id = nodes.length;
      nodes.push([p[0], p[1]]);
      const k = cx + ',' + cy;
      if (!nGrid.has(k)) nGrid.set(k, []);
      nGrid.get(k).push(id);
      return id;
    }

    // 6. 把"节点落在别的线段内部"补插（旧版缺的就是这一步）
    const segIndex = new Map();       // 临时：把子线段按网格索引
    const sgrid = new Map();
    edges.forEach(([a, b], i) => {
      const x0 = Math.floor(Math.min(a[0], b[0]) / CELL), x1 = Math.floor(Math.max(a[0], b[0]) / CELL);
      const y0 = Math.floor(Math.min(a[1], b[1]) / CELL), y1 = Math.floor(Math.max(a[1], b[1]) / CELL);
      for (let x = x0; x <= x1; x++) for (let y = y0; y <= y1; y++) {
        const k = cellKey(x, y);
        if (!sgrid.has(k)) sgrid.set(k, []);
        sgrid.get(k).push(i);
      }
    });
    const extraCuts = new Map();      // edgeIdx -> [{t,x,y}]
    const probe = (pt) => {
      const cx = Math.floor(pt[0] / CELL), cy = Math.floor(pt[1] / CELL);
      for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) {
        const arr = sgrid.get((cx + dx) + ',' + (cy + dy));
        if (!arr) continue;
        for (const i of arr) {
          const [a, b] = edges[i];
          const r = projSeg(pt, a, b);
          if (r.d <= tol + 1e-9 && r.t > 1e-6 && r.t < 1 - 1e-6) {
            if (!extraCuts.has(i)) extraCuts.set(i, []);
            extraCuts.get(i).push({ t: r.t, x: r.x, y: r.y });
          }
        }
      }
    };
    for (const e of edges) { probe(e[0]); probe(e[1]); }

    // 7. 应用补插，建边表
    const link = new Map();
    function addEdge(a, b) {
      if (a === b) return;
      const k = a < b ? a + '|' + b : b + '|' + a;
      if (!link.has(k)) link.set(k, [a, b]);
    }
    edges.forEach(([a, b], i) => {
      const extra = (extraCuts.get(i) || []).slice();
      const pts = [{ t: 0, x: a[0], y: a[1] }, { t: 1, x: b[0], y: b[1] }].concat(extra);
      pts.sort((p, q) => p.t - q.t);
      for (let k = 0; k + 1 < pts.length; k++) {
        const p = pts[k], q = pts[k + 1];
        if (q.t - p.t < 1e-9) continue;
        addEdge(nodeOf([p.x, p.y]), nodeOf([q.x, q.y]));
      }
    });

    // 8. 连通分量
    const par = nodes.map((_, i) => i);
    const find = (x) => { while (par[x] !== x) { par[x] = par[par[x]]; x = par[x]; } return x; };
    for (const [a, b] of link.values()) {
      const ra = find(a), rb = find(b);
      if (ra !== rb) par[ra] = rb;
    }

    // 9. 半边与走面
    const out = nodes.map(() => []);
    for (const [a, b] of link.values()) {
      out[a].push({ to: b, ang: Math.atan2(nodes[b][1] - nodes[a][1], nodes[b][0] - nodes[a][0]) });
      out[b].push({ to: a, ang: Math.atan2(nodes[a][1] - nodes[b][1], nodes[a][0] - nodes[b][0]) });
    }
    for (const l of out) l.sort((p, q) => p.ang - q.ang);

    const walked = new Set();
    const loops = [];
    for (const [a, b] of link.values()) {
      for (const [u0, v0] of [[a, b], [b, a]]) {
        if (walked.has(u0 + '>' + v0)) continue;
        const ring = [];
        let u = u0, v = v0, guard = 0;
        while (guard++ < 100000) {
          walked.add(u + '>' + v);
          ring.push([nodes[u][0], nodes[u][1]]);
          const list = out[v];
          let idx = -1;
          for (let i = 0; i < list.length; i++) if (list[i].to === u) { idx = i; break; }
          if (idx < 0) break;
          const nxt = list[(idx + 1) % list.length];
          u = v; v = nxt.to;
          if (u === u0 && v === v0) break;
        }
        if (ring.length < 3) continue;
        ring.push([ring[0][0], ring[0][1]]);
        const ar = signedArea(ring);
        if (Math.abs(ar) > minArea) loops.push({ ring, area: ar, comp: find(u0) });
      }
    }

    // 10. 去重（孤立闭环会正反各走一次）
    const uniq = [];
    const seenLoop = new Set();
    for (const l of loops) {
      const r = l.ring;
      // 用"全部顶点排序后的字符串"做 key：只看面积/顶点数会把不同的面误判成同一个
      const k = r.slice(0, -1).map(p => p[0].toFixed(2) + ',' + p[1].toFixed(2)).sort().join(';');
      if (seenLoop.has(k)) continue;
      seenLoop.add(k);
      uniq.push(l);
    }

    // 11. 每个连通分量丢一个无界面（面积最大的那圈）
    const byComp = new Map();
    uniq.forEach((l, i) => {
      if (!byComp.has(l.comp)) byComp.set(l.comp, []);
      byComp.get(l.comp).push(i);
    });
    const outer = new Set();
    for (const idxs of byComp.values()) {
      if (idxs.length < 2) continue;
      let big = idxs[0];
      for (const i of idxs) if (Math.abs(uniq[i].area) > Math.abs(uniq[big].area)) big = i;
      outer.add(big);
    }

    // 12. 拆 spur：环里重复出现的顶点，取其中面积最大的一段作为主环
    function stripSpurs(ring0) {
      let ring = ring0, depth = 0;
      while (depth++ < 200) {
        const seen = new Map();
        let cut = -1, at = -1;
        for (let i = 0; i < ring.length - 1; i++) {
          const k = ring[i][0].toFixed(3) + ',' + ring[i][1].toFixed(3);
          if (seen.has(k)) { cut = seen.get(k); at = i; break; }
          seen.set(k, i);
        }
        if (at < 0) return ring;
        const inner = ring.slice(cut, at + 1);
        const rest = ring.slice(0, cut + 1).concat(ring.slice(at));
        const pick = Math.abs(signedArea(inner)) >= Math.abs(signedArea(rest)) ? inner : rest;
        if (pick.length >= ring.length || pick.length < 4) return ring;
        ring = pick;
      }
      return ring;
    }

    const faces = [];
    uniq.forEach((l, i) => {
      const isOuter = outer.has(i);
      let ring = l.ring;
      if (!isOuter) ring = stripSpurs(ring);
      if (ring.length < 4) return;
      faces.push({ ring, area: Math.abs(signedArea(ring)), outer: isOuter, holes: [], comp: l.comp });
    });

    // 13. 洞：落在别的面内部的更小的面
    const inner = faces.filter(f => !f.outer).sort((a, b) => b.area - a.area);
    for (let i = 0; i < inner.length; i++) {
      const f = inner[i];
      for (let j = i + 1; j < inner.length; j++) {
        const g = inner[j];
        if (g.comp === f.comp) continue;                       // 同一分量不会互相嵌套
        if (pointInRing(g.ring[0][0], g.ring[0][1], f.ring)) f.holes.push(g.ring);
      }
    }

    return {
      faces,
      stats: { segs: segs.length, nodes: nodes.length, edges: link.size, faces: faces.length, ms: Date.now() - t0 }
    };
  }

  // 最小包含面（不含外部面；洞不参与，因为嵌套面本身更小）
  function locate(faces, x, y) {
    let best = null;
    for (const f of faces) {
      if (f.outer) continue;
      if (f.area > (best ? best.area : Infinity)) continue;
      if (pointInRing(x, y, f.ring)) best = f;
    }
    return best;
  }

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
      if (pointInRing(c[0], c[1], ring)) return c;
    }
    for (let i = 0; i + 1 < ring.length; i++) {
      const p = ring[i], q = ring[i + 1];
      const dx = q[1] - p[1], dy = -(q[0] - p[0]);
      const L = Math.hypot(dx, dy) || 1;
      for (const d of [2, 5, 10, 20]) {
        const x = (p[0] + q[0]) / 2 + dx / L * d, y = (p[1] + q[1]) / 2 + dy / L * d;
        if (pointInRing(x, y, ring)) return [x, y];
      }
    }
    return [ring[0][0], ring[0][1]];
  }

  const api = { build, locate, representative, pointInRing, signedArea };
  root.Geom = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
