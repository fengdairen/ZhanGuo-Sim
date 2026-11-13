# -*- coding: utf-8 -*-
"""勘误图生成（精简版）：
   - 名字 ≥3 字：红圈 + 标注「编号 名字」（提示可能粘连/误识）
   - 未识别    ：橙圈 + 标注「编号 ⌀」
   - 名字 ≤2 字：绿圈，不标注
同时输出 review.csv（可筛选）与 review_todo.csv（只含待处理）
"""
import csv
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
OUT = ROOT / "data" / "map" / "review"
OUT.mkdir(parents=True, exist_ok=True)

N = 3
S = 2
PAD = 70
FONT_PATH = "C:/Windows/Fonts/msyhbd.ttc"
FONT_SIZE = 24 * S

rows = list(csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")))
for r in rows:
    r["x"] = float(r["x"])
    r["y"] = float(r["y"])

im = Image.open(ROOT / "ditu.png").convert("RGB")
W, H = im.size
font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

GREEN = (0, 150, 0)
RED = (200, 0, 0)
ORANGE = (230, 120, 0)
RAD = {"都": 16, "城": 12, "邑": 10}
tw, th = W // N, H // N


def status(r):
    n = len(r["name"])
    if n == 0:
        return "未识别"
    if n >= 3:
        return "长名待查"
    return "短名"


for r in rows:
    rr, cc = int(r["y"] // th), int(r["x"] // tw)
    r["tile"] = f"r{rr}c{cc}"
    r["status"] = status(r)

made = []
for rr in range(N):
    for cc in range(N):
        cx0, cy0 = cc * tw, rr * th
        cx1, cy1 = min(cx0 + tw, W), min(cy0 + th, H)
        x0, y0 = max(0, cx0 - PAD), max(0, cy0 - PAD)
        x1, y1 = min(W, cx1 + PAD), min(H, cy1 + PAD)
        tile = im.crop((x0, y0, x1, y1)).copy()
        tile = tile.resize((tile.width * S, tile.height * S), Image.LANCZOS)
        d = ImageDraw.Draw(tile)
        placed = []
        n_in = 0

        def overlaps(b):
            return any(not (b[2] < p[0] or b[0] > p[2] or b[3] < p[1] or b[1] > p[3]) for p in placed)

        for r in rows:
            if not (cx0 <= r["x"] < cx1 and cy0 <= r["y"] < cy1):
                continue
            n_in += 1
            px, py = (r["x"] - x0) * S, (r["y"] - y0) * S
            rad = RAD[r["kind"]] * S
            st = r["status"]

            if st == "短名":
                d.ellipse([px - rad, py - rad, px + rad, py + rad], outline=GREEN, width=3 * S)
                continue

            color = RED if st == "长名待查" else ORANGE
            d.ellipse([px - rad, py - rad, px + rad, py + rad], outline=color, width=3 * S)

            label = f'{r["id"]} {r["name"]}' if st == "长名待查" else f'{r["id"]} ⌀'
            bb = d.textbbox((0, 0), label, font=font)
            w, h = bb[2] - bb[0], bb[3] - bb[1]
            cands = [
                (px + rad + 6, py - rad - h - 4),
                (px - rad - 6 - w, py - rad - h - 4),
                (px + rad + 6, py + rad + 4),
                (px - rad - 6 - w, py + rad + 4),
                (px - w / 2, py - rad - h - 10),
                (px - w / 2, py + rad + 10),
            ]
            tx, ty = cands[0]
            for ax, ay in cands:
                box = (ax - 3, ay - 2, ax + w + 3, ay + h + 2)
                if not overlaps(box):
                    tx, ty = ax, ay
                    placed.append(box)
                    break
            else:
                placed.append((tx - 3, ty - 2, tx + w + 3, ty + h + 2))

            d.rectangle([tx - 3, ty - 2, tx + w + 3, ty + h + 2], fill=(255, 255, 255), outline=color)
            d.text((tx - bb[0], ty - bb[1]), label, font=font, fill=color)

        name = f"tile_r{rr}c{cc}.png"
        tile.save(OUT / name)
        made.append((name, n_in))

# 索引图
idx = im.copy()
d = ImageDraw.Draw(idx)
for r in rows:
    rad = RAD[r["kind"]] + 5
    c = {"短名": GREEN, "长名待查": RED, "未识别": ORANGE}[r["status"]]
    d.ellipse([r["x"] - rad, r["y"] - rad, r["x"] + rad, r["y"] + rad], outline=c, width=4)
for i in range(1, N):
    d.line([(i * tw, 0), (i * tw, H)], fill=(0, 80, 220), width=6)
    d.line([(0, i * th), (W, i * th)], fill=(0, 80, 220), width=6)
for rr in range(N):
    for cc in range(N):
        d.text((cc * tw + 24, rr * th + 18), f"r{rr}c{cc}", fill=(0, 80, 220),
               font=ImageFont.truetype(FONT_PATH, 96))
s = 1600 / max(W, H)
idx.resize((int(W * s), int(H * s)), Image.LANCZOS).save(OUT / "index.png")

# CSV
COLS = ["id", "kind", "tile", "x", "y", "recognized", "chars", "status", "correction"]
rows.sort(key=lambda r: (r["tile"], r["y"], r["x"]))


def dump(path, data):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(COLS)
        for r in data:
            w.writerow([r["id"], r["kind"], r["tile"], round(r["x"]), round(r["y"]),
                        r["name"], len(r["name"]), r["status"], ""])


dump(ROOT / "data" / "map" / "review.csv", rows)
todo = [r for r in rows if r["status"] != "短名"]
dump(ROOT / "data" / "map" / "review_todo.csv", todo)

print("status", Counter(r["status"] for r in rows))
print("todo", len(todo), "total", len(rows), "tiles", len(made))
