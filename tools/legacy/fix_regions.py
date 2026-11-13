# -*- coding: utf-8 -*-
"""按用户勘误修正：
  1) 部族同名重复 → 去重（保留首个位置）
  2) 姑蔑：误判为部族，实为「都」——移入城邑
  3) 舒鲍：文字块切分漏掉，定位后补为部族
"""
import csv
import math
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
OX, OY = 512, 866

# ---------- 1) 解析用户输入 ----------
reg_raw = list(csv.DictReader((ROOT / "data" / "map" / "regions_filled.csv").open(encoding="utf-8-sig")))
parsed = []
for r in reg_raw:
    raw = (r.get("name") or "").strip()
    name, _, note = raw.partition("#")
    parsed.append({"id": r["id"], "name": name.strip(), "note": note.strip(),
                   "x": float(r["x"]), "y": float(r["y"])})

before = len(parsed)
seen = {}
uniq = []
for p in parsed:
    if not p["name"] or p["name"] == "（删）":
        continue
    if p["name"] in seen:
        seen[p["name"]]["dup_of"] = seen[p["name"]].get("dup_of", 0) + 1
        continue
    seen[p["name"]] = p
    uniq.append(p)
print(f"部族 {before} → 去重 {len(uniq)}")

# ---------- 2) 姑蔑 → 城邑 ----------
GUMIE = "姑蔑"
gumie = next((p for p in uniq if p["name"] == GUMIE), None)
if gumie:
    uniq = [p for p in uniq if p["name"] != GUMIE]

nodes = list(csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")))
if gumie:
    # 名称在文字块左上，符号在右侧约 +70px
    nx = round(gumie["x"] + 78, 1)
    ny = round(gumie["y"] + 12, 1)
    nodes.append({"id": "n1038", "name": GUMIE, "kind": "都", "x": nx, "y": ny})
    print(f"姑蔑 → 城邑 n1038 @ ({nx},{ny})")

# ---------- 3) 补 舒鲍 ----------
alpha = np.asarray(Image.open(ROOT / "assets" / "source" / "城池名称.png").convert("RGBA"))[:, :, 3] > 0
H, W = alpha.shape
shu = next((p for p in uniq if p["name"] == "舒龚"), None)
if shu:
    ex = shu["x"] - OX - 132      # 依据放大图估计：舒鲍在舒龚左侧约 132px、上 42px
    ey = shu["y"] - OY - 42
    x0, y0 = int(ex - 110), int(ey - 55)
    x1, y1 = int(ex + 110), int(ey + 55)
    sub = alpha[max(0, y0):y1, max(0, x0):x1]
    ys, xs = np.where(sub)
    if len(xs):
        bx0 = max(0, x0) + xs.min(); bx1 = max(0, x0) + xs.max()
        by0 = max(0, y0) + ys.min(); by1 = max(0, y0) + ys.max()
        cx, cy = (bx0 + bx1) / 2 + OX, (by0 + by1) / 2 + OY
        uniq.append({"id": "rg200", "name": "舒鲍", "note": "手工补充（切分漏掉）",
                     "x": cx, "y": cy})
        print(f"舒鲍 → 部族 rg200 @ ({cx:.0f},{cy:.0f})  墨迹px={int(sub.sum())}")
    else:
        print("舒鲍定位失败：该区域无墨迹")

# ---------- 写回 ----------
with (ROOT / "data" / "map" / "nodes.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "name", "kind", "x", "y"])
    for n in nodes:
        w.writerow([n["id"], n["name"], n["kind"], n["x"], n["y"]])

with (ROOT / "data" / "map" / "regions.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "name", "x", "y", "note"])
    for p in sorted(uniq, key=lambda p: (p["y"], p["x"])):
        w.writerow([p["id"], p["name"], round(p["x"], 1), round(p["y"], 1), p["note"]])

print(f"城邑 {len(nodes)}  部族 {len(uniq)}")
