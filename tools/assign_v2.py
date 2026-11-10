# -*- coding: utf-8 -*-
"""重做标签分配：全局一对一（一个文字标签只能属于一个城址）。

此前 merge_passes 是「每个城址各自投票」，同一个标签可以同时被两个相邻城址选中，
于是出现 35px 内两个「蓟」这种重复。改成按「间隙从小到大」贪心配对，
每个标签、每个城址都只用一次。
"""
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
OX, OY = 512, 866


def clean(s):
    s = s.replace("|", "").replace(" ", "").replace("\u3000", "")
    return re.sub(r"[^\u4e00-\u9fff]", "", s)


def safe_load(p):
    try:
        t = Path(p).read_text(encoding="utf-8").strip()
        if not t or t == "null":
            return []
        d = json.loads(t)
        return d if isinstance(d, list) else [d]
    except Exception:
        return []


pool = []          # (text, x0,y0,x1,y1, src)


def add(t, x0, y0, x1, y1, src):
    c = clean(t)
    if c:
        pool.append((c, x0 + OX, y0 + OY, x1 + OX, y1 + OY, src))


for g in safe_load(ROOT / "tools" / "_ocr_names.json"):
    add(g["text"], g["x"], g["y"], g["x"] + g["w"], g["y"] + g["h"], "full")

mt = ROOT / "tools" / "ocr_tiles" / "meta.txt"
if mt.exists():
    m3 = {}
    for line in mt.read_text(encoding="utf-8").splitlines():
        nm, x0, y0, s = line.split()
        m3[nm.replace(".png", "")] = (int(x0), int(y0), float(s))
    for f in (ROOT / "tools" / "ocr_tiles").glob("t*.json"):
        x0, y0, s = m3.get(f.stem, (0, 0, 1))
        for g in safe_load(f):
            for l in (g.get("lines") or []):
                add(l["t"], l["x"] / s + x0, l["y"] / s + y0,
                    (l["x"] + l["w"]) / s + x0, (l["y"] + l["h"]) / s + y0, "t3")

for tag in ("p2", "p4"):
    base = ROOT / "tools" / "passes" / tag
    mp = base / "meta.json"
    if not mp.exists():
        continue
    meta = json.loads(mp.read_text(encoding="utf-8"))
    for g in safe_load(base / "result.json"):
        m = meta.get(g["id"])
        if not m:
            continue
        for l in (g.get("lines") or []):
            add(l["t"], l["x"] / m["scale"] + m["x0"], l["y"] / m["scale"] + m["y0"],
                (l["x"] + l["w"]) / m["scale"] + m["x0"],
                (l["y"] + l["h"]) / m["scale"] + m["y0"], tag)

nm = ROOT / "tools" / "node_crops" / "meta.json"
if nm.exists():
    nmd = json.loads(nm.read_text(encoding="utf-8"))
    for g in safe_load(ROOT / "tools" / "_ocr_nodes.json"):
        m = nmd.get(g["id"])
        if not m:
            continue
        for l in (g.get("lines") or []):
            add(l["t"], l["x"] / 3 + m["x0"], l["y"] / 3 + m["y0"],
                (l["x"] + l["w"]) / 3 + m["x0"], (l["y"] + l["h"]) / 3 + m["y0"], "node")

print("pool", len(pool))

rows = list(csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")))
for r in rows:
    r["x"] = float(r["x"]); r["y"] = float(r["y"]); r["name"] = ""

GAP_MIN, GAP_MAX, DY_TOL = 2, 50, 15
cands = []
for li, (t, x0, y0, x1, y1, src) in enumerate(pool):
    cy = (y0 + y1) / 2
    for ni, n in enumerate(rows):
        if abs(cy - n["y"]) > DY_TOL:
            continue
        gr = x0 - n["x"]
        gl = n["x"] - x1
        gap = None
        if GAP_MIN <= gr <= GAP_MAX:
            gap = gr
        elif GAP_MIN <= gl <= GAP_MAX:
            gap = gl
        if gap is not None:
            cands.append((gap, ni, li))
cands.sort()

used_n, used_l = set(), set()
for gap, ni, li in cands:
    if ni in used_n or li in used_l:
        continue
    used_n.add(ni); used_l.add(li)
    rows[ni]["name"] = pool[li][0]

named = sum(1 for r in rows if r["name"])
print(f"一对一分配完成：已命名 {named}/{len(rows)}")

with (ROOT / "data" / "map" / "nodes.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "name", "kind", "x", "y"])
    for r in rows:
        w.writerow([r["id"], r["name"], r["kind"], r["x"], r["y"]])
