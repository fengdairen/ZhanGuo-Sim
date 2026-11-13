# -*- coding: utf-8 -*-
"""最后一轮找补：对剩余待处理城址，做「3x放大 + 二值化」的全图裁剪。"""
import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
OUT = ROOT / "tools" / "todo_crops2"
OUT.mkdir(exist_ok=True)
for f in OUT.glob("*.png"):
    f.unlink()

SCALE = 3
L, R, U, D = 190, 230, 60, 60

im = Image.open(ROOT / "assets" / "source" / "ditu.png").convert("RGB")
W, H = im.size
rows = list(csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")))
todo = [r for r in rows if (not r["name"]) or len(r["name"]) >= 3]
print("todo", len(todo))

meta = {}
for r in todo:
    cx, cy = float(r["x"]), float(r["y"])
    x0 = int(max(0, cx - L)); x1 = int(min(W, cx + R))
    y0 = int(max(0, cy - U)); y1 = int(min(H, cy + D))
    t = im.crop((x0, y0, x1, y1))
    t = t.resize((t.width * SCALE, t.height * SCALE), Image.LANCZOS)
    a = np.asarray(t).astype(np.int16)
    lum = a[:, :, 0] * 0.299 + a[:, :, 1] * 0.587 + a[:, :, 2] * 0.114
    # 只保留"文字级深色"，地形与浅色阴影一律变白
    b = (lum < 125)
    out = np.where(b, 0, 255).astype(np.uint8)
    img = Image.fromarray(out).convert("RGB")
    img.save(OUT / f"{r['id']}.png")
    meta[r["id"]] = {"mx": (cx - x0) * SCALE, "my": (cy - y0) * SCALE}

(OUT / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
print("crops", len(meta))
