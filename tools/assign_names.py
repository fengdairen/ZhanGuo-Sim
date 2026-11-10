# -*- coding: utf-8 -*-
"""按「相邻性」把地名标签分配给城址：
   - 标签与标记垂直居中对齐（|dy| 小）
   - 水平间隙 6~45px，在标记左侧或右侧
   - 每个标签只能归属一个城址，按间隙从小到大贪心
数据源：全局 OCR + 逐城 OCR（换算回画布坐标）
"""
import csv
import json
import math
import re
from collections import Counter
from pathlib import Path

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
OX, OY = 512, 866          # 名称层 → 画布
SCALE = 3


def clean(s: str) -> str:
    s = s.replace("|", "").replace(" ", "").replace("\u3000", "")
    return re.sub(r"[^\u4e00-\u9fff]", "", s)


lines = []   # (text, x0, y0, x1, y1)

glob = json.loads((ROOT / "tools" / "_ocr_names.json").read_text(encoding="utf-8"))
if isinstance(glob, dict):
    glob = [glob]
for g in glob:
    t = clean(g["text"])
    if t:
        lines.append((t, g["x"] + OX, g["y"] + OY, g["x"] + g["w"] + OX, g["y"] + g["h"] + OY))

meta = json.loads((ROOT / "tools" / "node_crops" / "meta.json").read_text(encoding="utf-8"))
per = json.loads((ROOT / "tools" / "_ocr_nodes.json").read_text(encoding="utf-8"))
if isinstance(per, dict):
    per = [per]
for o in per:
    m = meta.get(o["id"])
    if not m:
        continue
    for l in (o.get("lines") or []):
        t = clean(l["t"])
        if not t:
            continue
        x0 = l["x"] / SCALE + m["x0"] + OX
        y0 = l["y"] / SCALE + m["y0"] + OY
        x1 = (l["x"] + l["w"]) / SCALE + m["x0"] + OX
        y1 = (l["y"] + l["h"]) / SCALE + m["y0"] + OY
        lines.append((t, x0, y0, x1, y1))

# 去重（同文本、同位置）
seen = set()
uniq = []
for t, x0, y0, x1, y1 in lines:
    key = (t, round(x0 / 6), round(y0 / 6))
    if key in seen:
        continue
    seen.add(key)
    uniq.append((t, x0, y0, x1, y1))
lines = uniq
print("line pool", len(lines))

nodes = list(csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")))
for n in nodes:
    n["x"] = float(n["x"])
    n["y"] = float(n["y"])

GAP_MIN, GAP_MAX, DY_TOL = 5, 46, 14
cands = []
for li, (t, x0, y0, x1, y1) in enumerate(lines):
    cy = (y0 + y1) / 2
    for ni, n in enumerate(nodes):
        if abs(cy - n["y"]) > DY_TOL:
            continue
        # 标签在标记右侧
        gap_r = x0 - n["x"]
        # 标签在标记左侧
        gap_l = n["x"] - x1
        gap = None
        if GAP_MIN <= gap_r <= GAP_MAX:
            gap = gap_r
        elif GAP_MIN <= gap_l <= GAP_MAX:
            gap = gap_l
        if gap is not None:
            cands.append((gap, ni, li))

cands.sort()
used_n, used_l = set(), set()
assign = {}
for gap, ni, li in cands:
    if ni in used_n or li in used_l:
        continue
    used_n.add(ni)
    used_l.add(li)
    assign[ni] = lines[li][0]

for ni, n in enumerate(nodes):
    n["name"] = assign.get(ni, "")

named = sum(1 for n in nodes if n["name"])
print(f"named {named} / {len(nodes)}  ({named/len(nodes):.0%})")
print("length hist", sorted(Counter(len(n["name"]) for n in nodes).items()))

with (ROOT / "data" / "map" / "nodes.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "name", "kind", "x", "y"])
    for n in nodes:
        w.writerow([n["id"], n["name"], n["kind"], n["x"], n["y"]])
print("written")
