// tools/smoke/smoke_geom.js —— 平面划分（重写版）回归测试
// 用法：node tools/smoke/smoke_geom.js
const path = require('path');
const fs = require('fs');
const G = require(path.join(__dirname, '..', 'pipeline', 'geom.js'));

let failed = 0;
function check(c, m) { if (!c) { console.error('FAIL: ' + m); failed++; } }

// 1. 正方形
{
  const r = G.build([[[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]]]);
  const inner = r.faces.filter(f => !f.outer);
  check(inner.length === 1, '正方形 1 个面，实际 ' + inner.length);
  check(Math.abs(inner[0].area - 10000) < 1, '面积 10000，实际 ' + inner[0].area);
}

// 2. 十字切四块
{
  const r = G.build([
    [[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]],
    [[0, 50], [100, 50]],
    [[50, 0], [50, 100]]
  ]);
  const inner = r.faces.filter(f => !f.outer);
  check(inner.length === 4, '十字 4 块，实际 ' + inner.length);
}

// 3. 端点差 0.4px 也要切开（旧版在这里失败）
{
  const r = G.build([
    [[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]],
    [[50, 0.4], [50, 99.6]]                       // 两端各差 0.4px 没碰到
  ]);
  const inner = r.faces.filter(f => !f.outer);
  check(inner.length === 2, '端点差 0.4px 应切 2 块，实际 ' + inner.length);
}

// 4. 内部闭环 → 洞
{
  const r = G.build([
    [[0, 0], [200, 0], [200, 200], [0, 200], [0, 0]],
    [[80, 80], [120, 80], [120, 120], [80, 120], [80, 80]]
  ]);
  const inner = r.faces.filter(f => !f.outer);
  check(inner.length === 2, '外框+内环 = 2 个面，实际 ' + inner.length);
  const big = inner.find(f => f.area > 10000);
  const small = inner.find(f => f.area < 10000);
  check(big && big.holes.length === 1, '大面应有 1 个洞，实际 ' + (big ? big.holes.length : 'n/a'));
  check(G.locate(r.faces, 10, 10) === big, '外圈点应落在大面');
  check(G.locate(r.faces, 100, 100) === small, '内圈点应落在小面');
  check(G.locate(r.faces, 100, 100) !== big, '内圈点不应落在大面');
}

// 5. 顺时针画的闭环，内部也要成面
{
  const r = G.build([[[0, 0], [0, 100], [100, 100], [100, 0], [0, 0]]]);   // 顺时针
  const inner = r.faces.filter(f => !f.outer);
  check(inner.length === 1, '顺时针闭环应有 1 个面，实际 ' + inner.length);
  check(G.locate(r.faces, 50, 50), '顺时针闭环内部应可定位');
}

// 6. 悬边不影响切分
{
  const r = G.build([
    [[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]],
    [[50, 50], [80, 80]]                          // 内部悬边
  ]);
  check(r.faces.filter(f => !f.outer).length === 1, '悬边不应多切面');
}

// 7. 弦切开：两端落在边界上，中点在面内
{
  const sq = [[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]];
  const r = G.build([sq, [[0, 50], [100, 50]]]);
  const inner = r.faces.filter(f => !f.outer);
  check(inner.length === 2, '横切线应切 2 块，实际 ' + inner.length);
}

// 8. 真实河网：加一条弦应当多出一个面
{
  const V = path.join(__dirname, '..', '..', 'data', 'map', 'vector');
  const flat = f => { const o = []; for (let i = 0; i + 1 < f.length; i += 2) o.push([f[i], f[i + 1]]); return o; };
  const rivers = JSON.parse(fs.readFileSync(path.join(V, 'rivers_w.json'), 'utf8')).map(r => flat(r.slice(1)));
  const coasts = JSON.parse(fs.readFileSync(path.join(V, 'coast_drawn.json'), 'utf8')).map(c => flat(c.pts));
  const lakes = JSON.parse(fs.readFileSync(path.join(V, 'lakes_drawn.json'), 'utf8')).map(l => flat(l.pts));
  const base = rivers.concat(coasts, lakes);

  const r0 = G.build(base, { minArea: 300 });
  const n0 = r0.faces.filter(f => !f.outer).length;

  // 找一个大面，在里面横切一条线
  // 取大面边界上两个相距较远的顶点连一条弦（端点必须落在线上，否则就是悬边）
  const big = r0.faces.filter(f => !f.outer).sort((a, b) => b.area - a.area)[0];
  const ring = big.ring;
  let i0 = 0, i1 = 1, bestD = 0;
  for (let i = 0; i < ring.length - 1; i += Math.max(1, Math.floor(ring.length / 40))) {
    const j = (i + Math.floor(ring.length / 2)) % (ring.length - 1);
    const d = Math.hypot(ring[i][0] - ring[j][0], ring[i][1] - ring[j][1]);
    if (d > bestD) { bestD = d; i0 = i; i1 = j; }
  }
  const chord = [[ring[i0][0], ring[i0][1]], [ring[i1][0], ring[i1][1]]];
  const r1 = G.build(base.concat([chord]), { minArea: 300 });
  const n1 = r1.faces.filter(f => !f.outer).length;
  check(n1 > n0, '加一条弦后面数应增加：' + n0 + ' → ' + n1);

  console.log('   真实河网：' + n0 + ' 面，' + r0.stats.ms + 'ms；加弦后 ' + n1 + ' 面');
}

console.log(failed ? ('FAIL ' + failed + ' 项') : 'PASS  平面划分（重写版）：正方形/十字/近端点/洞/顺时针/悬边/弦/真实河网');
process.exit(failed ? 1 : 0);
