# -*- coding: utf-8 -*-
"""对未命名的节点，生成「留白 + 4x 放大」的裁剪块，专治单字地名。"""
import csv
import json
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
NAME_OFF_X, NAME_OFF_Y = 512, 866
OUT = ROOT / "tools" / "node_crops2"
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)

SCALE = 4
PAD = 24
L, R, U, D = 170, 230, 80, 80

im = Image.open(ROOT / "tools" / "_names_white.png").convert("RGB")
W, H = im.size
rows = list(csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")))
todo = [r for r in rows if not r["name"]]
print("empty nodes", len(todo))

meta = {}
for r in todo:
    cx = float(r["x"]) - NAME_OFF_X
    cy = float(r["y"]) - NAME_OFF_Y
    x0 = int(max(0, cx - L)); x1 = int(min(W, cx + R))
    y0 = int(max(0, cy - U)); y1 = int(min(H, cy + D))
    if x1 <= x0 or y1 <= y0:
        continue
    t = im.crop((x0, y0, x1, y1))
    canvas = Image.new("RGB", (t.width + PAD * 2, t.height + PAD * 2), (255, 255, 255))
    canvas.paste(t, (PAD, PAD))
    canvas = canvas.resize((canvas.width * SCALE, canvas.height * SCALE), Image.LANCZOS)
    canvas.save(OUT / f"{r['id']}.png")
    meta[r["id"]] = {"mx": round((cx - x0 + PAD) * SCALE, 1), "my": round((cy - y0 + PAD) * SCALE, 1)}

(OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
print("crops", len(meta))
