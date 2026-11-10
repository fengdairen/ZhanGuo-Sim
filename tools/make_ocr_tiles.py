# -*- coding: utf-8 -*-
"""把地名层切 3x3（带重叠）并放大 2x，供逐块 OCR。"""
from pathlib import Path

from PIL import Image

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
SRC = ROOT / "tools" / "_names_white.png"
OUT = ROOT / "tools" / "ocr_tiles"
OUT.mkdir(exist_ok=True)

im = Image.open(SRC).convert("RGB")
W, H = im.size
N, PAD, SCALE = 3, 120, 2
tw, th = W // N, H // N

meta = []
for r in range(N):
    for c in range(N):
        x0 = max(0, c * tw - PAD)
        y0 = max(0, r * th - PAD)
        x1 = min(W, (c + 1) * tw + PAD)
        y1 = min(H, (r + 1) * th + PAD)
        t = im.crop((x0, y0, x1, y1))
        t = t.resize((t.width * SCALE, t.height * SCALE), Image.LANCZOS)
        name = f"t{r}{c}.png"
        t.save(OUT / name)
        meta.append((name, x0, y0, SCALE))

(OUT / "meta.txt").write_text(
    "\n".join(f"{n} {x} {y} {s}" for n, x, y, s in meta), encoding="utf-8")
print("tiles", len(meta), "size", tw, th)
