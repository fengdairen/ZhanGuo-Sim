# -*- coding: utf-8 -*-
"""尺度实验：把未识别节点的标签单独抠出，按 3/6/8 倍放大，看哪档能被 OCR 吃下。"""
import csv
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
OX, OY = 512, 866
OUT = ROOT / "tools" / "scale_test"
OUT.mkdir(exist_ok=True)

names_img = Image.open(ROOT / "assets" / "source" / "城池名称.png").convert("RGBA")
alpha = np.asarray(names_img)[:, :, 3] > 0
H, W = alpha.shape
# 关键：必须用「白底合成图」取像素，直接 RGBA→RGB 会把透明区变成黑色
rgb = Image.open(ROOT / "tools" / "_names_white.png").convert("RGB")

rows = list(csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")))
empty = [r for r in rows if not r["name"]]


def ink_bbox(x, y):
    best = None
    for (x0, x1) in ((x + 8, x + 130), (x - 130, x - 8)):
        x0c, x1c = max(0, x0), min(W, x1)
        y0c, y1c = max(0, y - 18), min(H, y + 18)
        if x1c <= x0c or y1c <= y0c:
            continue
        sub = alpha[y0c:y1c, x0c:x1c]
        if sub.sum() < 15:
            continue
        ys, xs = np.where(sub)
        bb = (x0c + xs.min(), y0c + ys.min(), x0c + xs.max(), y0c + ys.max())
        area = (bb[2] - bb[0]) * (bb[3] - bb[1])
        if best is None or area < best[0]:
            best = (area, bb)
    return best[1] if best else None


picked = []
for r in empty:
    x, y = int(float(r["x"])) - OX, int(float(r["y"])) - OY
    bb = ink_bbox(x, y)
    if bb:
        picked.append((r["id"], bb))
    if len(picked) >= 6:
        break

for nid, (x0, y0, x1, y1) in picked:
    pad = 8
    box = (max(0, x0 - pad), max(0, y0 - pad), min(W, x1 + pad), min(H, y1 + pad))
    t = rgb.crop(box)
    for s in (3, 6, 8):
        canvas = Image.new("RGB", (t.width + 20, t.height + 20), (255, 255, 255))
        canvas.paste(t, (10, 10))
        canvas = canvas.resize((canvas.width * s, canvas.height * s), Image.LANCZOS)
        canvas.save(OUT / f"{nid}_s{s}.png")
    print(nid, "bbox w,h =", x1 - x0 + 1, y1 - y0 + 1)
