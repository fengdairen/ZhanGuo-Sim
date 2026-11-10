# -*- coding: utf-8 -*-
"""标定 v2：用底图的精确海色，不再依赖 floodfill。

1. 海岸线：底图海面是纯色 (199,154,102)。取海陆边界带，
   搜索使"海岸线像素落在边界带上"比例最大的偏移（按 1/2 尺度，精度 2px）。
2. 河道湖泊：湖泊是蓝色块。底图里水体同色，取"内陆水体连通域"质心，
   与蓝色连通域质心做最近邻匹配，取位移中位数。这样红/黑线与蓝块共用同一偏移。

中文结果写 tools/_vec_cal2.txt。
"""
from pathlib import Path

import numpy as np
from PIL import Image

S = 2
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tools" / "_vec_cal2.txt"
lines = []


def log(m):
    lines.append(str(m))


# ---------- 工具 ----------
def pool(mask, s=S):
    h, w = mask.shape
    h2, w2 = h // s, w // s
    return mask[:h2 * s, :w2 * s].reshape(h2, s, w2, s).max(axis=(1, 3))


def dilate(m, n=1):
    out = m.copy()
    for _ in range(n):
        p = np.zeros_like(out)
        p[1:, :] |= out[:-1, :]
        p[:-1, :] |= out[1:, :]
        p[:, 1:] |= out[:, :-1]
        p[:, :-1] |= out[:, 1:]
        out |= p
    return out


