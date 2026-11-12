"""大云梦泽 = (1 ∪ 2) − 陆地。

三个环的关系（实测）：
- 1 与 2 重叠（1 的北岸落在 2 内部）
- 陆地 大部分落在 1 内部 → 是"负片"，要挖掉

做法：栅格化求并集再擦掉陆地，追踪外轮廓与内洞，
然后按"是否与河道重合"切成 手绘 / 河段 交替的 pieces。

产物：tools/_ym_union.json  {pts, pieces, holes}
"""
from __future__ import annotations

import json
import math
import pathlib

from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "map" / "rivers" / "river_segments.json"
OUT = ROOT / "tools" / "_ym_union.json"

POS = ("大云梦泽1", "大云梦泽2")
NEG = "大云梦泽（陆地）"
MARGIN = 6
RDP_EPS = 1.1
RIVER_TOL = 2.4          # 判定"落在河道上"的容差（世界像素）
MIN_RIVER_PTS = 5
MIN_RIVER_LEN = 30.0


def rdp(pts, eps):
    if len(pts) < 3:
        return pts

    def rec(a, b):
        if b - a < 2:
            return []
        ax, ay = pts[a]
        bx, by = pts[b]
        dx, dy = bx - ax, by - ay
        L = math.hypot(dx, dy) or 1e-9
        best, bi = -1, -1
        for i in range(a + 1, b):
            px, py = pts[i]
            dd = abs((px - ax) * dy - (py - ay) * dx) / L
            if dd > best:
                best, bi = dd, i
        if best > eps:
            return rec(a, bi) + [bi] + rec(bi, b)
        return []

    keep = sorted(set([0] + rec(0, len(pts) - 1) + [len(pts) - 1]))
    return [pts[i] for i in keep]


def solid_loader(img, w, h, want=1):
    pix = img.load()
    def f(x, y):
        return 0 <= x < w and 0 <= y < h and (1 if pix[x, y] > 0 else 0) == want
    return f


def trace(is_solid, w, h, start_hint=None):
    """Moore 邻域追踪；is_solid(x,y) 判定"属于要连成环的区域"。"""
    start = start_hint
    if start is None:
        for y in range(h):
            for x in range(w):
                if is_solid(x, y):
                    start = (x, y)
                    break
            if start:
                break
    if not start:
        return []
    dirs = [(-1, 0), (-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1)]
    contour, cur, back = [start], start, 7
    for _ in range(w * h * 4):
        moved = False
        for k in range(8):
            d = (back + 1 + k) % 8
            nx, ny = cur[0] + dirs[d][0], cur[1] + dirs[d][1]
            if is_solid(nx, ny):
                contour.append((nx, ny))
                back = (d + 4) % 8
                cur = (nx, ny)
                moved = True
                break
        if not moved:
            break
        if cur == start and len(contour) > 4:
            break
    return contour


