# -*- coding: utf-8 -*-
"""矢量化结果的合理性自检（不依赖浏览器）。

1. 有多少城邑落在海里？（应当为 0，除非该城本就是海港/岛屿）
2. 城邑到最近河道的距离分布（聚落应临水）
3. 湖面是否压到城邑
"""
import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
VEC = ROOT / "data" / "map" / "vector"
S = 4

W, H = 9101, 8509
CW, CH = W // S, H // S

coast = json.loads((VEC / "coast.json").read_text(encoding="utf-8"))
lakes = json.loads((VEC / "lakes.json").read_text(encoding="utf-8"))
rivers = json.loads((VEC / "rivers_w.json").read_text(encoding="utf-8"))

sea_img = Image.new("L", (CW, CH), 0)
d = ImageDraw.Draw(sea_img)
for poly in coast["sea"]:
    d.polygon([(p[0] / S, p[1] / S) for p in poly], fill=255)
sea = np.array(sea_img) > 127

lake_img = Image.new("L", (CW, CH), 0)
dl = ImageDraw.Draw(lake_img)
for poly in lakes:
    dl.polygon([(p[0] / S, p[1] / S) for p in poly], fill=255)
lake = np.array(lake_img) > 127

riv_img = Image.new("L", (CW, CH), 0)
dr = ImageDraw.Draw(riv_img)
for e in rivers:
    pts = [(e[i] / S, e[i + 1] / S) for i in range(1, len(e), 2)]
    dr.line(pts, fill=255, width=1)
riv = np.array(riv_img) > 127

# 距离场：反复膨胀（近似到 12 像素）
dist = np.full((CH, CW), 99, dtype=np.int16)
cur = riv.copy()
for k in range(13):
    dist[cur] = np.minimum(dist[cur], k)
    p = np.zeros_like(cur)
    p[1:, :] |= cur[:-1, :]
    p[:-1, :] |= cur[1:, :]
    p[:, 1:] |= cur[:, :-1]
    p[:, :-1] |= cur[:, 1:]
    cur |= p

rows = list(csv.DictReader(open(ROOT / "data" / "map" / "nodes.csv", encoding="utf-8-sig")))
in_sea, in_lake, no_river, ds = [], [], [], []
for r in rows:
    x, y = int(float(r["x"]) // S), int(float(r["y"]) // S)
    if not (0 <= y < CH and 0 <= x < CW):
        continue
    if sea[y, x]:
        in_sea.append(r["name"])
    if lake[y, x]:
        in_lake.append(r["name"])
    d0 = int(dist[y, x]) * S
    ds.append(d0)
    if d0 > 48:
        no_river.append((r["name"], r["kind"], d0))

print(f"城邑 {len(rows)}")
print(f"落在海域内: {len(in_sea)}  {in_sea[:8]}")
print(f"落在湖面内: {len(in_lake)}  {in_lake[:8]}")
print(f"距河道 >48px: {len(no_river)}  {no_river[:8]}")
print(f"距河道中位数 {np.median(ds):.0f}px  75分位 {np.percentile(ds,75):.0f}px  90分位 {np.percentile(ds,90):.0f}px")
