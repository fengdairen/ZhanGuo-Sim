# -*- coding: utf-8 -*-
"""字体匹配实验：把已识别的地名字与几种字体的渲染结果比对，看哪种最接近图上字形。"""
import csv
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
OX, OY = 512, 866
G = 24
alpha = np.asarray(Image.open(ROOT / "城池名称.png").convert("RGBA"))[:, :, 3] > 0
H, W = alpha.shape

FONTS = [
    ("simsun", "C:/Windows/Fonts/simsun.ttc"),
    ("simhei", "C:/Windows/Fonts/simhei.ttf"),
    ("msyh", "C:/Windows/Fonts/msyh.ttc"),
    ("simkai", "C:/Windows/Fonts/simkai.ttf"),
    ("simfang", "C:/Windows/Fonts/simfang.ttf"),
]


def ink_bbox(x, y, reach=70):
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


def norm_bin(sub):
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
    return v / n if n > 0 else None


def render(ch, fontpath, size=64):
    f = ImageFont.truetype(fontpath, size)
    img = Image.new("L", (size * 2, size * 2), 0)
    d = ImageDraw.Draw(img)
    bbox = d.textbbox((0, 0), ch, font=f)
    d.text((size - (bbox[2] + bbox[0]) / 2, size - (bbox[3] + bbox[1]) / 2), ch, font=f, fill=255)
    a = np.asarray(img) > 100
    return norm_bin(a)


rows = list(csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")))
samples = []
for r in rows:
    if len(r["name"]) != 2:
        continue
    x, y = int(float(r["x"])) - OX, int(float(r["y"])) - OY
    bb = ink_bbox(x, y)
    if not bb:
        continue
    x0, y0, x1, y1 = bb
    w = x1 - x0 + 1
    if not (30 <= w <= 58):
        continue
    half = (x1 - x0 + 1) // 2
    for i, ch in enumerate(r["name"]):
        a0 = x0 + i * half
        a1 = x0 + (i + 1) * half - 1
        v = norm_bin(alpha[y0:y1 + 1, a0:a1 + 1])
        if v is not None:
            samples.append((ch, v))
    if len(samples) >= 60:
        break

print("samples", len(samples))
scores = {}
for name, path in FONTS:
    if not Path(path).exists():
        print("missing", name)
        continue
    tot = []
    for ch, v in samples:
        try:
            t = render(ch, path)
        except Exception:
            continue
        if t is None:
            continue
        tot.append(float(t @ v))
    if tot:
        scores[name] = (np.mean(tot), np.median(tot), len(tot))
for k, v in sorted(scores.items(), key=lambda kv: -kv[1][0]):
    print(f"{k:8} mean={v[0]:.3f} median={v[1]:.3f} n={v[2]}")
