# -*- coding: utf-8 -*-
"""从 城池.png（仅符号层）提取连通域，输出统计与 CSV。
不依赖 scipy：用行游程 + 并查集做连通标记。
"""
import csv
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
SRC = ROOT / "城池.png"
OUT_CSV = ROOT / "tools" / "_components.csv"

img = Image.open(SRC).convert("RGBA")
a = np.asarray(img)
mask = a[:, :, 3] > 0
H, W = mask.shape
print("layer size", W, H, "alpha px", int(mask.sum()))

# ---------- 行游程 ----------
runs = []  # (y, x0, x1)  x1 exclusive
for y in range(H):
    row = mask[y]
    if not row.any():
        continue
    d = np.diff(np.concatenate(([0], row.astype(np.int8), [0])))
    starts = np.where(d == 1)[0]
    ends = np.where(d == -1)[0]
    for s, e in zip(starts, ends):
        runs.append((y, int(s), int(e)))

print("runs", len(runs))

# ---------- 并查集 ----------
parent = list(range(len(runs)))

def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x

def union(a_, b_):
    ra, rb = find(a_), find(b_)
    if ra != rb:
        parent[rb] = ra

# 按行分组
by_row = {}
for i, (y, x0, x1) in enumerate(runs):
    by_row.setdefault(y, []).append(i)

for y in range(1, H):
    cur = by_row.get(y, [])
    prev = by_row.get(y - 1, [])
    if not cur or not prev:
        continue
    i = j = 0
    while i < len(cur) and j < len(prev):
        cy, cx0, cx1 = runs[cur[i]]
        py, px0, px1 = runs[prev[j]]
        if cx0 < px1 and px0 < cx1:          # 8 邻接：允许对角
            union(cur[i], prev[j])
        if cx1 < px1:
            i += 1
        else:
            j += 1

# ---------- 聚合 ----------
agg = {}
for i, (y, x0, x1) in enumerate(runs):
    r = find(i)
    rec = agg.get(r)
    if rec is None:
        agg[r] = [x0, y, x1 - 1, y, x1 - x0]      # minx,miny,maxx,maxy,area
    else:
        if x0 < rec[0]: rec[0] = x0
        if y < rec[1]: rec[1] = y
        if x1 - 1 > rec[2]: rec[2] = x1 - 1
        if y > rec[3]: rec[3] = y
        rec[4] += x1 - x0

comps = [(v[0], v[1], v[2], v[3], v[4]) for v in agg.values()]
print("components", len(comps))

w_hist = Counter(c[2] - c[0] + 1 for c in comps)
h_hist = Counter(c[3] - c[1] + 1 for c in comps)
print("width hist (top)", w_hist.most_common(12))
print("height hist (top)", h_hist.most_common(12))
area_hist = Counter(c[4] for c in comps)
print("area hist (top)", area_hist.most_common(12))

# 尺寸交叉表
cross = Counter((c[2] - c[0] + 1, c[3] - c[1] + 1) for c in comps)
print("bbox (w,h) top 15:", cross.most_common(15))

with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["id", "x0", "y0", "x1", "y1", "w", "h", "area", "cx", "cy"])
    for i, (x0, y0, x1, y1, area) in enumerate(comps):
        w.writerow([i, x0, y0, x1, y1, x1 - x0 + 1, y1 - y0 + 1, area,
                    (x0 + x1) / 2, (y0 + y1) / 2])
print("csv ->", OUT_CSV)
