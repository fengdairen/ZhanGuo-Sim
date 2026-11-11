"""从描迹海岸线推导海面多边形（不再使用位图提取的 sea）。

原理
----
开放岸线的两端都落在图幅边上时，沿"较近的那条图幅边"把两端接起来，
就得到一个闭合多边形：它围住的正是海。闭合环海岸线（岛屿）不参与，
后续单独按陆地填充。

输入  data/map/vector/coast_drawn.json   （rivers_from_editor.py 产出）
输出  data/map/vector/sea_from_coast.json

用法  python tools/build_sea_from_coast.py
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
VEC = ROOT / "data" / "map" / "vector"
CW, CH = 9101, 8509          # 画布尺寸（与描迹器一致）


def load(name):
    p = VEC / name
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def atomic_write(path: pathlib.Path, text: str):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def snap_to_frame(p):
    """把端点吸附到最近的图幅边。"""
    x, y = p
    cands = [
        (abs(y - 0), (x, 0)),
        (abs(y - CH), (x, CH)),
        (abs(x - 0), (0, y)),
        (abs(x - CW), (CW, y)),
    ]
    cands.sort(key=lambda t: t[0])
    return cands[0][1]


def edge_of(p):
    x, y = p
    if abs(y) < 1e-6:
        return 0            # 上边
    if abs(x - CW) < 1e-6:
        return 1            # 右边
    if abs(y - CH) < 1e-6:
        return 2            # 下边
    if abs(x) < 1e-6:
        return 3            # 左边
    return -1


CORNERS = {(0, 1): (CW, 0), (1, 2): (CW, CH), (2, 3): (0, CH), (3, 0): (0, 0)}


def frame_path(p, q):
    """沿图幅边从 p 走到 q，两个方向取较短的那条。"""
    ea, eb = edge_of(p), edge_of(q)
    if ea < 0 or eb < 0:
        return [p, q]
    best = None
    for direction in (1, -1):
        out = [p]
        e = ea
        guard = 0
        while e != eb and guard < 8:
            nxt = (e + direction) % 4
            key = (e, nxt) if direction == 1 else (nxt, e)
            out.append(CORNERS[key])
            e = nxt
            guard += 1
        out.append(q)
        L = sum(((out[i + 1][0] - out[i][0]) ** 2 + (out[i + 1][1] - out[i][1]) ** 2) ** 0.5
                for i in range(len(out) - 1))
        if best is None or L < best[0]:
            best = (L, out)
    return best[1]


def main():
    drawn = load("coast_drawn.json")
    if not drawn:
        print("没有 coast_drawn.json：先跑 tools/rivers_from_editor.py")
        sys.exit(3)

    opens = [c for c in drawn if not c.get("closed")]
    if not opens:
        print("没有开放的岸线，无法推导海面")
        sys.exit(4)
    opens.sort(key=lambda c: -len(c["pts"]))
    c = opens[0]
    pts = [(c["pts"][i], c["pts"][i + 1]) for i in range(0, len(c["pts"]), 2)]

    A = snap_to_frame(pts[0])
    B = snap_to_frame(pts[-1])
    closing = frame_path(B, A)
    poly = list(pts) + closing[1:-1]

    area = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        area += x1 * y2 - x2 * y1
    area = abs(area) / 2

    atomic_write(VEC / "sea_from_coast.json",
                 json.dumps([poly], separators=(",", ":")))

    print(f"OK 海面多边形 {len(poly)} 点，面积 {area:,.0f} 平方像素"
          f"（画幅 {area / (CW * CH):.1%}）→ sea_from_coast.json")


if __name__ == "__main__":
    main()
