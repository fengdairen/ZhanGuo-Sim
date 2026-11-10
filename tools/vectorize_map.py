# -*- coding: utf-8 -*-
"""把三张参考位图矢量化成画布坐标下的折线/多边形。

输入（全部 9101x8509 全画布，偏移 0,0）：
  底图河道湖泊.png   红(255,0,0)=河 蓝(0,42,255)=湖 棕(101,55,0)=边界
  底图海岸线.png     黑=海岸线
  ditu.png           仅用于取海面色块（导出海的多边形）

输出：data/map/vector/*.json（坐标单位=画布像素，y 向下）
  rivers.json   [[x,y,...], ...]  折线
  lakes.json    [[x,y,...], ...]  闭合多边形
  borders.json  [[x,y,...], ...]
  coast.json    {"lines":[...], "sea":[...], "islands":[...]}

算法：1/2 尺度做掩膜 -> Zhang-Suen 细化成 1px 骨架 -> 8 邻接图走线 ->
      拆成端点/交点之间的折线 -> 去毛刺 -> Ramer-Douglas-Peucker 简化。
湖泊特殊处理：每个湖都被一圈红线包着（那是湖岸，不是河），
      所以先把蓝块膨胀后覆盖的红像素剔掉，湖岸改由湖多边形自己的描边负责。
"""
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

S = 2
W, H = 9101, 8509
W2, H2 = W // S, H // S
ROOT = Path(__file__).resolve().parent.parent
OUTDIR = ROOT / "data" / "map" / "vector"
REPORT = ROOT / "tools" / "_vec_report.txt"
log_lines = []


def log(m):
    log_lines.append(str(m))


# ---------------- 基础 ----------------
def load_rgb(path):
    return np.array(Image.open(ROOT / path).convert("RGB")).astype(np.int16)


def pool(mask):
    h, w = mask.shape
    h2, w2 = h // S, w // S
    return mask[:h2 * S, :w2 * S].reshape(h2, S, w2, S).max(axis=(1, 3))


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


print("读取位图 ...")
riv = load_rgb("底图河道湖泊.png")
red_full = (riv[..., 0] > 200) & (riv[..., 1] < 80) & (riv[..., 2] < 80)
blue_full = (riv[..., 2] > 200) & (riv[..., 0] < 80) & (riv[..., 1] < 80)
brown_full = (np.abs(riv[..., 0] - 101) <= 30) & (np.abs(riv[..., 1] - 55) <= 30) & (riv[..., 2] <= 45)
del riv
coast_rgb = load_rgb("底图海岸线.png")
coast_full = (coast_rgb.max(axis=2) < 60)
del coast_rgb
ditu = load_rgb("ditu.png")
water_full = (
    (np.abs(ditu[..., 0] - 199) <= 5)
    & (np.abs(ditu[..., 1] - 154) <= 5)
    & (np.abs(ditu[..., 2] - 102) <= 5)
)
del ditu

red = pool(red_full)
blue = pool(blue_full)
brown = pool(brown_full)
coast = pool(coast_full)
sea = pool(water_full)
del red_full, blue_full, brown_full, coast_full, water_full
log(f"掩膜(1/{S}): 河 {int(red.sum())}  湖 {int(blue.sum())}  边界 {int(brown.sum())}  海岸 {int(coast.sum())}  海 {int(sea.sum())}")


# ---------------- 细化 ----------------
def thin(img, max_iter=40):
    p = img.copy()
    for it in range(max_iter):
        changed = False
        for step in (0, 1):
            pad = np.pad(p, 1)
            p2 = pad[:-2, 1:-1]
            p3 = pad[:-2, 2:]
            p4 = pad[1:-1, 2:]
            p5 = pad[2:, 2:]
            p6 = pad[2:, 1:-1]
            p7 = pad[2:, :-2]
            p8 = pad[1:-1, :-2]
            p9 = pad[:-2, :-2]
            B = (p2.astype(np.uint8) + p3 + p4 + p5 + p6 + p7 + p8 + p9)
            seq = (p2, p3, p4, p5, p6, p7, p8, p9, p2)
            A = np.zeros_like(B)
            for k in range(8):
                A += ((~seq[k]) & seq[k + 1]).astype(np.uint8)
            if step == 0:
                c1 = ~(p2 & p4 & p6)
                c2 = ~(p4 & p6 & p8)
            else:
                c1 = ~(p2 & p4 & p8)
                c2 = ~(p2 & p6 & p8)
            rem = p & (B >= 2) & (B <= 6) & (A == 1) & c1 & c2
            if rem.any():
                p &= ~rem
                changed = True
        if not changed:
            break
    return p


