#!/usr/bin/env python3
"""make_standalone.py —— 把舆图打成"单文件 HTML"

纹理以 data URI 内嵌，整个舆图只剩一个 .html 文件：
- 双击即可离线打开
- 可以发网盘 / 微信 / 邮箱，对方下载就能看
- 也可以丢到任何静态托管（不会再有子路径、跨域、证书之外的依赖问题）

用法：
    python tools/pipeline/make_standalone.py
产出：
    dist/舆图.html
"""
import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "dist" / "map-vector"
OUT = ROOT / "dist" / "舆图.html"


def main():
    html_path = SRC / "map.html"
    if not html_path.exists():
        print("没有 dist/map-vector/map.html，先跑 重建地图.cmd")
        return 1
    html = html_path.read_text(encoding="utf-8")

    tex = None
    for name, mime in (("mount.webp", "image/webp"), ("mount.png", "image/png")):
        if (SRC / name).exists():
            tex = (SRC / name, mime)
            break

    if tex:
        path, mime = tex
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        uri = "data:%s;base64,%s" % (mime, data)
        before = len(html)
        for ref in ("mount.webp", "mount.png"):
            html = html.replace("MOUNT.src = '%s'" % ref, "MOUNT.src = '%s'" % uri)
        print("内嵌纹理：%s（%.1f MB → base64 %.1f MB）" % (
            path.name, path.stat().st_size / 1024 / 1024, len(uri) / 1024 / 1024))
        if len(html) == before:
            print("警告：没找到 MOUNT.src 引用，纹理未内嵌")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print("单文件已生成 ->", OUT, "%.1f MB" % (OUT.stat().st_size / 1024 / 1024))
    print("双击即可打开；也可直接上传到任意网盘或静态托管")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
