# -*- coding: utf-8 -*-
"""给河网折线算"上游汇流长度"，据此定线宽（主干粗、支流细）。

做法：把折线端点按 4px 网格吸附成图节点，边权=折线长度。
从"河口"（离海岸线最近、且在图上没被包住的端点）沿图做 BFS 求图距离，
按距离从大到小（远=上游）累加上游长度：
    acc[v] = Σ_{u->v} (acc[u] + len(u,v))
线宽 = clamp(1.4 + 1.05*log10(1 + acc/220), 1.4, 11)

输入 data/map/vector/rivers.json + coast.json -> 输出 rivers_w.json:
  [[width, x1,y1,x2,y2, ...], ...]
"""
import json
import math
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VEC = ROOT / "data" / "map" / "vector"
GRID = 4

rivers = json.loads((VEC / "rivers.json").read_text(encoding="utf-8"))
coast = json.loads((VEC / "coast.json").read_text(encoding="utf-8"))


def snap(p):
    return (round(p[0] / GRID), round(p[1] / GRID))


# 海岸线栅格，用于找河口
coast_pts = []
for line in coast["lines"]:
    coast_pts.extend(line)
CS = 60  # 海岸格网
coast_cells = set((int(x // CS), int(y // CS)) for x, y in coast_pts)


def near_coast(x, y, rad=2):
    cx, cy = int(x // CS), int(y // CS)
    for dx in range(-rad, rad + 1):
        for dy in range(-rad, rad + 1):
            if (cx + dx, cy + dy) in coast_cells:
                return True
    return False


# 建图
edges = []
deg = defaultdict(int)
vpos = {}
for i, pts in enumerate(rivers):
    if len(pts) < 2:
        continue
    a, b = snap(pts[0]), snap(pts[-1])
    if a == b:
        continue
    length = 0.0
    for k in range(len(pts) - 1):
        length += math.hypot(pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1])
    vpos[a] = (pts[0][0], pts[0][1])
    vpos[b] = (pts[-1][0], pts[-1][1])
    edges.append((a, b, length, i))
    deg[a] += 1
    deg[b] += 1

print(f"边 {len(edges)}  点 {len(vpos)}")

adj = defaultdict(list)
for ei, (a, b, L, i) in enumerate(edges):
    adj[a].append((b, ei))
    adj[b].append((a, ei))

# 河口 = 端点贴近海岸，或度为 1 且在图边缘
mouths = []
for v in vpos:
    x, y = vpos[v]
    if near_coast(x, y):
        mouths.append(v)
if not mouths:
    mouths = [v for v in vpos if deg[v] == 1]
print(f"河口 {len(mouths)}")

# 图距离（从河口向上游）
dist = {}
q = deque()
for m in mouths:
    dist[m] = 0.0
    q.append(m)
while q:
    v = q.popleft()
    for w, ei in adj[v]:
        nd = dist[v] + edges[ei][2]
        if w not in dist or nd < dist[w] - 1e-6:
            dist[w] = nd
            q.append(w)
# 没连上的岛屿状河网
for v in vpos:
    dist.setdefault(v, 0.0)

# 按图距离降序（上游优先）累加
order = sorted(dist.items(), key=lambda t: -t[1])
acc = defaultdict(float)
incoming = defaultdict(list)
for a, b, L, i in edges:
    if dist[a] > dist[b]:
        incoming[b].append((a, L))
    elif dist[b] > dist[a]:
        incoming[a].append((b, L))
    else:
        incoming[b].append((a, L))

for v, d in order:
    for u, L in incoming[v]:
        acc[v] = max(acc[v], acc[u] + L)
    if not incoming[v]:
        acc[v] = 0.0

out = []
for a, b, L, i in edges:
    up = max(acc[a], acc[b])
    width = 1.4 + 1.05 * math.log10(1 + up / 220.0)
    width = max(1.4, min(11.0, width))
    pts = rivers[i]
    out.append([round(width, 2)] + [round(c, 1) for xy in pts for c in xy])

(VEC / "rivers_w.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
ws = [e[0] for e in out]
print(f"线宽范围 {min(ws):.1f}–{max(ws):.1f}，输出 {len(out)} 条，{(VEC/'rivers_w.json').stat().st_size/1024:.0f} KB")
