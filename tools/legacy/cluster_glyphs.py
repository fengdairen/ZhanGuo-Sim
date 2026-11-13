# -*- coding: utf-8 -*-
"""单字地名解法：字形聚类 + 已知字库匹配。

输出：
  data/map/nodes.csv            补上能自动确认的字
  tools/clusters/*.png          每个「未确认字形簇」的代表图
  data/map/clusters.csv         簇清单（用户给每簇起名一次即可）
"""
import csv
import json
import pickle
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
OX, OY = 512, 866
G = 28
CL = ROOT / "tools" / "clusters"
CL.mkdir(parents=True, exist_ok=True)

alpha = np.asarray(Image.open(ROOT / "assets" / "source" / "城池名称.png").convert("RGBA"))[:, :, 3] > 0
H, W = alpha.shape

# ---------- 1) 连通域（字形） ----------
runs = []
for y in range(H):
    row = alpha[y]
    if not row.any():
        continue
    d = np.diff(np.concatenate(([0], row.astype(np.int8), [0])))
    st = np.where(d == 1)[0]; en = np.where(d == -1)[0]
    for s, e in zip(st, en):
        runs.append((y, int(s), int(e)))

parent = list(range(len(runs)))

def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]; x = parent[x]
    return x

def union(a_, b_):
    ra, rb = find(a_), find(b_)
    if ra != rb: parent[rb] = ra

by_row = {}
for i, (y, x0, x1) in enumerate(runs):
    by_row.setdefault(y, []).append(i)

for y in range(1, H):
    cur = by_row.get(y, []); prev = by_row.get(y - 1, [])
    i = j = 0
    while i < len(cur) and j < len(prev):
        _, cx0, cx1 = runs[cur[i]]
        _, px0, px1 = runs[prev[j]]
        if cx0 < px1 + 1 and px0 < cx1 + 1:
            union(cur[i], prev[j])
        if cx1 < px1: i += 1
        else: j += 1

agg = {}
for i, (y, x0, x1) in enumerate(runs):
    r = find(i); rec = agg.get(r)
    if rec is None:
        agg[r] = [x0, y, x1, y]
    else:
        rec[0] = min(rec[0], x0); rec[1] = min(rec[1], y)
        rec[2] = max(rec[2], x1); rec[3] = max(rec[3], y)
glyphs = sorted((tuple(map(int, b)) for b in agg.values()), key=lambda g: (g[1], g[0]))
print("glyphs", len(glyphs))

# ---------- 2) 合并成词 ----------
words = []
for g in glyphs:
    x0, y0, x1, y1 = g
    hit = False
    for w in words:
        if not (y1 < w[1] - 2 or y0 > w[3] + 2):
            if max(x0 - w[2], w[0] - x1) <= 9:
                w[0] = min(w[0], x0); w[1] = min(w[1], y0)
                w[2] = max(w[2], x1); w[3] = max(w[3], y1)
                hit = True
                break
    if not hit:
        words.append([x0, y0, x1, y1])
print("words", len(words))


