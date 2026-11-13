# -*- coding: utf-8 -*-
"""把勘误表里的 correction 列写回 nodes.csv。
用法：python tools/apply_corrections.py [review.csv路径]
规则：
  correction 为空    → 不改
  correction = "-"   → 清空该名（标记为未识别）
  其它               → 用该值覆盖
"""
import csv
import sys
from pathlib import Path

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
review_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "map" / "review.csv"
nodes_path = ROOT / "data" / "map" / "nodes.csv"

fix = {}
for r in csv.DictReader(review_path.open(encoding="utf-8-sig")):
    c = (r.get("correction") or "").strip()
    if not c:
        continue
    fix[r["id"]] = "" if c in ("-", "—", "空") else c

nodes = list(csv.DictReader(nodes_path.open(encoding="utf-8-sig")))
changed = 0
for n in nodes:
    if n["id"] in fix:
        if n["name"] != fix[n["id"]]:
            changed += 1
        n["name"] = fix[n["id"]]

with nodes_path.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "name", "kind", "x", "y"])
    for n in nodes:
        w.writerow([n["id"], n["name"], n["kind"], n["x"], n["y"]])

named = sum(1 for n in nodes if n["name"])
print(f"corrections read={len(fix)} applied={changed}")
print(f"named {named}/{len(nodes)}")
