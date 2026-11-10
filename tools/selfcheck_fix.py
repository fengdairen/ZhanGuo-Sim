# -*- coding: utf-8 -*-
"""自检修复：
  1) 80px 内同名的城址，只保留一个，其余清空（标签被重复分配）；
  2) 以「水」结尾的视为河流名，清空；
  3) 以「回/囗/口」等方框字符残留的再洗一遍（保险）。
清空的都会进入待办清单。
"""
import csv
import json
import math
import re
from pathlib import Path

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
BOX = "口囗回〇ロㅁ"

rows = list(csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")))
for r in rows:
    r["x"] = float(r["x"]); r["y"] = float(r["y"])

cleared_dup, cleared_river, cleared_box = [], [], []

# 1) 重名
groups = {}
for r in rows:
    if r["name"]:
        groups.setdefault(r["name"], []).append(r)

for name, g in groups.items():
    if len(g) < 2:
        continue
    for i, a in enumerate(g):
        for b in g[i + 1:]:
            d = math.hypot(a["x"] - b["x"], a["y"] - b["y"])
            if d < 80:
                # 保留靠前的，清掉后者
                loser = b if a["name"] else a
                if loser["name"]:
                    cleared_dup.append((loser["id"], name, round(d)))
                    loser["name"] = ""

# 2) 河名
for r in rows:
    if r["name"].endswith("水"):
        cleared_river.append((r["id"], r["name"]))
        r["name"] = ""

# 3) 方框残留
for r in rows:
    if r["name"] and any(ch in r["name"] for ch in BOX):
        segs = [s for s in re.split(f"[{BOX}]+", r["name"]) if s]
        r["name"] = segs[0] if segs else ""
        if not r["name"]:
            cleared_box.append(r["id"])

for r in rows:
    r.setdefault("name", "")

with (ROOT / "data" / "map" / "nodes.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "name", "kind", "x", "y"])
    for r in rows:
        w.writerow([r["id"], r["name"], r["kind"], r["x"], r["y"]])

named = sum(1 for r in rows if r["name"])
print(f"清重名 {len(cleared_dup)}  清河名 {len(cleared_river)}  清方框 {len(cleared_box)}")
print(f"已命名 {named}/{len(rows)}")
(ROOT / "tools" / "_cleared.json").write_text(
    json.dumps({"dup": cleared_dup, "river": cleared_river}, ensure_ascii=False), encoding="utf-8")
