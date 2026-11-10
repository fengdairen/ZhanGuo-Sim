# -*- coding: utf-8 -*-
"""多轮 OCR 结果合并 + 投票归属。
思路：
  1) 把「整图 / 3x3 / 2x2 / 4x4 / 逐城」五路结果全部换算到画布坐标；
  2) 对每个城址，收集满足「垂直居中 + 水平间隙 5~46px」的候选标签；
  3) 按文本投票（不同来源各算一票），得票最高且领先者胜出；
  4) 票数持平或没有候选 → 标记为「待人工」。
"""
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
OX, OY = 512, 866          # 名称层 → 画布


def clean(s: str) -> str:
    s = s.replace("|", "").replace(" ", "").replace("\u3000", "")
    return re.sub(r"[^\u4e00-\u9fff]", "", s)


pool = []   # (text, x0, y0, x1, y1, source)  画布坐标


def safe_load(path):
    """空文件 / 空数组时 PowerShell 会写出空串或 null，这里统一兜住。"""
    try:
        txt = Path(path).read_text(encoding="utf-8").strip()
        if not txt or txt == "null":
            return []
        d = json.loads(txt)
        return d if isinstance(d, list) else [d]
    except Exception:
        return []


def add(text, x0, y0, x1, y1, src):
    t = clean(text)
    if t:
        pool.append((t, x0 + OX, y0 + OY, x1 + OX, y1 + OY, src))


# 1) 整图
for g in safe_load(ROOT / "tools" / "_ocr_names.json"):
    add(g["text"], g["x"], g["y"], g["x"] + g["w"], g["y"] + g["h"], "full")

# 2) 3x3（scale 2）
meta_txt = ROOT / "tools" / "ocr_tiles" / "meta.txt"
if meta_txt.exists():
    m3 = {}
    for line in meta_txt.read_text(encoding="utf-8").splitlines():
        nm, x0, y0, s = line.split()
        m3[nm.replace(".png", "")] = (int(x0), int(y0), float(s))
    for f in (ROOT / "tools" / "ocr_tiles").glob("t*.json"):
        x0, y0, s = m3.get(f.stem, (0, 0, 1))
        for g in safe_load(f):
            for l in (g.get("lines") or []):
                add(l["t"], l["x"] / s + x0, l["y"] / s + y0,
                    (l["x"] + l["w"]) / s + x0, (l["y"] + l["h"]) / s + y0, "t3")

# 3) p2 / p4
for tag in ("p2", "p4"):
    base = ROOT / "tools" / "passes" / tag
    mp = base / "meta.json"
    if not mp.exists():
        continue
    meta = json.loads(mp.read_text(encoding="utf-8"))
    for g in safe_load(base / "result.json"):
        m = meta.get(g["id"])
        if not m:
            continue
        for l in (g.get("lines") or []):
            add(l["t"], l["x"] / m["scale"] + m["x0"], l["y"] / m["scale"] + m["y0"],
                (l["x"] + l["w"]) / m["scale"] + m["x0"],
                (l["y"] + l["h"]) / m["scale"] + m["y0"], tag)

# 4) 逐城（scale 3）
np_ = ROOT / "tools" / "node_crops" / "meta.json"
if np_.exists():
    nm = json.loads(np_.read_text(encoding="utf-8"))
    for g in safe_load(ROOT / "tools" / "_ocr_nodes.json"):
        m = nm.get(g["id"])
        if not m:
            continue
        for l in (g.get("lines") or []):
            add(l["t"], l["x"] / 3 + m["x0"], l["y"] / 3 + m["y0"],
                (l["x"] + l["w"]) / 3 + m["x0"], (l["y"] + l["h"]) / 3 + m["y0"], "node")

print("pool", len(pool), "sources", Counter(p[5] for p in pool))

# ---------- 归属 ----------
nodes = list(csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")))
for n in nodes:
    n["x"] = float(n["x"])
    n["y"] = float(n["y"])

GAP_MIN, GAP_MAX, DY_TOL = 3, 50, 15
cand = defaultdict(list)     # node index -> list of (gap, text, src)
for t, x0, y0, x1, y1, src in pool:
    cy = (y0 + y1) / 2
    for i, n in enumerate(nodes):
        if abs(cy - n["y"]) > DY_TOL:
            continue
        gr = x0 - n["x"]
        gl = n["x"] - x1
        gap = None
        if GAP_MIN <= gr <= GAP_MAX:
            gap = gr
        elif GAP_MIN <= gl <= GAP_MAX:
            gap = gl
        if gap is not None:
            cand[i].append((gap, t, src))

named = conflict = none = 0
for i, n in enumerate(nodes):
    cs = cand.get(i, [])
    if not cs:
        n["name"] = ""
        n["_status"] = "无候选"
        none += 1
        continue
    votes = defaultdict(set)     # text -> set(src)
    best_gap = {}
    for gap, t, src in cs:
        votes[t].add(src)
        best_gap[t] = min(best_gap.get(t, 1e9), gap)
    ranked = sorted(votes.items(), key=lambda kv: (-len(kv[1]), best_gap[kv[0]]))
    top_t, top_s = ranked[0]
    second = len(ranked[1][1]) if len(ranked) > 1 else 0
    if len(top_s) >= 2 or (second == 0 and len(top_s) == 1):
        n["name"] = top_t
        n["_status"] = "自动"
        named += 1
    else:
        n["name"] = top_t
        n["_status"] = "存疑"
        conflict += 1

print(f"自动命名 {named}  存疑 {conflict}  无候选 {none}")

# 写回
with (ROOT / "data" / "map" / "nodes.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "name", "kind", "x", "y"])
    for n in nodes:
        w.writerow([n["id"], n["name"], n["kind"], round(n["x"], 1), round(n["y"], 1)])

# 仅导出需要人工的
need = [n for n in nodes if n["_status"] != "自动"]
with (ROOT / "data" / "map" / "review_todo.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "kind", "x", "y", "recognized", "status", "correction"])
    for n in need:
        w.writerow([n["id"], n["kind"], round(n["x"]), round(n["y"]), n["name"], n["_status"], ""])
print("need manual", len(need))

# 更新全量 review.csv 的状态
allrows = []
for n in nodes:
    rr, cc = int(n["y"] // (8509 // 3)), int(n["x"] // (9101 // 3))
    allrows.append((n, f"r{rr}c{cc}"))
with (ROOT / "data" / "map" / "review.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "kind", "tile", "x", "y", "recognized", "chars", "status", "correction"])
    for n, tile in allrows:
        st = n["_status"] if n["_status"] != "自动" else ("长名" if len(n["name"]) >= 3 else "自动")
        w.writerow([n["id"], n["kind"], tile, round(n["x"]), round(n["y"]),
                    n["name"], len(n["name"]), st, ""])
print("done")
