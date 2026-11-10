# -*- coding: utf-8 -*-
"""把矢量化结果用 PIL 画成预览图，用于肉眼检查质量（不依赖浏览器）。

输出 tools/_vec_preview.png
"""
import csv
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
VEC = ROOT / "data" / "map" / "vector"
OUT = ROOT / "tools" / "_vec_preview.png"

SCALE = 0.16
W, H = 9101, 8509
CW, CH = int(W * SCALE), int(H * SCALE)

PAPER = (242, 231, 203)
SEA = (185, 199, 204)
SEA_EDGE = (140, 160, 170)
LAKE = (127, 176, 201)
RIVER = (62, 124, 166)
BORDER = (168, 112, 60)
COAST = (107, 123, 140)
CITY = (59, 42, 26)


def L(path):
    return json.loads((VEC / path).read_text(encoding="utf-8"))


def sc(pts):
    return [(p[0] * SCALE, p[1] * SCALE) for p in pts]


img = Image.new("RGB", (CW, CH), PAPER)
d = ImageDraw.Draw(img)

coast = L("coast.json")
for poly in coast["sea"]:
    d.polygon(sc(poly), fill=SEA)

for line in coast["lines"]:
    d.line(sc(line), fill=COAST, width=1)

for poly in L("lakes.json"):
    d.polygon(sc(poly), fill=LAKE)
    d.line(sc(poly + poly[:1]), fill=RIVER, width=1)

rw = VEC / "rivers_w.json"
if rw.exists():
    for e in json.loads(rw.read_text(encoding="utf-8")):
        w = max(1, round(e[0] * SCALE * 1.6))
        pts = [(e[i] * SCALE, e[i + 1] * SCALE) for i in range(1, len(e), 2)]
        d.line(pts, fill=RIVER, width=w)
else:
    for line in L("rivers.json"):
        d.line(sc(line), fill=RIVER, width=1)

for line in L("borders.json"):
    d.line(sc(line), fill=BORDER, width=1)

rows = list(csv.DictReader(open(ROOT / "data" / "map" / "nodes.csv", encoding="utf-8-sig")))
for r in rows:
    x, y = float(r["x"]) * SCALE, float(r["y"]) * SCALE
    k = r["kind"]
    rad = {"都": 3, "城": 2, "邑": 1}[k]
    d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=CITY)

for r in csv.DictReader(open(ROOT / "data" / "map" / "regions.csv", encoding="utf-8-sig")):
    x, y = float(r["x"]) * SCALE, float(r["y"]) * SCALE
    d.ellipse([x - 2, y - 2, x + 2, y + 2], outline=(150, 60, 40), width=1)

img.save(OUT)
print(f"saved {OUT} {img.size}")
