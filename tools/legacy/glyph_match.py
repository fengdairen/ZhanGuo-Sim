# -*- coding: utf-8 -*-
"""用地图自身的字形做模板，识别 OCR 读不出的单字地名。

原理：同一张图的字体完全一致。
  1) 从「已正确识别」的 2 字地名中切出单字，建立 字形→字 模板库；
  2) 对未识别的城址，取其旁边的墨迹块，切出单字；
  3) 用归一化相关度在模板库中匹配。
"""
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
OX, OY = 512, 866
G = 24                      # 归一化尺寸

alpha = np.asarray(Image.open(ROOT / "assets" / "source" / "城池名称.png").convert("RGBA"))[:, :, 3] > 0
H, W = alpha.shape


def ink_bbox(x, y, reach=70):
    """在标记左右两侧找墨迹块，返回最靠近的那个 bbox。"""
    best = None
    for x0, x1 in ((x + 5, x + reach), (x - reach, x - 5)):
        xa, xb = max(0, int(x0)), min(W, int(x1))
        ya, yb = max(0, int(y - 22)), min(H, int(y + 22))
        if xb <= xa or yb <= ya:
            continue
        sub = alpha[ya:yb, xa:xb]
        if sub.sum() < 12:
            continue
        ys, xs = np.where(sub)
        bb = (xa + xs.min(), ya + ys.min(), xa + xs.max(), ya + ys.max())
        gap = (bb[0] - x) if bb[0] > x else (x - bb[2])
        if best is None or gap < best[0]:
            best = (gap, bb)
    return best[1] if best else None


def norm(crop):
    """二值 → 等比缩放 → 居中放进 G×G → 归一化向量。"""
    ys, xs = np.where(crop)
    if len(xs) == 0:
        return None
    sub = crop[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = sub.shape
    scale = (G - 4) / max(h, w)
    nh, nw = max(1, int(round(h * scale))), max(1, int(round(w * scale)))
    img = Image.fromarray((sub * 255).astype(np.uint8)).resize((nw, nh), Image.LANCZOS)
    canvas = np.zeros((G, G), dtype=np.float32)
    oy, ox = (G - nh) // 2, (G - nw) // 2
    canvas[oy:oy + nh, ox:ox + nw] = np.asarray(img, dtype=np.float32) / 255.0
    v = canvas.reshape(-1)
    n = np.linalg.norm(v)
    return v / n if n > 0 else None


def split_cols(bb, n):
    """把整体 bbox 按字符数等分（CJK 等宽）。"""
    x0, y0, x1, y1 = bb
    w = (x1 - x0 + 1) / n
    return [(int(x0 + i * w), y0, int(x0 + (i + 1) * w) - 1, y1) for i in range(n)]


rows = list(csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")))
for r in rows:
    r["x"] = float(r["x"])
    r["y"] = float(r["y"])

# ---------- 1) 建库：只取「2 字且已识别」的样本 ----------
lib = defaultdict(list)
built = 0
for r in rows:
    name = r["name"]
    if len(name) != 2:
        continue
    x, y = int(r["x"]) - OX, int(r["y"]) - OY
    bb = ink_bbox(x, y)
    if not bb:
        continue
    x0, y0, x1, y1 = bb
    # bbox 应为两个字宽；若明显偏离则跳过
    if not (30 <= (x1 - x0 + 1) <= 58):
        continue
    for i, (a0, b0, a1, b1) in enumerate(split_cols(bb, 2)):
        sub = alpha[b0:b1 + 1, a0:a1 + 1]
        v = norm(sub)
        if v is not None:
            lib[name[i]].append(v)
            built += 1
print("templates", built, "distinct chars", len(lib))

# 每个字取平均模板
proto = {c: np.mean(np.stack(vs), axis=0) for c, vs in lib.items()}
chars = list(proto.keys())
M = np.stack([proto[c] for c in chars])          # (K, G*G)
Mn = M / np.linalg.norm(M, axis=1, keepdims=True)

# ---------- 2) 识别未命名的单字 ----------
todo = [r for r in rows if not r["name"]]
resolved, unknown = [], []
for r in todo:
    x, y = int(r["x"]) - OX, int(r["y"]) - OY
    bb = ink_bbox(x, y)
    if not bb:
        unknown.append((r, None))
        continue
    x0, y0, x1, y1 = bb
    w = x1 - x0 + 1
    if w > 34:               # 不像单字（可能两字或残片）
        unknown.append((r, bb))
        continue
    v = norm(alpha[y0:y1 + 1, x0:x1 + 1])
    if v is None:
        unknown.append((r, bb))
        continue
    sims = Mn @ v
    k = int(np.argmax(sims))
    top, second = float(sims[k]), float(np.partition(sims, -2)[-2])
    if top >= 0.86 and top - second >= 0.04:
        resolved.append((r, chars[k], top, top - second))
    else:
        unknown.append((r, bb))

print(f"未命名 {len(todo)}  字形匹配成功 {len(resolved)}  仍未知 {len(unknown)}")
from collections import Counter
print("匹配到的字", Counter(c for _, c, _, _ in resolved).most_common(20))

# 写回
for r, c, _, _ in resolved:
    r["name"] = c

with (ROOT / "data" / "map" / "nodes.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "name", "kind", "x", "y"])
    for r in rows:
        w.writerow([r["id"], r["name"], r["kind"], round(r["x"], 1), round(r["y"], 1)])

# 剩余
with (ROOT / "data" / "map" / "review_todo.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "kind", "x", "y", "recognized", "status", "correction"])
    for r, bb in unknown:
        w.writerow([r["id"], r["kind"], round(r["x"]), round(r["y"]), "", "未识别", ""])
    # 同时保留 3 字以上的
    for r in rows:
        if len(r["name"]) >= 3:
            w.writerow([r["id"], r["kind"], round(r["x"]), round(r["y"]), r["name"], "长名待查", ""])
print("review_todo 写出完成")