def norm(sub):
    ys, xs = np.where(sub)
    if len(xs) == 0:
        return None
    sub = sub[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = sub.shape
    s = (G - 4) / max(h, w)
    nh, nw = max(1, int(round(h * s))), max(1, int(round(w * s)))
    img = Image.fromarray((sub * 255).astype(np.uint8)).resize((nw, nh), Image.LANCZOS)
    c = np.zeros((G, G), dtype=np.float32)
    oy, ox = (G - nh) // 2, (G - nw) // 2
    c[oy:oy + nh, ox:ox + nw] = np.asarray(img, dtype=np.float32) / 255.0
    v = c.reshape(-1)
    n = np.linalg.norm(v)
    return (v / n).astype(np.float32) if n > 0 else None


# 词内字形
for w in words:
    x0, y0, x1, y1 = w
    inner = [g for g in glyphs if g[0] >= x0 - 1 and g[2] <= x1 + 1 and g[1] >= y0 - 1 and g[3] <= y1 + 1]
    w.append(sorted(inner, key=lambda g: g[0]))
    w.append((x1 - x0 + 1))

# ---------- 3) 词 → 城址 ----------
nodes = list(csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")))
for n in nodes:
    n["x"] = float(n["x"]) - OX
    n["y"] = float(n["y"]) - OY
    n["canvas_x"] = n["x"] + OX
    n["canvas_y"] = n["y"] + OY

pairs = []
for wi, w in enumerate(words):
    x0, y0, x1, y1 = w[0], w[1], w[2], w[3]
    cy = (y0 + y1) / 2
    for ni, n in enumerate(nodes):
        if abs(cy - n["y"]) > 16:
            continue
        gap = min(abs(x0 - n["x"]), abs(n["x"] - x1))
        if gap <= 50:
            pairs.append((gap, wi, ni))
pairs.sort()
used_w, used_n = set(), set()
word_of = {}
for gap, wi, ni in pairs:
    if wi in used_w or ni in used_n:
        continue
    used_w.add(wi); used_n.add(ni); word_of[ni] = wi
print("words assigned", len(word_of))

# ---------- 4) 已知字库（来自 OCR 成功且为 2 字的地名） ----------
lib = defaultdict(list)
for ni, wi in word_of.items():
    n = nodes[ni]
    name = n["name"]
    gl = words[wi][4]
    if len(name) == 2 and len(gl) == 2:
        for ch, g in zip(name, gl):
            v = norm(alpha[g[1]:g[3] + 1, g[0]:g[2] + 1])
            if v is not None:
                lib[ch].append(v)
proto = {c: np.mean(np.stack(v), axis=0) for c, v in lib.items()}
for c in proto:
    proto[c] = proto[c] / np.linalg.norm(proto[c])
print("library chars", len(proto), "samples", sum(len(v) for v in lib.values()))

# ---------- 5) 单字词匹配 / 聚类 ----------
singles = []
for ni, wi in word_of.items():
    n = nodes[ni]
    gl = words[wi][4]
    if n["name"] or len(gl) != 1:
        continue
    g = gl[0]
    v = norm(alpha[g[1]:g[3] + 1, g[0]:g[2] + 1])
    if v is not None:
        singles.append((ni, v, g))
print("single-char unknowns", len(singles))

chars = list(proto.keys())
if chars:
    M = np.stack([proto[c] for c in chars])
else:
    M = np.zeros((0, G * G), dtype=np.float32)

auto = 0
rest = []
for ni, v, g in singles:
    if len(chars):
        sims = M @ v
        k = int(np.argmax(sims))
        top = float(sims[k])
        second = float(np.partition(sims, -2)[-2]) if len(sims) > 1 else 0.0
        if top >= 0.93 and top - second >= 0.06:
            nodes[ni]["name"] = chars[k]
            auto += 1
            continue
    rest.append((ni, v, g))
print("auto-resolved single chars", auto, "remaining", len(rest))

# 剩余按形状聚类
V = np.stack([v for _, v, _ in rest]) if rest else np.zeros((0, G * G), dtype=np.float32)
lab = list(range(len(rest)))

def f2(x):
    while lab[x] != x:
        lab[x] = lab[lab[x]]; x = lab[x]
    return x

if len(rest):
    S = V @ V.T
    for i in range(len(rest)):
        for j in range(i + 1, len(rest)):
            if S[i, j] >= 0.90:
                a_, b_ = f2(i), f2(j)
                if a_ != b_: lab[b_] = a_

clusters = defaultdict(list)
for i in range(len(rest)):
    clusters[f2(i)].append(i)
print("clusters", len(clusters))

# ---------- 6) 输出 ----------
font = ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", 20)
cl_rows = []
sheet_imgs = []
for ci, (root, members) in enumerate(sorted(clusters.items(), key=lambda kv: -len(kv[1]))):
    ni, v, g = rest[members[0]]
    pad = 6
    crop = alpha[max(0, g[1] - pad):g[3] + 1 + pad, max(0, g[0] - pad):g[2] + 1 + pad]
    im = Image.new("RGB", (crop.shape[1] * 4, crop.shape[0] * 4), (255, 255, 255))
    src = Image.fromarray((crop * 255).astype(np.uint8)).convert("L").resize((crop.shape[1] * 4, crop.shape[0] * 4), Image.LANCZOS)
    im.paste(Image.merge("RGB", (src, src, src)), (0, 0))
    im.save(CL / f"c{ci:03d}.png")
    sheet_imgs.append((ci, im, len(members)))
    for m in members:
        cl_rows.append((f"c{ci:03d}", nodes[rest[m][0]]["id"], len(members)))

with (ROOT / "data" / "map" / "clusters.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["cluster", "char", "count", "sample_node", "x", "y"])
    for ci, (root, members) in enumerate(sorted(clusters.items(), key=lambda kv: -len(kv[1]))):
        ni = rest[members[0]][0]
        w.writerow([f"c{ci:03d}", "", len(members), nodes[ni]["id"],
                    round(nodes[ni]["canvas_x"]), round(nodes[ni]["canvas_y"])])

# 联系表
cols, cell = 8, 120
rows_n = (len(sheet_imgs) + cols - 1) // cols
sheet = Image.new("RGB", (cols * cell, rows_n * (cell + 24)), (255, 255, 255))
d = ImageDraw.Draw(sheet)
for idx, (ci, im, cnt) in enumerate(sheet_imgs):
    r, c = idx // cols, idx % cols
    x, y = c * cell, r * (cell + 24)
    thumb = im.copy()
    thumb.thumbnail((cell - 10, cell - 10), Image.LANCZOS)
    sheet.paste(thumb, (x + 5, y + 5))
    d.text((x + 5, y + cell), f"c{ci:03d} ×{cnt}", fill=(0, 0, 0), font=font)
sheet.save(ROOT / "data" / "map" / "clusters_sheet.png")
print("clusters sheet", sheet.size)

# 写回 nodes
with (ROOT / "data" / "map" / "nodes.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "name", "kind", "x", "y"])
    for n in nodes:
        w.writerow([n["id"], n["name"], n["kind"], round(n["canvas_x"], 1), round(n["canvas_y"], 1)])

named = sum(1 for n in nodes if n["name"])
print(f"named {named}/{len(nodes)}")
