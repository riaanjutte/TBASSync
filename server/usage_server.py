"""TBAS Sync usage tracker (stdlib only).

    python3 usage_server.py serve   # HTTP API on 127.0.0.1:5083 (exposed via Tailscale Funnel at /tbassync)
                                    # + dashboard on 127.0.0.1:5084 (tailnet only, via `tailscale serve --https=8445`)
    python3 usage_server.py stats   # print a usage report

Clients POST /tbassync/ping with JSON {"id": <32 hex>, "version": <int>, "event": "launch"|"heartbeat",
"installed": <unix ts>}. One row per device is kept; IP addresses are never stored or logged.
"""
import json
import os
import re
import sqlite3
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DB_PATH = os.environ.get("TBASSYNC_USAGE_DB", "/var/lib/tbassync-usage/usage.db")
HOST, PORT = "127.0.0.1", int(os.environ.get("TBASSYNC_USAGE_PORT", "5083"))
DASHBOARD_PORT = int(os.environ.get("TBASSYNC_DASHBOARD_PORT", "5084"))
EVENTS = {"launch", "heartbeat"}
ID_RE = re.compile(r"^[0-9a-f]{32}$")
MAX_DEVICES = 50_000


def db():
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.execute("""CREATE TABLE IF NOT EXISTS devices (
        id TEXT PRIMARY KEY, version INTEGER, installed INTEGER,
        first_seen INTEGER, last_seen INTEGER, launches INTEGER DEFAULT 0)""")
    return con


def parse(body):
    """Validated (id, version, event, installed) or None."""
    try:
        data = json.loads(body)
        device_id, version, event = data["id"], int(data["version"]), data["event"]
        installed = int(data.get("installed") or 0)
    except (ValueError, KeyError, TypeError):
        return None
    if not (isinstance(device_id, str) and ID_RE.match(device_id) and event in EVENTS and 0 < version < 10_000):
        return None
    now = int(time.time())
    if not 1_600_000_000 <= installed <= now + 86_400:   # missing or nonsense client clock
        installed = None
    return device_id, version, event, installed


def accepts(con, device_id):
    """Known devices always; new ones only below the cap, so random IDs cannot fill the disk."""
    return con.execute("SELECT EXISTS(SELECT 1 FROM devices WHERE id = ?) OR COUNT(*) < ? FROM devices",
                       (device_id, MAX_DEVICES)).fetchone()[0] == 1


def record(con, device_id, version, event, installed, now):
    with con:
        con.execute("""INSERT INTO devices (id, version, installed, first_seen, last_seen, launches)
                       VALUES (?, ?, ?, ?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET version = excluded.version, last_seen = excluded.last_seen,
                           installed = COALESCE(devices.installed, excluded.installed),
                           launches = devices.launches + excluded.launches""",
                    (device_id, version, installed, now, now, 1 if event == "launch" else 0))


class Handler(BaseHTTPRequestHandler):
    timeout = 10   # a client that never sends its body must not hold a thread forever

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        if self.path != "/tbassync/ping" or not 0 < length <= 1024:
            return self._reply(404 if self.path != "/tbassync/ping" else 400)
        parsed = parse(self.rfile.read(length))
        if parsed is None:
            return self._reply(400)
        con = db()
        try:
            if not accepts(con, parsed[0]):
                return self._reply(503)
            record(con, *parsed, int(time.time()))
        finally:
            con.close()
        self._reply(204)

    def do_GET(self):
        self._reply(404)

    def _reply(self, code):
        self.send_response(code)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args):
        pass   # no access log: it would hold client addresses


def stats(con):
    now = int(time.time())
    day = lambda ts: datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d") if ts else "-"
    one = lambda sql, *a: con.execute(sql, a).fetchone()[0]
    print(f"Devices total:        {one('SELECT COUNT(*) FROM devices')}")
    for label, secs in (("Active last 24 h:", 86_400), ("Active last 7 days:", 7 * 86_400), ("Active last 30 days:", 30 * 86_400)):
        print(f"{label:22}{one('SELECT COUNT(*) FROM devices WHERE last_seen >= ?', now - secs)}")
    print("\nVersions (devices active in the last 30 days):")
    for version, n in con.execute("SELECT version, COUNT(*) FROM devices WHERE last_seen >= ? GROUP BY version "
                                  "ORDER BY version DESC", (now - 30 * 86_400,)):
        print(f"  v{version}: {n}")
    print("\nNew devices per week (first seen):")
    for week, n in con.execute("SELECT strftime('%Y-W%W', first_seen, 'unixepoch'), COUNT(*) FROM devices "
                               "GROUP BY 1 ORDER BY 1 DESC LIMIT 8"):
        print(f"  {week}: {n}")
    print(f"\n{'device':10} {'ver':>4} {'installed':10} {'first seen':10} {'last seen':16} {'launches':>8}")
    for d, v, inst, first, last, launches in con.execute(
            "SELECT id, version, installed, first_seen, last_seen, launches FROM devices ORDER BY last_seen DESC"):
        last_s = datetime.fromtimestamp(last, timezone.utc).strftime("%Y-%m-%d %H:%M")
        print(f"{d[:8]:10} {v:>4} {day(inst):10} {day(first):10} {last_s:16} {launches:>8}")


