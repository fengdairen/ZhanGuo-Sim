# -*- coding: utf-8 -*-
"""给每个城邑/部族填人口（v2）。

修正 v1 的错误：
  - 地图上有重名城（如两个「平陆」），锚点会选错 → 改为取「离本国中心最近」的候选
  - 分摊时无半径限制，会把人口撒到千里之外 → 加 420px 上限
  - 国中心：先用该国有核心城的群定出锚点，取其重心

规则仍是：都30万 / 城8万 / 邑2万；有真实人群数据的按该群权重缩放后分摊。
"""
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
W = {"都": 30.0, "城": 8.0, "邑": 2.0}
TRIBE_POP = 10.0
RADIUS = 420

nodes = list(csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")))
for n in nodes:
    n["x"] = float(n["x"]); n["y"] = float(n["y"])
    n["pop"] = 0.0; n["source"] = ""

state = json.loads((ROOT / "data" / "state.json").read_text(encoding="utf-8"))
SUF = ("都人", "都", "邑", "城", "人", "地", "氏", "领地", "地区", "地带", "土地", "飞地")


def variants(name):
    out = {name}
    for s in SUF:
        if name.endswith(s) and len(name) > len(s):
            out.add(name[: -len(s)])
    for s in SUF:
        out.add(name + s)
    return out


idx = defaultdict(list)
for n in nodes:
    if n["name"]:
        for v in variants(n["name"]):
            idx[v].append(n)

# ---- 各国「中心」：优先用有核心城的人群 ----
seat = {}
for nat in state["nations"]:
    pts = []
    for g in nat["populationGroups"]:
        for key in ((g.get("coreCity") or ""), g["name"]):
            for k in variants(key):
                for n in idx.get(k, []):
                    pts.append(n)
            if pts:
                break
        if len(pts) >= 2:
            break
    if pts:
        seat[nat["name"]] = (sum(p["x"] for p in pts) / len(pts),
                             sum(p["y"] for p in pts) / len(pts))

used = set()


def pick_anchor(nat_name, keys):
    best, bd = None, 1e18
    sx, sy = seat.get(nat_name, (None, None))
    for k in keys:
        for n in idx.get(k, []):
            if id(n) in used:
                continue
            if sx is None:
                return n
            d = (n["x"] - sx) ** 2 + (n["y"] - sy) ** 2
            if d < bd:
                bd, best = d, n
    return best


groups = []
for nat in state["nations"]:
    for g in nat["populationGroups"]:
        if g["du"] + g["cheng"] + g["yi"] <= 0:
            continue
        groups.append({"nation": nat["name"], "g": g})

matched = 0
for item in groups:
    nat_name, g = item["nation"], item["g"]
    keys = []
    if g.get("coreCity"):
        keys.append(g["coreCity"])
    keys.append(g["name"])
    kk = []
    for k in keys:
        kk.extend(variants(k))
    anchor = pick_anchor(nat_name, kk)
    if not anchor:
        continue
    matched += 1
    used.add(id(anchor))

    wsum = g["du"] * W["都"] + g["cheng"] * W["城"] + g["yi"] * W["邑"]
    scale = 1.0
    if g.get("population"):
        scale = (g["population"] / 10.0) / wsum     # 千人 → 万人

    if g["du"] > 0:
        anchor["pop"] = W["都"] * scale
        anchor["source"] = f"{nat_name}·{g['name']}(都)"

    def take(kind, count, label):
        if count <= 0:
            return
        cands = []
        for n in nodes:
            if n["kind"] != kind or id(n) in used:
                continue
            d = math.hypot(n["x"] - anchor["x"], n["y"] - anchor["y"])
            if d <= RADIUS:
                cands.append((d, n))
        cands.sort(key=lambda t: t[0])
        for d, n in cands[:int(count)]:
            used.add(id(n))
            n["pop"] = W[kind] * scale
            n["source"] = f"{nat_name}·{g['name']}({label})"

    take("城", g["cheng"], "城")
    take("邑", g["yi"], "邑")
    take("都", max(0, g["du"] - 1), "都")

print(f"人群 {len(groups)}，锚点 {matched}")

for n in nodes:
    if n["pop"] <= 0:
        n["pop"] = W.get(n["kind"], 2.0)
        n["source"] = "默认值"

regions = list(csv.DictReader((ROOT / "data" / "map" / "regions.csv").open(encoding="utf-8-sig")))
for r in regions:
    r["pop"] = TRIBE_POP
    r["source"] = "部族假设值"

with (ROOT / "data" / "map" / "nodes.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "name", "kind", "x", "y", "pop", "source"])
    for n in nodes:
        w.writerow([n["id"], n["name"], n["kind"], round(n["x"], 1), round(n["y"], 1),
                    round(n["pop"], 2), n["source"]])

with (ROOT / "data" / "map" / "regions.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "name", "x", "y", "pop", "source", "note"])
    for r in regions:
        w.writerow([r["id"], r["name"], r["x"], r["y"], r["pop"], r["source"], r.get("note", "")])

ct = sum(n["pop"] for n in nodes)
tt = sum(r["pop"] for r in regions)
real = sum(n["pop"] for n in nodes if n["source"] != "默认值")
L = [f"城邑 {len(nodes)} 座：{ct:.0f} 万",
     f"部族 {len(regions)} 个：{tt:.0f} 万",
     f"合计 {ct + tt:.0f} 万",
     f"其中来自经济表：{real:.0f} 万（{sum(1 for n in nodes if n['source'] != '默认值')} 座城）",
     f"默认值：{ct - real:.0f} 万（{sum(1 for n in nodes if n['source'] == '默认值')} 座城）"]
(ROOT / "tools" / "_census_pop2.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))
