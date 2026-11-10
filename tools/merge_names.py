# -*- coding: utf-8 -*-
"""把逐城 OCR 结果合并回 nodes.csv。
规则：取离标记中心最近的一行文字（标记在裁剪块内的固定位置），并做清洗。
"""
import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
MAX_DIST = 150

meta = json.loads((ROOT / "tools" / "node_crops" / "meta.json").read_text(encoding="utf-8"))

nodes = list(csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")))
ocr = json.loads((ROOT / "tools" / "_ocr_nodes.json").read_text(encoding="utf-8"))
if isinstance(ocr, dict):
    ocr = [ocr]
by_id = {o["id"]: o for o in ocr}


def clean(s: str) -> str:
    s = s.replace("|", "").replace(" ", "").replace("\u3000", "")
    s = re.sub(r"[^\u4e00-\u9fff]", "", s)
    return s


def rect_dist(l, px, py):
    x, y, w, h = l["x"], l["y"], l["w"], l["h"]
    dx = max(x - px, 0, px - (x + w))
    dy = max(y - py, 0, py - (y + h))
    return (dx * dx + dy * dy) ** 0.5


named, empty, ambiguous = 0, 0, 0
report = []
for n in nodes:
    o = by_id.get(n["id"], {})
    lines = o.get("lines", []) or []
    m = meta.get(n["id"])
    if not m:
        n["name"] = ""
        empty += 1
        continue
    mk = (m["mx"], m["my"])
    best, bestd, second = None, 1e9, 1e9
    for l in lines:
        d = rect_dist(l, *mk)
        if d < bestd:
            second, bestd, best = bestd, d, l
        elif d < second:
            second = d
    if best is None or bestd > MAX_DIST or not clean(best["t"]):
        n["name"] = ""
        empty += 1
        continue
    if second - bestd < 12:          # 两个候选几乎等距 → 不确定
        ambiguous += 1
    n["name"] = clean(best["t"])
    named += 1
    report.append((n["id"], n["kind"], n["name"], round(bestd, 1)))

print(f"nodes={len(nodes)} named={named} empty={empty} ambiguous={ambiguous}")

# 名字长度分布与重复
lens = Counter(len(n["name"]) for n in nodes)
print("名字长度分布:", sorted(lens.items()))
dups = [(k, v) for k, v in Counter(n["name"] for n in nodes if n["name"]).items() if v > 1]
print("重名数量:", len(dups), " 例:", dups[:12])

out = ROOT / "data" / "map" / "nodes.csv"
with out.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "name", "kind", "x", "y"])
    for n in nodes:
        w.writerow([n["id"], n["name"], n["kind"], n["x"], n["y"]])
print("written", out)

(ROOT / "tools" / "_merge_report.txt").write_text(
    "\n".join(f"{i}\t{k}\t{t}\t{d}" for i, k, t, d in report[:400]), encoding="utf-8")
