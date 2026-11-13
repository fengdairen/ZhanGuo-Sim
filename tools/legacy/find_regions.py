# -*- coding: utf-8 -*-
"""从名称层里找出「没有对应城址方格」的文字块——这些是部族名。

做法：
  1) 名称层做连通域 → 字形 → 按水平邻近合并成「词」（与建城址时同一套逻辑）；
  2) 每个词按「垂直居中 + 水平间隙」配给最近的城址（一对一，全局贪心）；
  3) 配不上的词 = 部族候选；
  4) 输出候选清单 + 每个词的裁剪图（供 OCR 与人工确认）。
"""
import csv
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
CROP = ROOT / "tools" / "region_crops"
CROP.mkdir(parents=True, exist_ok=True)
for f in CROP.glob("*.png"):
    f.unlink()

alpha = np.asarray(Image.open(ROOT / "assets" / "source" / "城池名称.png").convert("RGBA"))[:, :, 3] > 0
white = Image.open(ROOT / "tools" / "_names_white.png").convert("RGB")
H, W = alpha.shape

# ---- 连通域 ----
runs = []
for y in range(H):
    row = alpha[y]
    if not row.any():
        continue
    d = np.diff(np.concatenate(([0], row.astype(np.int8), [0])))
    st = np.where(d == 1)[0]; en = np.where(d == -1)[0]
    for s, e in zip(st, en):
        runs.append((y, int(s), int(e)))

par = list(range(len(runs)))
def find(x):
    while par[x] != x:
        par[x] = par[par[x]]; x = par[x]
    return x
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb: par[rb] = ra

by_row = {}
for i, (y, x0, x1) in enumerate(runs):
    by_row.setdefault(y, []).append(i)
for y in range(1, H):
    cur = by_row.get(y, []); prev = by_row.get(y - 1, [])
    i = j = 0
    while i < len(cur) and j < len(prev):
        _, cx0, cx1 = runs[cur[i]]
        _, px0, px1 = runs[prev[j]]
        if cx0 < px1 + 1 and px0 < cx1 + 1:
            union(cur[i], prev[j])
        if cx1 < px1: i += 1
        else: j += 1

agg = {}
for i, (y, x0, x1) in enumerate(runs):
    r = find(i); rec = agg.get(r)
    if rec is None:
        agg[r] = [x0, y, x1, y]
    else:
        rec[0] = min(rec[0], x0); rec[1] = min(rec[1], y)
        rec[2] = max(rec[2], x1); rec[3] = max(rec[3], y)
glyphs = sorted((tuple(map(int, b)) for b in agg.values()), key=lambda g: (g[1], g[0]))

words = []
for g in glyphs:
    x0, y0, x1, y1 = g
    hit = False
    for w in words:
        if not (y1 < w[1] - 2 or y0 > w[3] + 2):
            if max(x0 - w[2], w[0] - x1) <= 9:
                w[0] = min(w[0], x0); w[1] = min(w[1], y0)
                w[2] = max(w[2], x1); w[3] = max(w[3], y1)
                hit = True
                break
    if not hit:
        words.append([x0, y0, x1, y1])
print("words", len(words))

# ---- 配给城址 ----
nodes = list(csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")))
OX, OY = 512, 866
for n in nodes:
    n["nx"] = float(n["x"]) - OX
    n["ny"] = float(n["y"]) - OY

pairs = []
for wi, w in enumerate(words):
    cy = (w[1] + w[3]) / 2
    for ni, n in enumerate(nodes):
        if abs(cy - n["ny"]) > 16:
            continue
        gap = min(abs(w[0] - n["nx"]), abs(n["nx"] - w[2]))
        if 2 <= gap <= 50:
            pairs.append((gap, wi, ni))
pairs.sort()
uw, un = set(), set()
for gap, wi, ni in pairs:
    if wi in uw or ni in un:
        continue
    uw.add(wi); un.add(ni)
print("assigned words", len(uw), "unassigned", len(words) - len(uw))

# ---- 候选 ----
cands = []
for wi, w in enumerate(words):
    if wi in uw:
        continue
    x0, y0, x1, y1 = w
    ww, hh = x1 - x0 + 1, y1 - y0 + 1
    if ww < 12 or hh < 12:          # 噪点
        continue
    cands.append({"x0": x0, "y0": y0, "x1": x1, "y1": y1, "w": ww, "h": hh})

cands.sort(key=lambda c: (c["y0"], c["x0"]))
print("region candidates", len(cands))

meta = {}
for i, c in enumerate(cands):
    rid = f"rg{i:03d}"
    c["id"] = rid
    pad = 6
    box = (max(0, c["x0"] - pad), max(0, c["y0"] - pad),
           min(W, c["x1"] + pad), min(H, c["y1"] + pad))
    t = white.crop(box)
    t = t.resize((t.width * 4, t.height * 4), Image.LANCZOS)
    t.save(CROP / f"{rid}.png")
    meta[rid] = {"x0": box[0], "y0": box[1], "scale": 4}

(CROP / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
with (ROOT / "data" / "map" / "regions_candidates.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "canvas_x", "canvas_y", "w", "h"])
    for c in cands:
        w.writerow([c["id"], c["x0"] + OX, c["y0"] + OY, c["w"], c["h"]])
print("crops ->", CROP)
