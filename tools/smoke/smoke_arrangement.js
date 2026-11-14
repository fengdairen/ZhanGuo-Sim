// tools/smoke/smoke_arrangement.js —— 平面划分引擎测试
// 用法：node tools/smoke/smoke_arrangement.js
const path = require('path');
const fs = require('fs');

global.window = global;
const Arrangement = require(path.join(__dirname, '..', 'pipeline', 'arrangement.js'));

function check(c, m) { if (!c) { console.error('FAIL: ' + m); process.exit(1); } }

// ---- 1. 一个正方形 → 1 个面 ----
{
  const sq = [[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]];
  const r = Arrangement.build([sq], { minArea: 10 });
  const inner = r.faces.filter(f => !f.outer);
  check(inner.length === 1, '正方形应切出 1 个面，实际 ' + inner.length);
  check(Math.abs(inner[0].area - 10000) < 1, '面积应为 10000，实际 ' + inner[0].area);
}

// ---- 2. 十字线把正方形切成 4 块 ----
{
  const sq = [[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]];
  const h = [[0, 50], [100, 50]];
  const v = [[50, 0], [50, 100]];
  const r = Arrangement.build([sq, h, v], { minArea: 10 });
  const inner = r.faces.filter(f => !f.outer);
  check(inner.length === 4, '十字应切出 4 个面，实际 ' + inner.length);
  const total = inner.reduce((s, f) => s + f.area, 0);
  check(Math.abs(total - 10000) < 50, '四块面积合计应约为 10000，实际 ' + Math.round(total));
}

// ---- 3. 悬边不产生假面 ----
{
  const sq = [[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]];
  const tail = [[50, 50], [80, 80]];          // 完全在内部的短线段
  const r = Arrangement.build([sq, tail], { minArea: 10 });
  const inner = r.faces.filter(f => !f.outer);
  check(inner.length === 1, '内部悬边不应多切出面，实际 ' + inner.length);
}

// ---- 4. 代表点落在面内 ----
{
  const sq = [[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]];
  const r = Arrangement.build([sq, [[50, 50], [80, 80]]], { minArea: 10 });
  const f = r.faces.find(x => !x.outer);
  const c = Arrangement.representative(f);
  check(Arrangement.contains(f, c[0], c[1]), '代表点应在面内');
}

console.log('PASS  平面划分：正方形 / 十字切分 / 悬边 / 代表点');
