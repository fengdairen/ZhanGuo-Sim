# -*- coding: utf-8 -*-
"""建立人口表：城市 × 人群 × 数量。

产出：
  data/map/groups.csv      人群库（名称 + 简介）
  data/map/populations.csv 人口条目（城市、人群、万数、备注）
迁移规则：每个城邑现有的总人口，全部记为「无认同人口」一条。
"""
import csv
from pathlib import Path

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")

BASE = "无认同人口"
BASE_NOTE = "无确切的民族或国家认同，只认为自己是种地的野人"

nodes = list(csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")))
regions = list(csv.DictReader((ROOT / "data" / "map" / "regions.csv").open(encoding="utf-8-sig")))

groups = [{"name": BASE, "note": BASE_NOTE}]
seen = {BASE}
rows = []
i = 0
for n in nodes:
    pop = float(n["pop"])
    if pop <= 0:
        continue
    i += 1
    rows.append({"id": f"p{i:05d}", "city_id": n["id"], "group": BASE,
                 "amount": round(pop, 2), "note": ""})
for r in regions:
    pop = float(r["pop"])
    if pop <= 0:
        continue
    i += 1
    rows.append({"id": f"p{i:05d}", "city_id": r["id"], "group": BASE,
                 "amount": round(pop, 2), "note": "部族"})

with (ROOT / "data" / "map" / "groups.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["name", "note"])
    for g in groups:
        w.writerow([g["name"], g["note"]])

with (ROOT / "data" / "map" / "populations.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "city_id", "group", "amount", "note"])
    for r in rows:
        w.writerow([r["id"], r["city_id"], r["group"], r["amount"], r["note"]])

total = sum(r["amount"] for r in rows)
print(f"人群 {len(groups)} 个；人口条目 {len(rows)} 条；合计 {total:.1f} 万")
