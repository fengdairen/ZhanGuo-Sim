# -*- coding: utf-8 -*-
"""按每个城址裁剪地名区域（记录标记在裁剪块内的真实位置，处理边缘裁切）。"""
import csv
import json
from pathlib import Path

from PIL import Image

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
NAME_OFF_X, NAME_OFF_Y = 512, 866
OUT = ROOT / "tools" / "node_crops"
OUT.mkdir(exist_ok=True)
SCALE = 3
BOX_L, BOX_R, BOX_U, BOX_D = 150, 220, 70, 70

im = Image.open(ROOT / "tools" / "_names_white.png").convert("RGB")
W, H = im.size

rows = list(csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")))
meta = {}
for r in rows:
    cx = float(r["x"]) - NAME_OFF_X
    cy = float(r["y"]) - NAME_OFF_Y
    x0 = int(max(0, cx - BOX_L)); x1 = int(min(W, cx + BOX_R))
    y0 = int(max(0, cy - BOX_U)); y1 = int(min(H, cy + BOX_D))
    if x1 <= x0 or y1 <= y0:
        continue
    t = im.crop((x0, y0, x1, y1))
    t = t.resize((t.width * SCALE, t.height * SCALE), Image.LANCZOS)
    t.save(OUT / f"{r['id']}.png")
    meta[r["id"]] = {
        "mx": round((cx - x0) * SCALE, 1),
        "my": round((cy - y0) * SCALE, 1),
        "x0": x0, "y0": y0,
        "w": t.width, "h": t.height,
    }

(OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
print("crops", len(meta), "->", OUT)
