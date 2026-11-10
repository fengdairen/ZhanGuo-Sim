# -*- coding: utf-8 -*-
"""标定两张参考位图在 9101x8509 画布坐标系中的偏移。

方法：不猜，用底图 ditu.png 反解。
- 海岸线：底图海面是有明确色差的褐区，取海面掩膜的内外边界带；
  搜索 (dx,dy) 使"海岸线像素落在海陆边界带上"的比例最大。
- 河道/边界：底图上山河是比周围更暗的细线，用 top-hat（原图 - 高斯模糊）取暗线；
  搜索 (dx,dy) 使"红/黑像素落在暗线上"的比例最大。

结果写 tools/_vec_cal.txt（UTF-8），控制台不看中文。
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

S = 4                       # 标定用缩放
CANVAS = (9101, 8509)
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tools" / "_vec_cal.txt"
lines = []


def log(msg):
    lines.append(str(msg))


# ---------- 底图 ----------
ditu = Image.open(ROOT / "ditu.png").convert("RGB")
assert ditu.size == CANVAS, ditu.size
W, H = CANVAS

# 海面：从东侧多个种子做 floodfill，取并集
sea_full = np.zeros((H, W), dtype=bool)
for seed in [(8300, 2600), (8800, 4200), (7600, 6400), (8900, 1200), (6200, 900)]:
    im = ditu.copy()
    try:
        ImageDraw.floodfill(im, seed, (255, 0, 255), thresh=38)
    except Exception as e:
        log(f"floodfill {seed} 失败: {e}")
        continue
    a = np.array(im)
    sea_full |= (a[..., 0] >= 250) & (a[..., 1] <= 5) & (a[..., 2] >= 250)
log(f"海面像素（全分辨率）: {int(sea_full.sum())}")

# 暗线（山河）
import numpy as _np
lum = np.array(ditu.convert("L"), dtype=np.int16)
blur = np.array(ditu.convert("L").filter(ImageFilter.GaussianBlur(3)), dtype=np.int16)
dark = (lum - blur) <= -6          # 比周围暗 -> 细线
log(f"暗线像素: {int(dark.sum())}")


def pool4(mask):
    h, w = mask.shape
    h2, w2 = h // S, w // S
    return mask[:h2 * S, :w2 * S].reshape(h2, S, w2, S).max(axis=(1, 3))


sea4 = pool4(sea_full)
dark4 = pool4(dark)
H4, W4 = sea4.shape
log(f"标定网格 {W4}x{H4}")


def dilate(m, n=1):
    out = m.copy()
    for _ in range(n):
        p = np.zeros_like(out)
        p[1:, :] |= out[:-1, :]
        p[:-1, :] |= out[1:, :]
        p[:, 1:] |= out[:, :-1]
        p[:, :-1] |= out[:, 1:]
        out = out | p
    return out


sea_d = dilate(sea4, 2)
sea_e = ~dilate(~sea4, 2)
band = sea_d & sea_e          # 海岸带
log(f"海岸带像素: {int(band.sum())}")

# ---------- 海岸线 ----------
coast = np.array(Image.open(ROOT / "海岸线.png").convert("RGBA"))
cm = coast[..., 3] > 100
cm4 = pool4(cm)
log(f"海岸线像素: {int(cm.sum())} -> 1/{S} 尺度 {int(cm4.sum())}")


def place(mask4, ox, oy, shape):
    """把 1/S 尺度的 mask 按画布像素偏移 (ox,oy) 贴进全图。"""
    out = np.zeros(shape, dtype=bool)
    x0, y0 = int(round(ox / S)), int(round(oy / S))
    h, w = mask4.shape
    xa, ya = max(0, x0), max(0, y0)
    xb, yb = min(shape[1], x0 + w), min(shape[0], y0 + h)
    if xb <= xa or yb <= ya:
        return out
    out[ya:yb, xa:xb] = mask4[ya - y0:yb - y0, xa - x0:xb - x0]
    return out


best = None
for dx in range(-40, 41, 4):
    for dy in range(-40, 41, 4):
        m = place(cm4, 5815 + dx, 1509 + dy, (H4, W4))
        n = int(m.sum())
        if n == 0:
            continue
        score = float((band & m).sum()) / n
        if best is None or score > best[0]:
            best = (score, dx, dy, n)
log(f"海岸线粗搜: score={best[0]:.3f} dx={best[1]} dy={best[2]} n={best[3]}")
# 细搜
bx, by = best[1], best[2]
best2 = best
for dx in range(bx - 6, bx + 7, 1):
    for dy in range(by - 6, by + 7, 1):
        m = place(cm4, 5815 + dx, 1509 + dy, (H4, W4))
        n = int(m.sum())
        if n == 0:
            continue
        score = float((band & m).sum()) / n
        if score > best2[0]:
            best2 = (score, dx, dy, n)
log(f"海岸线细搜: score={best2[0]:.3f} dx={best2[1]} dy={best2[2]}")
coast_off = (5815 + best2[1], 1509 + best2[2])
log(f"海岸线偏移 => {coast_off}")

# ---------- 河道湖泊 / 边界 ----------
riv = np.array(Image.open(ROOT / "河道湖泊.png").convert("RGBA"))
alpha = riv[..., 3] > 100
rgb = riv[..., :3].astype(np.int16)
red = alpha & (rgb[..., 0] > 180) & (rgb[..., 1] < 90) & (rgb[..., 2] < 90)
blue = alpha & (rgb[..., 2] > 180) & (rgb[..., 0] < 90) & (rgb[..., 1] < 160)
black = alpha & (rgb.max(axis=2) < 80)
log(f"河道湖泊.png 尺寸 {riv.shape[1]}x{riv.shape[0]}")
log(f"  红 {int(red.sum())}  蓝 {int(blue.sum())}  黑 {int(black.sum())}")

red4 = pool4(red)
blk4 = pool4(black)
dark_d = dilate(dark4, 1)

for name, m4 in [("红(河)", red4), ("黑(边界)", blk4)]:
    bestr = None
    for dx in range(-40, 41, 4):
        for dy in range(-80, 41, 4):
            m = place(m4, dx, dy, (H4, W4))
            n = int(m.sum())
            if n == 0:
                continue
            score = float((dark_d & m).sum()) / n
            if bestr is None or score > bestr[0]:
                bestr = (score, dx, dy, n)
    log(f"{name} 粗搜: score={bestr[0]:.3f} dx={bestr[1]} dy={bestr[2]} n={bestr[3]}")
    bx, by = bestr[1], bestr[2]
    b2 = bestr
    for dx in range(bx - 6, bx + 7, 1):
        for dy in range(by - 6, by + 7, 1):
            m = place(m4, dx, dy, (H4, W4))
            n = int(m.sum())
            if n == 0:
                continue
            score = float((dark_d & m).sum()) / n
            if score > b2[0]:
                b2 = (score, dx, dy, n)
    log(f"{name} 细搜: score={b2[0]:.3f} dx={b2[1]} dy={b2[2]}")
    log(f"{name} 偏移 => ({b2[1]}, {b2[2]})")

OUT.write_text("\n".join(lines), encoding="utf-8")
print("done ->", OUT)
