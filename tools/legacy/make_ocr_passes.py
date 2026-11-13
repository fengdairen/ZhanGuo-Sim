# -*- coding: utf-8 -*-
"""生成多种切分/缩放方案的原图分块，供多轮 OCR 交叉验证。"""
import json
from pathlib import Path

from PIL import Image

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
SRC = ROOT / "tools" / "_names_white.png"
BASE = ROOT / "tools" / "passes"
BASE.mkdir(exist_ok=True)

# (名称, 网格数, 放大倍数)
CONFIGS = [
    ("p2", 2, 1.6),
    ("p4", 4, 2.0),
]

im = Image.open(SRC).convert("RGB")
W, H = im.size
print("source", W, H)

for name, n, scale in CONFIGS:
    out = BASE / name
    out.mkdir(exist_ok=True)
    for f in out.glob("*.png"):
        f.unlink()
    tw, th = W // n, H // n
    meta = {}
    for r in range(n):
        for c in range(n):
            x0 = c * tw
            y0 = r * th
            x1 = W if c == n - 1 else (c + 1) * tw
            y1 = H if r == n - 1 else (r + 1) * th
            t = im.crop((x0, y0, x1, y1))
            t = t.resize((int(t.width * scale), int(t.height * scale)), Image.LANCZOS)
            fname = f"t{r}{c}.png"
            t.save(out / fname)
            meta[f"t{r}{c}"] = {"x0": x0, "y0": y0, "scale": scale}
    (out / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    print(name, "tiles", n * n, "tile", tw, th, "->", tw * scale, th * scale)
