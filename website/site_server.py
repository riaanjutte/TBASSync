"""TBAS squadron page, served at https://hsd-online.net/tbas/ behind HSD's nginx.

Fetches the TBAS skin collection from the HSD API every 10 minutes, keeps the
last good copy in memory as data.js, and serves index.html, the logo and data.js.
Standard library only; runs as an unprivileged user in a read-only container.
"""
import json
import logging
import os
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

COLLECTION_URLS = [
    "http://api:5000/skinsCollections/5",                 # HSD API container, same Docker network
    "https://hsd-online.net/api/skinsCollections/5",      # public fallback
]
PREVIEW_BASE = "https://hsd-online.net/api/skins/files/"
REFRESH_SECONDS = 600
PORT = int(os.environ.get("PORT", "8080"))
HERE = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("tbas-site")

STATIC = {
    "index.html": ("text/html; charset=utf-8", "no-cache"),
    "tbas-logo.png": ("image/png", "public, max-age=86400"),
}
_static_bytes = {name: open(os.path.join(HERE, name), "rb").read() for name in STATIC}
_data_js = b""  # empty until the first successful fetch; the page shows "can't be loaded" meanwhile


def build_skins(collection):
    skins = []
    for s in collection["skins"]:
        previews = (s.get("No_Restricted_Symbols") or {}).get("preview_images") or []
        asset = s.get("game_asset") or {}
        skins.append({
            "id": int(s["id"]),
            "title": s.get("title") or "",
            "aircraft": asset.get("display_name") or "Unknown aircraft",
            "module": asset.get("game_module") or "",
            "painter": s.get("creator") or "Unknown",
            "created": s.get("creation_date"),
            "updated": s.get("last_update") or s.get("creation_date"),
            "downloads": s.get("downloads_count") or 0,
            "img": PREVIEW_BASE + urllib.parse.quote(previews[0]["path"], safe="?=&") if previews else None,
        })
    return skins


def fetch_collection():
    last_error = None
    for url in COLLECTION_URLS:
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return json.load(resp)
        except Exception as e:  # try the next source
            last_error = e
            log.warning("fetch %s failed: %s", url, e)
    raise last_error


def refresh():
    global _data_js
    skins = build_skins(fetch_collection())
    if not skins:
        raise ValueError("collection returned no skins")
    _data_js = ("window.TBAS_SKINS = " + json.dumps(skins, ensure_ascii=False) + ";\n").encode("utf-8")
    log.info("refreshed: %d skins", len(skins))


def refresh_loop():
    while True:
        try:
            refresh()
        except Exception as e:  # keep serving the last good copy
            log.error("refresh failed: %s", e)
        time.sleep(REFRESH_SECONDS)


class Handler(BaseHTTPRequestHandler):
    server_version = "tbas-site"
    sys_version = ""

    def do_GET(self):
        self._serve(send_body=True)

    def do_HEAD(self):
        self._serve(send_body=False)

    def _serve(self, send_body):
        path = urllib.parse.urlsplit(self.path).path
        # nginx proxies the full /tbas/... path
        if path == "/tbas" or path.startswith("/tbas/"):
            path = path[len("/tbas"):]
        name = path.lstrip("/") or "index.html"
        if name == "data.js":
            body, ctype, cache = _data_js, "text/javascript; charset=utf-8", "public, max-age=60"
        elif name in STATIC:
            body = _static_bytes[name]
            ctype, cache = STATIC[name]
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if send_body:
            self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # nginx already logs requests


def self_test():
    sample = {"skins": [
        {"id": "1", "title": "A", "creator": "P", "creation_date": "c", "last_update": "u", "downloads_count": 3,
         "game_asset": {"display_name": "Bf 109 G-6 “Late”", "game_module": "M"},
         "No_Restricted_Symbols": {"preview_images": [{"path": "35803?md5=abc"}]}},
        {"id": "2", "title": "B", "creator": "P", "game_asset": {}},
    ]}
    a, b = build_skins(sample)
    assert a["img"] == PREVIEW_BASE + "35803?md5=abc" and a["aircraft"] == "Bf 109 G-6 “Late”", a
    assert b["img"] is None and b["aircraft"] == "Unknown aircraft" and b["updated"] is None, b


if __name__ == "__main__":
    self_test()
    threading.Thread(target=refresh_loop, daemon=True).start()
    log.info("listening on :%d", PORT)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
