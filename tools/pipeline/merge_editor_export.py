# -*- coding: utf-8 -*-
"""把地图编辑器导出的 map_edited.csv 合并回 nodes.csv / regions.csv。"""
import csv
from pathlib import Path

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
SRC = ROOT / "data" / "map" / "map_edited.csv"

ed = list(csv.DictReader(SRC.open(encoding="utf-8-sig")))
nodes = list(csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")))
regions = list(csv.DictReader((ROOT / "data" / "map" / "regions.csv").open(encoding="utf-8-sig")))

cur = {}
for r in nodes:
    cur[r["id"]] = {"id": r["id"], "name": r["name"], "kind": r["kind"],
                    "x": float(r["x"]), "y": float(r["y"]), "pop": float(r["pop"]),
                    "source": r.get("source", ""), "note": ""}
for r in regions:
    cur[r["id"]] = {"id": r["id"], "name": r["name"], "kind": "部族",
                    "x": float(r["x"]), "y": float(r["y"]), "pop": float(r["pop"]),
                    "source": r.get("source", ""), "note": r.get("note", "")}

added, deleted, changed = [], [], []
out = {}
for e in ed:
    i = e["id"]
    rec = {"id": i, "name": e["name"], "kind": e["kind"],
           "x": float(e["x"]), "y": float(e["y"]), "pop": float(e["pop"])}
    if e.get("deleted") == "1":
        if i in cur:
            deleted.append((i, cur[i]["name"]))
        continue
    if i not in cur:
        rec["source"] = "编辑器新增"
        added.append(rec)
        out[i] = rec
        continue
    c = cur[i]
    diff = []
    if rec["name"] != c["name"]:
        diff.append(f'名:{c["name"]}→{rec["name"]}')
    if rec["kind"] != c["kind"]:
        diff.append(f'类:{c["kind"]}→{rec["kind"]}')
    if abs(rec["pop"] - c["pop"]) > 1e-6:
        diff.append(f'人:{c["pop"]}→{rec["pop"]}')
    if abs(rec["x"] - c["x"]) > 0.5 or abs(rec["y"] - c["y"]) > 0.5:
        diff.append(f'位:({c["x"]:.0f},{c["y"]:.0f})→({rec["x"]:.0f},{rec["y"]:.0f})')
    if diff:
        changed.append((i, c["name"], diff))
    rec["source"] = c["source"]
    rec["note"] = c["note"]
    out[i] = rec

# 编辑器里没出现的旧条目：保留（避免误删）
for i, c in cur.items():
    if i not in out:
        out[i] = c

# 写回
nrow = [r for r in out.values() if r["kind"] != "部族"]
rrow = [r for r in out.values() if r["kind"] == "部族"]
nrow.sort(key=lambda r: r["id"])
rrow.sort(key=lambda r: r["id"])

with (ROOT / "data" / "map" / "nodes.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "name", "kind", "x", "y", "pop", "source"])
    for r in nrow:
        w.writerow([r["id"], r["name"], r["kind"], round(r["x"], 1), round(r["y"], 1),
                    round(r["pop"], 2), r.get("source", "")])

with (ROOT / "data" / "map" / "regions.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "name", "x", "y", "pop", "source", "note"])
    for r in rrow:
        w.writerow([r["id"], r["name"], round(r["x"], 1), round(r["y"], 1),
                    round(r["pop"], 2), r.get("source", ""), r.get("note", "")])

L = [f"编辑器 {len(ed)} 条 / 原数据 {len(cur)} 条",
     f"新增 {len(added)}　删除 {len(deleted)}　改动 {len(changed)}",
     f"结果：城邑 {len(nrow)}，部族 {len(rrow)}", ""]
for r in added:
    L.append(f'  + {r["id"]} {r["name"]} {r["kind"]} ({r["x"]:.0f},{r["y"]:.0f}) pop={r["pop"]}')
for i, n in deleted:
    L.append(f'  - {i} {n}')
for i, n, d in changed[:60]:
    L.append(f'  ~ {i} {n}: ' + "；".join(d))
(ROOT / "tools" / "_edit_diff.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))
