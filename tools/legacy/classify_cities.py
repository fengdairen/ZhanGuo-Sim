# -*- coding: utf-8 -*-
"""把连通域归类为 邑 / 城 / 都，并输出画布坐标。

规则（由点阵实测得出）：
  邑 = 10x10 空心方块
  城 = 10x10 方块 + 上下左右各一根 8x2 / 2x8 短横线（独立连通域）
  都 = 18x18 外框 + 中心 10x10 内框
所以先取所有 10x10 方块作为「城址」，再判它周围有没有外框/短横线。
"""
import csv
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
# 城池.png 在画布中的偏移（来自 PSD 图层 bbox）
OFF_X, OFF_Y = 635, 874

rows = list(csv.DictReader((ROOT / "tools" / "_components.csv").open(encoding="utf-8")))
rects = []
for r in rows:
    rects.append(dict(x0=int(r["x0"]), y0=int(r["y0"]), x1=int(r["x1"]), y1=int(r["y1"]),
                      w=int(r["w"]), h=int(r["h"]), area=int(r["area"]),
                      cx=float(r["cx"]), cy=float(r["cy"])))

squares = [r for r in rects if 9 <= r["w"] <= 12 and 9 <= r["h"] <= 12 and 45 <= r["area"] <= 90]
rings = [r for r in rects if 16 <= r["w"] <= 20 and 16 <= r["h"] <= 20]
hticks = [r for r in rects if 6 <= r["w"] <= 10 and 1 <= r["h"] <= 3]
vticks = [r for r in rects if 1 <= r["w"] <= 3 and 6 <= r["h"] <= 10]
ticks = hticks + vticks

print(f"squares={len(squares)} rings={len(rings)} hticks={len(hticks)} vticks={len(vticks)}")

# 空间索引：把短横线按格子分桶，避免 O(n^2)
CELL = 32
buckets = {}
for t in ticks:
    key = (int(t["cx"]) // CELL, int(t["cy"]) // CELL)
    buckets.setdefault(key, []).append(t)

ring_buckets = {}
for g in rings:
    key = (int(g["cx"]) // CELL, int(g["cy"]) // CELL)
    ring_buckets.setdefault(key, []).append(g)


def near(list_, cx, cy, rad):
    kx, ky = int(cx) // CELL, int(cy) // CELL
    out = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for it in list_.get((kx + dx, ky + dy), ()):
                if abs(it["cx"] - cx) <= rad and abs(it["cy"] - cy) <= rad:
                    out.append(it)
    return out


cities = []
for s in squares:
    cx, cy = s["cx"], s["cy"]
    g = near(ring_buckets, cx, cy, 3)
    t = near(buckets, cx, cy, 11)
    if g:
        kind = "都"
    elif len(t) >= 2:
        kind = "城"
    else:
        kind = "邑"
    cities.append(dict(kind=kind, cx=cx, cy=cy,
                       canvas_x=cx + OFF_X, canvas_y=cy + OFF_Y,
                       ticks=len(t), ring=bool(g)))

print("归类结果:", Counter(c["kind"] for c in cities))
print("城 的短横线数量分布:", Counter(c["ticks"] for c in cities if c["kind"] == "城"))

# 输出
out = ROOT / "data" / "map"
out.mkdir(parents=True, exist_ok=True)
with (out / "nodes.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "name", "kind", "x", "y"])
    for i, c in enumerate(sorted(cities, key=lambda c: (c["canvas_y"], c["canvas_x"]))):
        w.writerow([f"n{i:04d}", "", c["kind"], round(c["canvas_x"], 1), round(c["canvas_y"], 1)])
print("nodes ->", out / "nodes.csv")

# 叠加验证图：在合成图上标出三类
im = Image.open(ROOT / "ditu.png").convert("RGB")
draw = ImageDraw.Draw(im)
COLOR = {"都": (220, 0, 0), "城": (0, 90, 220), "邑": (0, 150, 0)}
R = {"都": 14, "城": 10, "邑": 7}
for c in cities:
    x, y, k = c["canvas_x"], c["canvas_y"], c["kind"]
    r = R[k]
    draw.ellipse([x - r, y - r, x + r, y + r], outline=COLOR[k], width=3)

crop = im.crop((3200, 3300, 4200, 4000))
crop.save(ROOT / "tools" / "_overlay_check.png")
print("overlay ->", ROOT / "tools" / "_overlay_check.png")
