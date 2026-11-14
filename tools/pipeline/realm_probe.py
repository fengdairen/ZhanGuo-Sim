#!/usr/bin/env python3
"""realm_probe.py —— 复现编辑器的地块填充，回答"这个点最后是什么颜色"

用法：
    python tools/pipeline/realm_probe.py 5850 4090
    python tools/pipeline/realm_probe.py 曲阜
    python tools/pipeline/realm_probe.py --list

它会：
1. 读 tools/_probe_faces.json（由 probe_faces.js 生成，含面、洞、认领）
2. 按编辑器的规则排序（面积从大到小）并逐层用 18% 透明度叠加
3. 打印命中的每一层（国家、颜色、面积）以及最终合成色
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "tools" / "_probe_faces.json"
BORDERS = ROOT / "data" / "map" / "borders.json"
NODES = ROOT / "data" / "map" / "nodes.csv"

PALETTE = {
    "lu": "#c0392b", "qi": "#2980b9", "song": "#27ae60", "wei": "#8e44ad",
    "han": "#d35400", "zhao": "#16a085", "qin": "#2c3e50", "yue": "#f39c12",
    "chu": "#e74c3c",
}
BG = (243, 232, 207)          # 纸面底色
ALPHA = 0.18                  # 编辑器 fillStyle 的 '2e'


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def point_in_ring(x, y, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def in_patch(x, y, f):
    if not point_in_ring(x, y, f["ring"]):
        return False
    for h in f.get("holes") or []:
        if point_in_ring(x, y, h):
            return False
    return True


def main():
    if not PROBE.exists():
        print("先跑：node tools/pipeline/probe_faces.js")
        return 1
    data = json.loads(PROBE.read_text(encoding="utf-8"))
    colors = dict(PALETTE)
    borders = json.loads(BORDERS.read_text(encoding="utf-8"))
    for n in borders.get("nations") or []:
        if n.get("color"):
            colors[n["id"]] = n["color"]

    argv = sys.argv[1:]
    if not argv or argv[0] == "--list":
        print(f"面 {len(data['faces'])}")
        for c in sorted(data["claims"], key=lambda c: -c["area"]):
            print(f"  {c['face']:>5}  {c['nation'] or '?':<12} {c['area']:>9,}  {c['faction']}")
        return 0

    # 坐标：数字 或 城名
    if len(argv) >= 2 and all(a.replace(".", "").replace("-", "").isdigit() for a in argv[:2]):
        x, y = float(argv[0]), float(argv[1])
    else:
        name = argv[0]
        x = y = None
        with NODES.open(encoding="utf-8-sig") as fh:
            next(fh)
            for line in fh:
                parts = line.rstrip("\n").split(",")
                if len(parts) > 2 and parts[1] == name:
                    x, y = float(parts[5]), float(parts[6])
                    break
        if x is None:
            print("没找到城：" + name)
            return 1

    # 认领 → 面
    by_id = {f["id"]: f for f in data["faces"]}
    realms = []
    for c in data["claims"]:
        f = by_id.get(c["face"])
        if not f:
            continue
        realms.append({"face": f["id"], "nation": c["nation"], "faction": c["faction"],
                       "area": f["area"], "ring": f["ring"], "holes": f.get("holes") or []})

    realms.sort(key=lambda r: -r["area"])          # 编辑器：大的先画

    r, g, b = BG
    hits = []
    for rl in realms:
        if not in_patch(x, y, rl):
            continue
        cr, cg, cb = hex_rgb(colors.get(rl["nation"], "#7a6248"))
        r = r * (1 - ALPHA) + cr * ALPHA
        g = g * (1 - ALPHA) + cg * ALPHA
        b = b * (1 - ALPHA) + cb * ALPHA
        hits.append(rl)

    print(f"点 ({x:.0f}, {y:.0f}) 命中 {len(hits)} 层")
    for rl in hits:
        print(f"   {rl['face']:>5}  {rl['nation'] or '?':<12} {colors.get(rl['nation'], '#7a6248')}"
              f"  {rl['area']:>9,}  {'有洞' + str(len(rl['holes'])) if rl['holes'] else ''}")
    print(f"最终颜色 rgb({round(r)}, {round(g)}, {round(b)})  = #{round(r):02x}{round(g):02x}{round(b):02x}")

    # --png：把这一带按编辑器的画法渲染成图，肉眼比对
    if "--png" in argv:
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            print("没有 Pillow，跳过出图")
            return 0
        R = 420
        x0, y0, x1, y1 = x - R, y - R, x + R, y + R
        img = Image.new("RGB", (2 * R, 2 * R), BG)
        dr = ImageDraw.Draw(img)
        for rl in realms:
            pts = [(px - x0, py - y0) for px, py in rl["ring"]]
            if len(pts) < 3:
                continue
            col = hex_rgb(colors.get(rl["nation"], "#7a6248"))
            layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            ld.polygon(pts, fill=col + (46,))
            for h in rl.get("holes") or []:
                hp = [(px - x0, py - y0) for px, py in h]
                if len(hp) >= 3:
                    ld.polygon(hp, fill=(0, 0, 0, 0))
            img = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
        dr = ImageDraw.Draw(img)
        dr.ellipse([R - 5, R - 5, R + 5, R + 5], outline=(200, 30, 20), width=3)
        out = ROOT / "tools" / "_probe.png"
        img.save(out)
        print("已出图", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