def label_runs(mask):
    """8 连通域标记（按行游程 + 并查集）。返回 (labels, runs, n)。"""
    H, W = mask.shape
    runs = []            # (y, x0, x1) 含端点
    row_span = []        # 每行的 run 索引区间
    for y in range(H):
        row = mask[y]
        if not row.any():
            row_span.append((len(runs), len(runs)))
            continue
        d = np.diff(np.concatenate(([0], row.view(np.int8), [0])))
        starts = np.flatnonzero(d == 1)
        ends = np.flatnonzero(d == -1) - 1
        base = len(runs)
        row_span.append((base, base + len(starts)))
        for x0, x1 in zip(starts.tolist(), ends.tolist()):
            runs.append((y, x0, x1))

    parent = list(range(len(runs)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for y in range(1, H):
        a0, a1 = row_span[y - 1]
        b0, b1 = row_span[y]
        i, j = a0, b0
        while i < a1 and j < b1:
            _, ax0, ax1 = runs[i]
            _, bx0, bx1 = runs[j]
            if ax0 - 1 <= bx1 and bx0 - 1 <= ax1:      # 8 邻接
                union(i, j)
            if ax1 < bx1:
                i += 1
            else:
                j += 1

    roots = {}
    labels = []
    for k in range(len(runs)):
        r = find(k)
        if r not in roots:
            roots[r] = len(roots)
        labels.append(roots[r])
    return labels, runs, len(roots)


def comp_stats(labels, runs, n):
    area = np.zeros(n, dtype=np.int64)
    sx = np.zeros(n)
    sy = np.zeros(n)
    bb = np.array([[10 ** 9, 10 ** 9, -1, -1]] * n, dtype=np.int64)
    for k, (y, x0, x1) in enumerate(runs):
        l = labels[k]
        w = x1 - x0 + 1
        area[l] += w
        sx[l] += w * (x0 + x1) / 2.0
        sy[l] += w * y
        bb[l] = [min(bb[l][0], x0), min(bb[l][1], y), max(bb[l][2], x1), max(bb[l][3], y)]
    cx = np.where(area > 0, sx / np.maximum(area, 1), 0)
    cy = np.where(area > 0, sy / np.maximum(area, 1), 0)
    return area, cx, cy, bb


# ---------- 底图水体 ----------
ditu = Image.open(ROOT / "ditu.png").convert("RGB")
a = np.array(ditu)
water = (
    (np.abs(a[..., 0].astype(np.int16) - 199) <= 5)
    & (np.abs(a[..., 1].astype(np.int16) - 154) <= 5)
    & (np.abs(a[..., 2].astype(np.int16) - 102) <= 5)
)
log(f"水体像素: {int(water.sum())} ({water.mean()*100:.1f}%)")

water2 = pool(water)
H2, W2 = water2.shape
log(f"1/{S} 网格 {W2}x{H2}")

sea_d = dilate(water2, 2)
sea_e = ~dilate(~water2, 2)
band = sea_d & ~sea_e
log(f"水陆边界带像素: {int(band.sum())}")

# ---------- 海岸线偏移 ----------
coast = np.array(Image.open(ROOT / "海岸线.png").convert("RGBA"))
cm = coast[..., 3] > 100
cm2 = pool(cm)
log(f"海岸线像素 {int(cm.sum())} -> 1/{S} {int(cm2.sum())}")


def place(m4, ox, oy, shape):
    out = np.zeros(shape, dtype=bool)
    x0, y0 = int(round(ox / S)), int(round(oy / S))
    h, w = m4.shape
    xa, ya = max(0, x0), max(0, y0)
    xb, yb = min(shape[1], x0 + w), min(shape[0], y0 + h)
    if xb <= xa or yb <= ya:
        return out
    out[ya:yb, xa:xb] = m4[ya - y0:yb - y0, xa - x0:xb - x0]
    return out


best = None
for dx in range(-30, 31, 2):
    for dy in range(-30, 31, 2):
        m = place(cm2, 5815 + dx, 1509 + dy, (H2, W2))
        n = int(m.sum())
        if not n:
            continue
        sc = float((band & m).sum()) / n
        if best is None or sc > best[0]:
            best = (sc, dx, dy, n)
log(f"海岸线: score={best[0]:.3f} dx={best[1]} dy={best[2]} n={best[3]}")
COAST = (5815 + best[1], 1509 + best[2])
log(f"海岸线偏移 => {COAST}  (PSD 记录为 (5815,1509))")

# ---------- 湖泊质心匹配 ----------
riv = np.array(Image.open(ROOT / "河道湖泊.png").convert("RGBA"))
alpha = riv[..., 3] > 100
rgb = riv[..., :3].astype(np.int16)
blue = alpha & (rgb[..., 2] > 170) & (rgb[..., 0] < 100) & (rgb[..., 1] < 170)
log(f"蓝像素 {int(blue.sum())}")

blue2 = pool(blue)
lab, runs, n = label_runs(blue2)
area, cx, cy, bb = comp_stats(lab, runs, n)
idx = [i for i in range(n) if area[i] >= 12]
log(f"蓝块 {n} 个，面积>=12 的 {len(idx)} 个（1/{S} 尺度）")
blobs = [(cx[i], cy[i], area[i]) for i in idx]

# 底图内陆水体（排除最大连通域=海）
labw, runsw, nw = label_runs(water2)
areaw, cxw, cyw, bbw = comp_stats(labw, runsw, nw)
order = np.argsort(-areaw)
log(f"底图水体连通域 {nw} 个，最大 {int(areaw[order[0]])}（海）")
lakes = [(cxw[i], cyw[i], areaw[i]) for i in order[1:] if areaw[i] >= 20][:200]
log(f"内陆水体（面积>=20）取 {len(lakes)} 个")

deltas = []
for bx, by, ba in blobs:
    bestd = None
    for lx, ly, la in lakes:
        d = (lx - bx) ** 2 + (ly - by) ** 2
        if bestd is None or d < bestd[0]:
            bestd = (d, lx - bx, ly - by)
    if bestd and bestd[0] <= 60 ** 2:
        deltas.append((bestd[1], bestd[2], bestd[0] ** 0.5))

if deltas:
    dxs = np.array([d[0] for d in deltas]) * S
    dys = np.array([d[1] for d in deltas]) * S
    log(f"匹配上的蓝块 {len(deltas)} 个")
    log(f"位移中位数 dx={np.median(dxs):.0f} dy={np.median(dys):.0f}")
    log(f"位移均值   dx={dxs.mean():.0f} dy={dys.mean():.0f} 标准差 dx={dxs.std():.0f} dy={dys.std():.0f}")
    for d in sorted(deltas, key=lambda t: t[2])[:8]:
        log(f"   蓝块匹配 dx={d[0]*S:+.0f} dy={d[1]*S:+.0f} 距离={d[2]*S:.0f}")

OUT.write_text("\n".join(lines), encoding="utf-8")
print("done")
