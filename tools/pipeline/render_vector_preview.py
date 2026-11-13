# -*- coding: utf-8 -*-
"""用 PIL 复刻 HTML 的绘制样式，生成预览图（用于不开浏览器时检查视觉）。

输出 tools/_vec_preview.png
"""
import csv
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent.parent
VEC = ROOT / "data" / "map" / "vector"
OUT = ROOT / "tools" / "_vec_preview.png"

SCALE = 0.155
W, H = 9101, 8509
CW, CH = int(W * SCALE), int(H * SCALE)

PAPER = (242, 231, 203)
SEA = (184, 198, 204)
SEA_EDGE = (140, 160, 170)
LAKE = (127, 176, 201)
RIVER = (62, 124, 166)
CASE = (150, 122, 88)
COAST = (109, 127, 140)
DU = (139, 46, 30)
CHENG = (107, 74, 47)
YI = (122, 98, 72)


def L(n):
    return json.loads((VEC / n).read_text(encoding="utf-8"))


def sc(pts):
    return [(p[0] * SCALE, p[1] * SCALE) for p in pts]


VECD = VEC
cd_path = VECD / "coast_drawn.json"
drawn = json.loads(cd_path.read_text(encoding="utf-8")) if cd_path.exists() else []

img = Image.new("RGB", (CW, CH), PAPER)
d = ImageDraw.Draw(img)

coast = L("coast.json")
for poly in coast["sea"]:
    d.polygon(sc(poly), fill=SEA)
for line in coast["lines"]:
    d.line(sc(line), fill=(200, 205, 205), width=1)

# 描迹海岸线 / 岛
lk_path = VECD / "lakes_drawn.json"
lakes_d = json.loads(lk_path.read_text(encoding="utf-8")) if lk_path.exists() else []
for l in lakes_d:
    pts = [(l["pts"][i], l["pts"][i+1]) for i in range(0, len(l["pts"]), 2)]
    if len(pts) >= 3:
        d.polygon(sc(pts), fill=(150, 190, 210), outline=(62, 124, 166))

for c in drawn:
    pts = [(c["pts"][i], c["pts"][i+1]) for i in range(0, len(c["pts"]), 2)]
    if c.get("closed"):
        d.polygon(sc(pts), fill=PAPER, outline=(77, 102, 117))
    else:
        d.line(sc(pts), fill=(77, 102, 117), width=2)

for poly in L("lakes.json"):
    d.polygon(sc(poly), fill=LAKE)
    d.line(sc(poly + poly[:1]), fill=RIVER, width=1)

rivers = L("rivers_w.json")
# 描边层
for e in rivers:
    w = max(1, round((e[0] + 2.0) * SCALE))
    pts = [(e[i] * SCALE, e[i + 1] * SCALE) for i in range(1, len(e), 2)]
    d.line(pts, fill=CASE, width=w)
for e in rivers:
    w = max(1, round(e[0] * SCALE))
    pts = [(e[i] * SCALE, e[i + 1] * SCALE) for i in range(1, len(e), 2)]
    d.line(pts, fill=RIVER, width=w)

for r in csv.DictReader(open(ROOT / "data" / "map" / "nodes.csv", encoding="utf-8-sig")):
    x, y = float(r["x"]) * SCALE, float(r["y"]) * SCALE
    k = r["kind"]
    if k == "都":
        d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=DU)
        d.ellipse([x - 5, y - 5, x + 5, y + 5], outline=DU, width=1)
    elif k == "城":
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=CHENG)
    else:
        d.ellipse([x - 1, y - 1, x + 1, y + 1], fill=YI)

img.save(OUT)
print(f"saved {OUT} {img.size}")
