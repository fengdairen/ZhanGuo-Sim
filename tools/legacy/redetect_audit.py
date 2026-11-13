# -*- coding: utf-8 -*-
"""对 城池.png 做一次完整的复检：
  1) 把所有连通域按形状分类（邑/城/都/齿线/其它）；
  2) 与现有 nodes.csv 逐一比对：检出但没记录的、记录了但没检出的；
  3) 列出「其它」形状的异常块，供人工看。
不修改任何数据，只出报告。
"""
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
OFF_X, OFF_Y = 635, 874

rows = list(csv.DictReader((ROOT / "tools" / "_components.csv").open(encoding="utf-8")))
rects = [dict(x0=int(r["x0"]), y0=int(r["y0"]), x1=int(r["x1"]), y1=int(r["y1"]),
              w=int(r["w"]), h=int(r["h"]), area=int(r["area"]),
              cx=float(r["cx"]), cy=float(r["cy"])) for r in rows]
print("components", len(rects))

squares = [r for r in rects if 9 <= r["w"] <= 12 and 9 <= r["h"] <= 12 and 45 <= r["area"] <= 90]
rings = [r for r in rects if 16 <= r["w"] <= 20 and 16 <= r["h"] <= 20]
hticks = [r for r in rects if 6 <= r["w"] <= 10 and 1 <= r["h"] <= 3]
vticks = [r for r in rects if 1 <= r["w"] <= 3 and 6 <= r["h"] <= 10]

used = set()
for lst in (squares, rings, hticks, vticks):
    for r in lst:
        used.add(id(r))
others = [r for r in rects if id(r) not in used]
print(f"方块={len(squares)} 外框={len(rings)} 横齿={len(hticks)} 竖齿={len(vticks)} 其它={len(others)}")

# 分类
CELL = 32
buckets = defaultdict(list)
for t in hticks + vticks:
    buckets[(int(t["cx"]) // CELL, int(t["cy"]) // CELL)].append(t)
ring_b = defaultdict(list)
for g in rings:
    ring_b[(int(g["cx"]) // CELL, int(g["cy"]) // CELL)].append(g)


def near(d, cx, cy, rad):
    kx, ky = int(cx) // CELL, int(cy) // CELL
    out = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for it in d.get((kx + dx, ky + dy), ()):
                if abs(it["cx"] - cx) <= rad and abs(it["cy"] - cy) <= rad:
                    out.append(it)
    return out


detected = []
for s in squares:
    cx, cy = s["cx"], s["cy"]
    kind = "都" if near(ring_b, cx, cy, 3) else ("城" if len(near(buckets, cx, cy, 11)) >= 2 else "邑")
    detected.append({"x": cx + OFF_X, "y": cy + OFF_Y, "kind": kind})
print("detected markers", len(detected), Counter(d["kind"] for d in detected))

# 与现有数据比对
nodes = list(csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")))
for n in nodes:
    n["x"] = float(n["x"]); n["y"] = float(n["y"])

matched = set()
unmatched_det = []
for d in detected:
    best, bd = None, 1e9
    for i, n in enumerate(nodes):
        dd = math.hypot(d["x"] - n["x"], d["y"] - n["y"])
        if dd < bd:
            bd, best = dd, i
    if best is not None and bd <= 12:
        matched.add(best)
    else:
        unmatched_det.append((d, bd))

missing = [(i, n) for i, n in enumerate(nodes) if i not in matched]

L = []
L.append(f"复检结果：图片上检出 {len(detected)} 个标点（都 {sum(1 for d in detected if d['kind']=='都')} / "
         f"城 {sum(1 for d in detected if d['kind']=='城')} / 邑 {sum(1 for d in detected if d['kind']=='邑')}）")
L.append(f"现有数据 {len(nodes)} 条，匹配上 {len(matched)} 条")
L.append("")
L.append(f"【检出但数据里没有】{len(unmatched_det)} 个：")
for d, bd in unmatched_det:
    L.append(f"   ({d['x']:.0f},{d['y']:.0f})  {d['kind']}  最近记录距离 {bd:.1f}px")
L.append("")
L.append(f"【数据里有但图上没检出】{len(missing)} 条：")
for i, n in missing:
    L.append(f"   {n['id']}  {n['name']}  {n['kind']}  ({n['x']:.0f},{n['y']:.0f})")
L.append("")
L.append(f"【形状异常块】{len(others)} 个：")
for r in others[:40]:
    L.append(f"   ({r['cx']+OFF_X:.0f},{r['cy']+OFF_Y:.0f})  {r['w']}x{r['h']}  area={r['area']}")

(ROOT / "tools" / "_redetect_report.txt").write_text("\n".join(L), encoding="utf-8")
print("report written")
