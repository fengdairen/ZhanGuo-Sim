#!/usr/bin/env python3
"""make_site.py —— 把舆图打包成可直接静态托管/分享的目录

产出：dist/site/
    index.html      入口页（说明 + 进入舆图 + 预览图）
    map.html        舆图本体（数据内嵌）
    mount.webp      山地纹理
    preview*.png    预览缩略图（有就拷）

用法：
    python tools/pipeline/make_site.py

上传：把 dist/site 整个目录丢到 Cloudflare Pages / GitHub Pages / 任意静态托管即可。
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "dist" / "map-vector"
DST = ROOT / "dist" / "site"

INDEX = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>战国演义 · 舆图</title>
<style>
  html,body{margin:0;height:100%;background:#54483a;color:#efe2c2;
            font-family:"Songti SC","SimSun",serif}
  .wrap{max-width:960px;margin:0 auto;padding:64px 24px 48px;text-align:center}
  h1{font-size:44px;letter-spacing:12px;margin:0 0 6px;font-weight:700}
  .sub{color:#b8a583;font-size:14px;letter-spacing:3px;margin-bottom:36px}
  .card{background:#f4ead2;color:#3a2b1c;border-radius:14px;padding:28px 30px;
        box-shadow:0 18px 50px rgba(0,0,0,.35);text-align:left}
  .card p{margin:0 0 14px;line-height:1.9;font-size:15px}
  .card b{color:#8b2e1e}
  .btn{display:inline-block;margin-top:8px;padding:13px 34px;border-radius:999px;
       background:#8b2e1e;color:#f7ecd2;text-decoration:none;font-size:17px;
       letter-spacing:4px;transition:.2s}
  .btn:hover{background:#a63a26;transform:translateY(-1px)}
  .shots{display:flex;gap:12px;justify-content:center;margin:30px 0 6px;flex-wrap:wrap}
  .shots img{width:230px;border-radius:10px;box-shadow:0 10px 26px rgba(0,0,0,.4)}
  .foot{margin-top:34px;color:#8a7a5e;font-size:12.5px;letter-spacing:1px}
</style>
</head>
<body>
  <div class="wrap">
    <h1>舆图</h1>
    <div class="sub">战国演义 · 公元前 390 年</div>

    <div class="card">
      <p>这是一张<b>可交互</b>的战国舆图：滚轮缩放、按住拖动平移。</p>
      <p>点击任意疆域，右侧显示该国的城邑（都 / 城 / 邑）、人口与地方势力；
         再点同一国内的地方势力，可单独高亮它横跨的地块。</p>
      <p>底图：1040 座城邑、181 段河流、31 处湖泊，全部为手工描迹。</p>
      <a class="btn" href="map.html">进入舆图</a>
    </div>

    <div class="shots">
      __SHOTS__
    </div>

    <div class="foot">鼠标滚轮缩放 · 按住拖动平移 · 点击看详情</div>
  </div>
</body>
</html>
"""


def main():
    if not (SRC / "map.html").exists():
        print("没有 dist/map-vector/map.html，先跑 重建地图.cmd")
        return 1
    DST.mkdir(parents=True, exist_ok=True)

    # 清掉上次的产物（只删本目录里的东西）
    for f in DST.iterdir():
        if f.is_file():
            f.unlink()

    shutil.copy2(SRC / "map.html", DST / "map.html")

    tex = None
    for name in ("mount.webp", "mount.png"):
        if (SRC / name).exists():
            tex = name
            shutil.copy2(SRC / name, DST / name)
            break
    if tex:
        # 页面里引用的文件名要和实际一致
        html = (DST / "map.html").read_text(encoding="utf-8")
        if tex != "mount.webp":
            html = html.replace("MOUNT.src = 'mount.webp'", "MOUNT.src = '%s'" % tex)
            (DST / "map.html").write_text(html, encoding="utf-8")

    shots = []
    for p in sorted(SRC.glob("preview*.png")):
        shutil.copy2(p, DST / p.name)
        if p.name.startswith("preview-"):
            shots.append('<img src="%s" alt="%s">' % (p.name, p.stem))
    (DST / "index.html").write_text(
        INDEX.replace("__SHOTS__", "\n      ".join(shots)), encoding="utf-8")

    total = sum(f.stat().st_size for f in DST.iterdir() if f.is_file())
    print("打包完成 ->", DST)
    for f in sorted(DST.iterdir()):
        if f.is_file():
            print("   %-22s %7.1f KB" % (f.name, f.stat().st_size / 1024))
    print("   合计 %.1f MB" % (total / 1024 / 1024))
    print("\n下一步：把 dist/site 整个目录上传到静态托管（Cloudflare Pages / GitHub Pages）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