def dashboard_data(con):
    now = int(time.time())
    one = lambda sql, *a: con.execute(sql, a).fetchone()[0]
    active = lambda secs: one("SELECT COUNT(*) FROM devices WHERE last_seen >= ?", now - secs)
    return {
        "now": now,
        "total": one("SELECT COUNT(*) FROM devices"),
        "active": {"day": active(86_400), "week": active(7 * 86_400), "month": active(30 * 86_400)},
        "versions": con.execute("SELECT version, COUNT(*) FROM devices WHERE last_seen >= ? GROUP BY version "
                                "ORDER BY version", (now - 30 * 86_400,)).fetchall(),
        "weeks": con.execute("SELECT date(first_seen, 'unixepoch', 'weekday 1', '-7 days'), COUNT(*) FROM devices "
                             "GROUP BY 1 ORDER BY 1").fetchall(),
        "devices": [dict(zip(("id", "version", "installed", "first_seen", "last_seen", "launches"), row))
                    for row in con.execute("SELECT substr(id, 1, 8), version, installed, first_seen, last_seen, "
                                           "launches FROM devices ORDER BY last_seen DESC LIMIT 500")],
    }


class DashboardHandler(BaseHTTPRequestHandler):
    """Private dashboard: bound to a separate port that only `tailscale serve` (tailnet) exposes,
    so the public Funnel route (/tbassync -> PORT) can never reach it."""
    timeout = 10

    def do_GET(self):
        if self.path == "/":
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.html"), "rb") as f:
                return self._send(f.read(), "text/html; charset=utf-8")
        if self.path == "/data.json":
            con = db()
            try:
                return self._send(json.dumps(dashboard_data(con)).encode(), "application/json")
            finally:
                con.close()
        self._send(b"", "text/plain", 404)

    def _send(self, body, content_type, code=200):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def self_test():
    con = sqlite3.connect(":memory:")
    con.execute("""CREATE TABLE devices (id TEXT PRIMARY KEY, version INTEGER, installed INTEGER,
        first_seen INTEGER, last_seen INTEGER, launches INTEGER DEFAULT 0)""")
    good = json.dumps({"id": "a" * 32, "version": 15, "event": "launch", "installed": 1_700_000_000}).encode()
    assert parse(good) == ("a" * 32, 15, "launch", 1_700_000_000)
    for bad in (b"{", b"[]", json.dumps({"id": "x", "version": 15, "event": "launch"}).encode(),
                json.dumps({"id": "a" * 32, "version": 15, "event": "drop table"}).encode(),
                json.dumps({"id": "a" * 32, "version": "abc", "event": "launch"}).encode()):
        assert parse(bad) is None, bad
    assert parse(json.dumps({"id": "b" * 32, "version": 15, "event": "launch", "installed": 5}).encode())[3] is None
    record(con, "a" * 32, 14, "launch", 1_700_000_000, 1000)
    record(con, "a" * 32, 15, "heartbeat", 1_800_000_000, 2000)
    record(con, "a" * 32, 15, "launch", None, 3000)
    assert con.execute("SELECT version, installed, first_seen, last_seen, launches FROM devices").fetchone() \
        == (15, 1_700_000_000, 1000, 3000, 2)
    global MAX_DEVICES
    MAX_DEVICES = 1   # table now full
    assert accepts(con, "a" * 32) and not accepts(con, "c" * 32)
    MAX_DEVICES = 2
    assert accepts(con, "c" * 32)
    data = dashboard_data(con)
    assert data["total"] == 1 and data["devices"][0]["id"] == "a" * 8 and data["versions"] == []   # last_seen is 1970
    print("self-test OK")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "serve"
    if command == "serve":
        db().close()
        dashboard = ThreadingHTTPServer((HOST, DASHBOARD_PORT), DashboardHandler)
        threading.Thread(target=dashboard.serve_forever, daemon=True).start()
        ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
    elif command == "stats":
        stats(db())
    elif command == "test":
        self_test()
    else:
        sys.exit(__doc__)
