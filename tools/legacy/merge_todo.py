# -*- coding: utf-8 -*-
"""把「全图重识别」的结果合并进 nodes.csv。
关键：全图上河流名是蓝色，必须过滤掉，否则会把水名当城名。
"""
import csv
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
SCALE = 2
DIR = ROOT / "tools" / "todo_crops"


def clean(s):
    s = s.replace("|", "").replace(" ", "").replace("\u3000", "")
    return re.sub(r"[^\u4e00-\u9fff]", "", s)


meta = json.loads((DIR / "meta.json").read_text(encoding="utf-8"))
res = json.loads((ROOT / "tools" / "_ocr_todo.json").read_text(encoding="utf-8"))
if isinstance(res, dict):
    res = [res]
by = {o["id"]: o for o in res}

rows = list(csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")))
fixed = 0
rejected_blue = 0

for r in rows:
    if r["name"] and len(r["name"]) < 3:
        continue
    m = meta.get(r["id"])
    o = by.get(r["id"])
    if not m or not o or not o.get("lines"):
        continue

    img = Image.open(DIR / f'{r["id"]}.png').convert("RGB")
    a = np.asarray(img).astype(np.int16)

    best, bestd = None, 1e9
    for l in o["lines"]:
        t = clean(l["t"])
        if not t:
            continue
        x, y, w, h = l["x"], l["y"], l["w"], l["h"]
        dx = max(x - m["mx"], 0, m["mx"] - (x + w))
        dy = max(y - m["my"], 0, m["my"] - (y + h))
        d = (dx * dx + dy * dy) ** 0.5
        if d > 90:
            continue

        # 颜色判断：蓝色 = 水名
        sub = a[int(y):int(y + h) + 1, int(x):int(x + w) + 1]
        if sub.size == 0:
            continue
        lum = sub[:, :, 0] * 0.299 + sub[:, :, 1] * 0.587 + sub[:, :, 2] * 0.114
        dark = sub[lum < 150]
        if len(dark) < 10:
            continue
        rr, gg, bb = dark[:, 0].mean(), dark[:, 1].mean(), dark[:, 2].mean()
        if bb > rr + 25:            # 偏蓝 → 水名
            rejected_blue += 1
            continue

        if d < bestd:
            bestd, best = d, t

    if best and bestd <= 90:
        r["name"] = best
        fixed += 1

# 多于 6 字的当作噪声，清掉
for r in rows:
    if len(r["name"]) > 6:
        r["name"] = ""

with (ROOT / "data" / "map" / "nodes.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "name", "kind", "x", "y"])
    for r in rows:
        w.writerow([r["id"], r["name"], r["kind"], r["x"], r["y"]])

named = sum(1 for r in rows if r["name"])
print(f"新补 {fixed}  蓝色水名过滤 {rejected_blue}  已命名 {named}/{len(rows)}")
