# -*- coding: utf-8 -*-
"""对仍未命名的城址，改从「全图」重新裁剪 OCR（部分地名不在名称层里）。"""
import csv
import json
from pathlib import Path

from PIL import Image

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
OUT = ROOT / "tools" / "todo_crops"
OUT.mkdir(exist_ok=True)
for f in OUT.glob("*.png"):
    f.unlink()

SCALE = 2
L, R, U, D = 170, 210, 55, 55

im = Image.open(ROOT / "ditu.png").convert("RGB")
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
    t.save(OUT / f"{r['id']}.png")
    meta[r["id"]] = {"mx": (cx - x0) * SCALE, "my": (cy - y0) * SCALE}

(OUT / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
print("crops", len(meta))
