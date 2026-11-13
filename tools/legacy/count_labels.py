# -*- coding: utf-8 -*-
"""统计名称层里到底有多少个「地名标签」（字块按水平邻近合并成词）。"""
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
a = np.asarray(Image.open(ROOT / "assets" / "source" / "城池名称.png").convert("RGBA"))[:, :, 3] > 0
H, W = a.shape
print("ink px", int(a.sum()))

runs = []
for y in range(H):
    row = a[y]
    if not row.any():
        continue
    d = np.diff(np.concatenate(([0], row.astype(np.int8), [0])))
    st = np.where(d == 1)[0]
    en = np.where(d == -1)[0]
    for s, e in zip(st, en):
        runs.append((y, int(s), int(e)))

parent = list(range(len(runs)))


def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def union(x, y):
    rx, ry = find(x), find(y)
    if rx != ry:
        parent[ry] = rx


by_row = {}
for i, (y, x0, x1) in enumerate(runs):
    by_row.setdefault(y, []).append(i)

for y in range(1, H):
    cur = by_row.get(y, [])
    prev = by_row.get(y - 1, [])
    i = j = 0
    while i < len(cur) and j < len(prev):
        _, cx0, cx1 = runs[cur[i]]
        _, px0, px1 = runs[prev[j]]
        if cx0 < px1 + 1 and px0 < cx1 + 1:      # 允许 1px 对角连接
            union(cur[i], prev[j])
        if cx1 < px1:
            i += 1
        else:
            j += 1

agg = {}
for i, (y, x0, x1) in enumerate(runs):
    r = find(i)
    rec = agg.get(r)
    if rec is None:
        agg[r] = [x0, y, x1, y]
    else:
        rec[0] = min(rec[0], x0); rec[1] = min(rec[1], y)
        rec[2] = max(rec[2], x1); rec[3] = max(rec[3], y)

glyphs = [(b[0], b[1], b[2], b[3]) for b in agg.values()]
print("glyph components", len(glyphs))

# 按行分组后水平合并成词
glyphs.sort(key=lambda g: (g[1] // 12, g[0]))
words = []
for g in glyphs:
    x0, y0, x1, y1 = g
    merged = False
    for w in words:
        wx0, wy0, wx1, wy1 = w
        if not (y1 < wy0 - 2 or y0 > wy1 + 2):
            gap = max(x0 - wx1, wx0 - x1)
            if gap <= 9:
                w[0] = min(wx0, x0); w[1] = min(wy0, y0)
                w[2] = max(wx1, x1); w[3] = max(wy1, y1)
                merged = True
                break
    if not merged:
        words.append([x0, y0, x1, y1])

print("word blocks", len(words))
from collections import Counter
lens = Counter()
for x0, y0, x1, y1 in words:
    lens[round((x1 - x0 + 1) / 21)] += 1
print("approx chars per word:", sorted(lens.items()))