# ---------------- 走线 ----------------
def trace_skeleton(sk):
    """返回 [(点列表, 是否闭合)]，点仍是 1/S 网格坐标 (x,y)。"""
    idx = np.flatnonzero(sk.ravel()).tolist()
    ptset = set(idx)
    adj = {}
    for i in idx:
        y, x = divmod(i, W2)
        nb = []
        for dy in (-1, 0, 1):
            yy = y + dy
            if yy < 0 or yy >= H2:
                continue
            base = yy * W2
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                xx = x + dx
                if 0 <= xx < W2:
                    j = base + xx
                    if j in ptset:
                        nb.append(j)
        adj[i] = nb
    deg = {i: len(v) for i, v in adj.items()}
    nodes = {i for i in idx if deg[i] != 2}
    used = set()
    paths = []

    def key(a, b):
        return (a, b) if a < b else (b, a)

    for n in nodes:
        for m in adj[n]:
            if key(n, m) in used:
                continue
            used.add(key(n, m))
            path = [n, m]
            prev, cur = n, m
            while cur not in nodes:
                nxt = [k for k in adj[cur] if k != prev]
                if not nxt:
                    break
                n2 = nxt[0]
                used.add(key(cur, n2))
                path.append(n2)
                prev, cur = cur, n2
            paths.append((path, False))

    # 纯环
    for i in idx:
        if deg[i] != 2:
            continue
        for m in adj[i]:
            if key(i, m) in used:
                continue
            used.add(key(i, m))
            path = [i, m]
            prev, cur = i, m
            while True:
                nxt = [k for k in adj[cur] if k != prev]
                if not nxt:
                    break
                n2 = nxt[0]
                if n2 == i:
                    used.add(key(cur, n2))
                    path.append(n2)
                    break
                if key(cur, n2) in used:
                    break
                used.add(key(cur, n2))
                path.append(n2)
                prev, cur = cur, n2
            paths.append((path, True))

    out = []
    for path, closed in paths:
        xy = [(int(p % W2) * S, int(p // W2) * S) for p in path]
        out.append((xy, closed))
    return out


def rdp(points, eps):
    if len(points) < 3:
        return points
    keep = np.zeros(len(points), dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    pts = np.asarray(points, dtype=np.float64)
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        seg = pts[b] - pts[a]
        ln = math.hypot(seg[0], seg[1])
        sub = pts[a + 1:b]
        if ln < 1e-9:
            d = np.hypot(sub[:, 0] - pts[a][0], sub[:, 1] - pts[a][1])
        else:
            d = np.abs(seg[0] * (sub[:, 1] - pts[a][1]) - seg[1] * (sub[:, 0] - pts[a][0])) / ln
        k = int(np.argmax(d))
        if d[k] > eps:
            keep[a + 1 + k] = True
            stack.append((a, a + 1 + k))
            stack.append((a + 1 + k, b))
    return [points[i] for i in range(len(points)) if keep[i]]


def prune(paths, min_len):
    out = []
    for xy, closed in paths:
        if not closed and len(xy) < 2:
            continue
        L = sum(math.hypot(xy[i + 1][0] - xy[i][0], xy[i + 1][1] - xy[i][1]) for i in range(len(xy) - 1))
        if L >= min_len:
            out.append((xy, closed))
    return out


# ---------------- 湖岸特殊处理 ----------------
# 湖被红线圈着：把蓝块膨胀后覆盖的红像素去掉，湖岸交给湖多边形描边
blue_big = dilate(blue, 3)
red_clean = red & ~blue_big
log(f"剔除湖岸红线: 河 {int(red.sum())} -> {int(red_clean.sum())}")

print("细化河网 ...")
riv_sk = thin(red_clean)
print("细化边界 ...")
bor_sk = thin(brown)
print("细化海岸 ...")
coa_sk = thin(coast)
log(f"骨架像素: 河 {int(riv_sk.sum())}  边界 {int(bor_sk.sum())}  海岸 {int(coa_sk.sum())}")

print("走线 ...")
riv_paths = prune(trace_skeleton(riv_sk), 24)
bor_paths = prune(trace_skeleton(bor_sk), 40)
coa_paths = prune(trace_skeleton(coa_sk), 40)
log(f"折线数: 河 {len(riv_paths)}  边界 {len(bor_paths)}  海岸 {len(coa_paths)}")
import statistics as _st
for _n,_ps in (("河",riv_paths),("边界",bor_paths),("海岸",coa_paths)):
    _l=[len(_p) for _p,_c in _ps]
    log(f"    {_n} 每段点数 中位{int(_st.median(_l))} 最大{max(_l)} 最小{min(_l)}")


def simplify(paths, eps, closed_by_flag=False):
    out = []
    for xy, closed in paths:
        if closed:
            simp = rdp(xy, eps)
        else:
            simp = rdp(xy, eps)
        if len(simp) >= 2:
            out.append(simp)
    return out


rivers = simplify(riv_paths, 2.2)
borders = simplify(bor_paths, 2.5)
coast_lines = simplify(coa_paths, 1.8)
log(f"简化后点数: 河 {sum(len(p) for p in rivers)}  边界 {sum(len(p) for p in borders)}  海岸 {sum(len(p) for p in coast_lines)}")


# ---------------- 湖泊多边形 ----------------
def label_runs(mask):
    Hh, Ww = mask.shape
    runs = []
    span = []
    for y in range(Hh):
        row = mask[y]
        if not row.any():
            span.append((len(runs), len(runs)))
            continue
        d = np.diff(np.concatenate(([0], row.view(np.int8), [0])))
        st = np.flatnonzero(d == 1)
        en = np.flatnonzero(d == -1) - 1
        b = len(runs)
        span.append((b, b + len(st)))
        for x0, x1 in zip(st.tolist(), en.tolist()):
            runs.append((y, x0, x1))
    par = list(range(len(runs)))

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    for y in range(1, Hh):
        a0, a1 = span[y - 1]
        b0, b1 = span[y]
        i, j = a0, b0
        while i < a1 and j < b1:
            _, ax0, ax1 = runs[i]
            _, bx0, bx1 = runs[j]
            if ax0 - 1 <= bx1 and bx0 - 1 <= ax1:
                ra, rb = find(i), find(j)
                if ra != rb:
                    par[rb] = ra
            if ax1 < bx1:
                i += 1
            else:
                j += 1
    return runs, find


def comp_masks(mask, min_area):
    runs, find = label_runs(mask)
    groups = {}
    for k, (y, x0, x1) in enumerate(runs):
        r = find(k)
        groups.setdefault(r, []).append((y, x0, x1))
    out = []
    for r, rs in groups.items():
        area = sum(x1 - x0 + 1 for _, x0, x1 in rs)
        if area >= min_area:
            y0 = min(t[0] for t in rs)
            y1 = max(t[0] for t in rs)
            x0 = min(t[1] for t in rs)
            x1 = max(t[2] for t in rs)
            m = np.zeros((y1 - y0 + 3, x1 - x0 + 3), dtype=bool)
            for y, a, b in rs:
                m[y - y0 + 1, a - x0 + 1:b - x0 + 2] = True
            out.append((m, x0 - 1, y0 - 1, area))
    out.sort(key=lambda t: -t[3])
    return out


def trace_contour(m):
    """Moore 邻域边界跟踪，返回相对坐标点列（m 外圈留 1px 空白）。"""
    ys, xs = np.nonzero(m)
    if len(ys) == 0:
        return []
    sy, sx = ys[0], xs[0]
    start = (sy, sx)
    dirs = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
    contour = [start]
    cur = start
    backtrack = (sy, sx - 1)
    Hh, Ww = m.shape

    def inside(y, x):
        return 0 <= y < Hh and 0 <= x < Ww and m[y, x]

    for _ in range(len(ys) * 8 + 10):
        di = dirs.index((backtrack[0] - cur[0], backtrack[1] - cur[1]))
        found = None
        for k in range(1, 9):
            dy, dx = dirs[(di + k) % 8]
            ny, nx = cur[0] + dy, cur[1] + dx
            if inside(ny, nx):
                found = ((ny, nx), (cur[0] + dirs[(di + k - 1) % 8][0], cur[1] + dirs[(di + k - 1) % 8][1]))
                break
        if found is None:
            break
        nxt, nb = found
        contour.append(nxt)
        backtrack = nb
        cur = nxt
        if cur == start and len(contour) > 3:
            break
    return [(x, y) for y, x in contour]


print("提取湖泊 ...")
lakes = []
for m, ox, oy, area in comp_masks(blue, 40 * S):
    c = trace_contour(m)
    if len(c) < 6:
        continue
    pts = [((x + ox) * S, (y + oy) * S) for x, y in c]
    pts = rdp(pts, 1.8)
    if len(pts) >= 4:
        lakes.append(pts)
log(f"湖泊 {len(lakes)} 个")

# ---------------- 海 ----------------
print("提取海面 ...")
sea_comps = comp_masks(sea, 1000)
sea_out = []
islands = []
for m, ox, oy, area in sea_comps[:1]:
    c = trace_contour(m)
    pts = [((x + ox) * S, (y + oy) * S) for x, y in c]
    pts = rdp(pts, 2.0)
    sea_out.append(pts)
    log(f"海多边形 点数 {len(pts)}  area(1/{S}^2) {area}")

# 岛：海岸线里的闭合环
for xy, closed in coa_paths:
    if closed and len(xy) > 8:
        islands.append(rdp(xy, 1.5))
log(f"岛/闭合环 {len(islands)} 个")

# ---------------- 输出 ----------------
OUTDIR.mkdir(parents=True, exist_ok=True)


def _js(o):
    try:
        return int(o)
    except Exception:
        return float(o)


def dump(name, obj):
    p = OUTDIR / name
    p.write_text(json.dumps(obj, separators=(",", ":"), default=_js), encoding="utf-8")
    log(f"{name}: {p.stat().st_size/1024:.0f} KB")


dump("rivers.json", rivers)
dump("lakes.json", lakes)
dump("borders.json", borders)
dump("coast.json", {"lines": coast_lines, "sea": sea_out, "islands": islands})

REPORT.write_text("\n".join(log_lines), encoding="utf-8")
print("done")