def main():
    d = json.loads(DATA.read_text(encoding="utf-8-sig"))
    lakes = {l["name"]: l for l in d["lakes"]}
    pos = [lakes[n] for n in POS]
    neg = lakes[NEG]

    xs = [p[0] for l in pos + [neg] for p in l["pts"]]
    ys = [p[1] for l in pos + [neg] for p in l["pts"]]
    x0, y0 = math.floor(min(xs)) - MARGIN, math.floor(min(ys)) - MARGIN
    x1, y1 = math.ceil(max(xs)) + MARGIN, math.ceil(max(ys)) + MARGIN
    W, H = x1 - x0 + 1, y1 - y0 + 1

    img = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(img)
    for l in pos:
        dr.polygon([(p[0] - x0, p[1] - y0) for p in l["pts"]], fill=255)
    dr.polygon([(p[0] - x0, p[1] - y0) for p in neg["pts"]], fill=0)

    is_wet = solid_loader(img, W, H, 1)

    outer = trace(is_wet, W, H)
    if not outer:
        raise SystemExit("没有外轮廓")

    # 内洞：未被水覆盖、且不与边界相连的背景块
    seen = [[False] * W for _ in range(H)]
    holes_px = []
    from collections import deque
    for y in range(H):
        for x in range(W):
            if is_wet(x, y) or seen[y][x]:
                continue
            comp, edge, q = [], False, deque([(x, y)])
            seen[y][x] = True
            while q:
                cx, cy = q.popleft()
                comp.append((cx, cy))
                if cx in (0, W - 1) or cy in (0, H - 1):
                    edge = True
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < W and 0 <= ny < H and not seen[ny][nx] and not is_wet(nx, ny):
                        seen[ny][nx] = True
                        q.append((nx, ny))
            if not edge and len(comp) > 20:
                holes_px.append(comp)

    def to_world(contour):
        pts = [(x + x0, y + y0) for x, y in contour]
        if len(pts) > 1 and pts[0] == pts[-1]:
            pts.pop()
        return pts

    river_pts = [(sg["id"], i, q) for sg in d["segments"] for i, q in enumerate(sg["pts"])]

    def tag_and_split(ring, tag_river=True):
        simp = rdp(ring, RDP_EPS)
        n = len(simp)

        def nearest(q):
            best = None
            for sid, i, v in river_pts:
                dd = math.hypot(v[0] - q[0], v[1] - q[1])
                if dd <= RIVER_TOL and (best is None or dd < best[0]):
                    best = (dd, sid, i)
            return best

        if n:
            cut = 0
            # 旋转到 river→free 的交界，避免首尾同类
            prev = nearest(simp[-1]) is not None
            for i in range(n):
                cur = nearest(simp[i]) is not None
                if cur != prev:
                    cut = i
                    break
                prev = cur
            simp = simp[cut:] + simp[:cut]

        tags, refs = [], []
        for q in simp:
            hit = nearest(q) if tag_river else None
            tags.append("river" if hit else "free")
            refs.append((hit[1], hit[2]) if hit else None)

        runs = []
        for q, t, r in zip(simp, tags, refs):
            if runs and runs[-1]["kind"] == t:
                runs[-1]["pts"].append(q)
                runs[-1]["refs"].append(r)
            else:
                runs.append({"kind": t, "pts": [q], "refs": [r]})

        # 太短的河段并入手绘段（栅格噪声）
        def run_len(r):
            return sum(math.hypot(r["pts"][i+1][0]-r["pts"][i][0], r["pts"][i+1][1]-r["pts"][i][1])
                       for i in range(len(r["pts"]) - 1))

        changed = True
        while changed:
            changed = False
            for i, r in enumerate(runs):
                if r["kind"] == "river" and (len(r["pts"]) < MIN_RIVER_PTS or run_len(r) < MIN_RIVER_LEN):
                    r["kind"] = "free"
                    r["refs"] = [None] * len(r["pts"])
                    changed = True
            # 合并相邻同类
            merged = []
            for r in runs:
                if merged and merged[-1]["kind"] == r["kind"]:
                    merged[-1]["pts"] += r["pts"][1:]
                    merged[-1]["refs"] += r["refs"][1:]
                else:
                    merged.append(r)
            if len(merged) > 1 and merged[0]["kind"] == merged[-1]["kind"]:
                merged[0]["pts"] = merged[-1]["pts"][:-1] + merged[0]["pts"]
                merged[0]["refs"] = merged[-1]["refs"][:-1] + merged[0]["refs"]
                merged.pop()
            if len(merged) != len(runs):
                changed = True
            runs = merged

        pieces = []
        for r in runs:
            pts = [[round(p[0], 1), round(p[1], 1)] for p in r["pts"]]
            if r["kind"] == "river" and r["refs"][0] and r["refs"][-1]:
                a, b = r["refs"][0], r["refs"][-1]
                pieces.append({"kind": "river", "from": {"seg": a[0], "idx": a[1]},
                               "to": {"seg": b[0], "idx": b[1]}, "pts": pts})
            else:
                pieces.append({"kind": "free", "pts": pts})
        return simp, pieces

    ring = to_world(outer)
    simp, pieces = tag_and_split(ring)

    holes = []
    for comp in holes_px:
        sub = Image.new("L", (W, H), 0)
        px = sub.load()
        for cxx, cyy in comp:
            px[cxx, cyy] = 255
        hc = trace(lambda x, y: 0 <= x < W and 0 <= y < H and px[x, y] > 0, W, H, comp[0])
        if len(hc) > 8:
            hr = to_world(hc)
            hs, hp = tag_and_split(hr)
            holes.append({"pts": [[round(p[0], 1), round(p[1], 1)] for p in hs], "pieces": hp})

    OUT.write_text(json.dumps({"pts": [[round(p[0], 1), round(p[1], 1)] for p in simp],
                               "pieces": pieces, "holes": holes},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print("外轮廓 %d → %d 点，%d 段：%s" % (len(ring), len(simp), len(pieces),
                                        " / ".join(p["kind"] for p in pieces)))
    print("内洞 %d 个" % len(holes))


if __name__ == "__main__":
    main()
