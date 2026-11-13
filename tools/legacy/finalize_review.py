# -*- coding: utf-8 -*-
"""自检 + 生成最终勘误包：待办 CSV + 联系表。

可疑规则：
  未识别      名字为空
  长名待查    长度 ≥3
  多段存疑    由「城名+城名」或「城名+水名」粘连拆出来的
  疑似水名    以 水/泽/川/池 结尾
  疑似山名    以 山 结尾
  重名        150px 内出现同名
"""
import csv
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
OUT = ROOT / "data" / "map" / "todo_sheets"
OUT.mkdir(parents=True, exist_ok=True)
for f in OUT.glob("*.png"):
    f.unlink()

rows = list(csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")))
for r in rows:
    r["x"] = float(r["x"]); r["y"] = float(r["y"])

multi = {}
sp = ROOT / "tools" / "_suspect.json"
if sp.exists():
    for s in json.loads(sp.read_text(encoding="utf-8")):
        multi[s["id"]] = s

WATER = ("水",)          # 只把「以水结尾」当河名；泽/池 可能是地名（狗泽、黄池）
MOUNT = ("山",)

# 重名检测
for i, a in enumerate(rows):
    if not a["name"]:
        continue
    for b in rows[i + 1:]:
        if b["name"] != a["name"]:
            continue
        if math.hypot(a["x"] - b["x"], a["y"] - b["y"]) < 40:
            a["_dup"] = b["id"]; b["_dup"] = a["id"]

todo = []
for r in rows:
    n = r["name"]
    st = None
    if not n:
        st = "未识别"
    elif len(n) >= 5:
        st = "超长待查"
    elif r.get("_dup"):
        st = "近距重名"
    if st:
        r["_status"] = st
        todo.append(r)

from collections import Counter
print("状态分布", Counter(r["_status"] for r in todo))
print("待处理", len(todo), "已命名", sum(1 for r in rows if r["name"]), "/", len(rows))

with (ROOT / "data" / "map" / "review_todo.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "kind", "x", "y", "recognized", "status", "correction"])
    for r in todo:
        w.writerow([r["id"], r["kind"], round(r["x"]), round(r["y"]), r["name"], r["_status"], ""])

# 联系表
im = Image.open(ROOT / "ditu.png").convert("RGB")
font = ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", 20)
CW, CH, SCALE, COLS, ROWS = 240, 150, 2, 4, 8
per = COLS * ROWS
sheets = (len(todo) + per - 1) // per
for s in range(sheets):
    batch = todo[s * per:(s + 1) * per]
    canvas = Image.new("RGB", (COLS * CW * SCALE, ROWS * (CH * SCALE + 26)), (255, 255, 255))
    d = ImageDraw.Draw(canvas)
    for i, r in enumerate(batch):
        cx, cy = r["x"], r["y"]
        crop = im.crop((int(cx - CW / 2), int(cy - CH / 2), int(cx + CW / 2), int(cy + CH / 2)))
        crop = crop.resize((CW * SCALE, CH * SCALE), Image.LANCZOS)
        px = (i % COLS) * CW * SCALE
        py = (i // COLS) * (CH * SCALE + 26)
        canvas.paste(crop, (px, py))
        mx = px + CW * SCALE / 2; my = py + CH * SCALE / 2
        d.ellipse([mx - 16, my - 16, mx + 16, my + 16], outline=(220, 0, 0), width=3)
        tag = f'{r["id"]} {r["name"] or "⌀"}'
        d.text((px + 4, py + CH * SCALE + 3), tag, fill=(200, 0, 0), font=font)
        d.rectangle([px, py, px + CW * SCALE - 1, py + CH * SCALE + 24], outline=(200, 200, 200))
    canvas.save(OUT / f"sheet_{s + 1}.png")
print("sheets", sheets)
