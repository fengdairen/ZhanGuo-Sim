# -*- coding: utf-8 -*-
"""河流描迹器的本地服务：打开网页 + 自动读写数据文件。

为什么需要它：
  浏览器里用 file:// 打开页面时，File System Access 的「绑定文件」句柄
  **不跨会话保留**，每次重启浏览器都要重新选一次文件。
  本地服务把读写放到进程侧，网页只发 HTTP 请求，从此不用再指定。

接口：
  GET  /api/load   读 data/map/rivers/river_segments.json
  POST /api/save   原子写入（写前留一份时间戳备份，保留最近 30 份）
  GET  /api/ping   探活
  其余路径         按 dist/river-editor/ 提供静态文件

用法：
  python tools/serve_river_editor.py            # 起服务并打印地址
  python tools/serve_river_editor.py --open     # 起服务并自动打开浏览器
  python tools/serve_river_editor.py --port 8765
"""
import argparse
import json
import os
import sys
import threading
import time
import webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "dist"            # 服务整个 dist/，页面才能相对取到 ../map-review/ditu.png
EDITOR = ROOT / "dist" / "river-editor"
DATA = ROOT / "data" / "map" / "rivers" / "river_segments.json"
VEC = ROOT / "data" / "map" / "vector"
CITY_STATE = ROOT / "data" / "map" / "_editor" / "city_state.json"
CITY_BACKUP = ROOT / "data" / "map" / "_editor" / "_backup"
BAKDIR = ROOT / "data" / "map" / "rivers" / "_backup"
KEEP = 30

_last_backup = [0.0]


def atomic_write(path: Path, text: str):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def backup_once_per_minute():
    """同一个分钟内的多次保存只留一份备份，避免刷屏。"""
    now = time.time()
    if now - _last_backup[0] < 60:
        return
    _last_backup[0] = now
    if not DATA.exists():
        return
    BAKDIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    try:
        (BAKDIR / f"river_segments-{stamp}.json").write_bytes(DATA.read_bytes())
    except Exception:
        return
    files = sorted(BAKDIR.glob("river_segments-*.json"))
    for old in files[:-KEEP]:
        try:
            old.unlink()
        except Exception:
            pass


class Server(ThreadingHTTPServer):
    # Windows 下 SO_REUSEADDR 会让第二个实例也能绑上同一端口（于是两个服务并存），
    # 关掉它，重复启动才能被检测到并提示「已在运行」。
    allow_reuse_address = False


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(WEB), **kw)

    def log_message(self, fmt, *args):
        # 只打写盘与错误，静态请求太吵
        if "/api/save" in (self.path or "") or str(args[1] if len(args) > 1 else "").startswith("4"):
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/ping"):
            return self._json({"ok": True, "data": str(DATA)})
        if self.path.startswith("/api/vector"):
            try:
                def load(name, default):
                    f = VEC / name
                    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else default
                return self._json({
                    "sea": [([v for xy in poly for v in xy]
                             if poly and isinstance(poly[0], (list, tuple)) else poly)
                            for poly in load("sea_from_coast.json", [])],
                    "rivers": load("rivers_w.json", []),
                    "lakes": load("lakes_drawn.json", []),
                    "coasts": load("coast_drawn.json", []),
                })
            except Exception as e:
                return self._json({"error": str(e)}, 500)
        if self.path.startswith("/api/map/load"):
            try:
                if not CITY_STATE.exists():
                    return self._json({"state": None})
                return self._json(json.loads(CITY_STATE.read_text(encoding="utf-8-sig")))
            except Exception as e:
                return self._json({"error": str(e)}, 500)
        if self.path.startswith("/api/load"):
            if not DATA.exists():
                return self._json({"version": 3, "canvas": [9101, 8509], "segments": []})
            try:
                return self._json(json.loads(DATA.read_text(encoding="utf-8-sig")))
            except Exception as e:
                return self._json({"error": str(e)}, 500)
        if self.path in ("/", ""):
            self.send_response(302)
            self.send_header("Location", "/index.html")
            self.end_headers()
            return
        # 目录访问补 index
        if self.path.endswith("/"):
            cand = WEB / self.path.lstrip("/") / "index.html"
            if cand.exists():
                self.path = self.path + "index.html"
        if self.path.endswith("/river-editor/"):
            self.path = "/river-editor/river_editor.html"
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/map/save"):
            try:
                n = int(self.headers.get("Content-Length") or 0)
                data = json.loads(self.rfile.read(n).decode("utf-8"))
                if not isinstance(data.get("items"), list):
                    return self._json({"error": "items 必须是数组"}, 400)
                CITY_STATE.parent.mkdir(parents=True, exist_ok=True)
                CITY_BACKUP.mkdir(parents=True, exist_ok=True)
                if CITY_STATE.exists():
                    stamp = time.strftime("%Y%m%d-%H%M%S")
                    dst = CITY_BACKUP / f"city_state-{stamp}.json"
                    if not dst.exists():
                        dst.write_text(CITY_STATE.read_text(encoding="utf-8"), encoding="utf-8")
                    olds = sorted(CITY_BACKUP.glob("city_state-*.json"))
                    for f in olds[:-30]:
                        f.unlink(missing_ok=True)
                atomic_write(CITY_STATE, json.dumps(data, ensure_ascii=False, indent=1))
                return self._json({"ok": True, "items": len(data["items"]),
                                   "at": time.strftime("%H:%M:%S")})
            except Exception as e:
                return self._json({"error": str(e)}, 500)
        if not self.path.startswith("/api/save"):
            return self._json({"error": "not found"}, 404)
        try:
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n).decode("utf-8")
            data = json.loads(raw)
            if not isinstance(data.get("segments"), list):
                return self._json({"error": "segments 必须是数组"}, 400)
            backup_once_per_minute()
            text = json.dumps(data, ensure_ascii=False, indent=1)
            atomic_write(DATA, text)
            segs = len(data["segments"])
            rivers = len({s.get("river") for s in data["segments"]})
            self._json({"ok": True, "bytes": len(text.encode("utf-8")),
                        "segments": segs, "rivers": rivers,
                        "at": time.strftime("%H:%M:%S")})
        except json.JSONDecodeError as e:
            self._json({"error": "JSON 解析失败: %s" % e}, 400)
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--open", action="store_true")
    args = ap.parse_args()

    WEB.mkdir(parents=True, exist_ok=True)
    url = f"http://127.0.0.1:{args.port}/"

    try:
        srv = Server(("127.0.0.1", args.port), Handler)
    except OSError as e:
        # 端口已被占用：多半是已经开着一个描迹器，直接把浏览器指过去就行
        if getattr(e, "errno", None) in (48, 98, 10048):
            print("端口 %d 已被占用，认为描迹器已在运行：%s" % (args.port, url))
            if args.open:
                webbrowser.open(url)
            return
        raise

    print("河流描迹器已启动：", url)
    print("数据文件：", DATA)
    print("关闭窗口即停止服务（或按 Ctrl+C）")
    if args.open:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
