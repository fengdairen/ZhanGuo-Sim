# -*- coding: utf-8 -*-
"""合并二值化 3x 重识别结果（只填空缺，不覆盖已有）。"""
import csv
import json
import re
from pathlib import Path

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
DIR = ROOT / "tools" / "todo_crops2"


def clean(s):
    s = s.replace("|", "").replace(" ", "").replace("\u3000", "")
    return re.sub(r"[^\u4e00-\u9fff]", "", s)


meta = json.loads((DIR / "meta.json").read_text(encoding="utf-8"))
res = json.loads((ROOT / "tools" / "_ocr_todo2.json").read_text(encoding="utf-8"))
if isinstance(res, dict):
    res = [res]
by = {o["id"]: o for o in res}

rows = list(csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")))
filled = 0
for r in rows:
    if r["name"]:
        continue
    m = meta.get(r["id"])
    o = by.get(r["id"])
    if not m or not o or not o.get("lines"):
        continue
    best, bd = None, 1e9
    for l in o["lines"]:
        t = clean(l["t"])
        if not (1 <= len(t) <= 4):
            continue
        x, y, w, h = l["x"], l["y"], l["w"], l["h"]
        dx = max(x - m["mx"], 0, m["mx"] - (x + w))
        dy = max(y - m["my"], 0, m["my"] - (y + h))
        d = (dx * dx + dy * dy) ** 0.5
        if d < bd:
            bd, best = d, t
    if best and bd <= 75:
        r["name"] = best
        filled += 1

with (ROOT / "data" / "map" / "nodes.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "name", "kind", "x", "y"])
    for r in rows:
        w.writerow([r["id"], r["name"], r["kind"], r["x"], r["y"]])

named = sum(1 for r in rows if r["name"])
short = sum(1 for r in rows if r["name"] and len(r["name"]) <= 2)
print(f"本轮补 {filled}  已命名 {named}/{len(rows)}  其中短名 {short}")
