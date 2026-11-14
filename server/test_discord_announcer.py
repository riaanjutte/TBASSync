"""Tests for discord_announcer.py (stdlib only). Run: python3 -m unittest -v test_discord_announcer

A local http.server plays both HSD (GET /collection) and Discord (POST /api/webhooks/...);
the announcer runs as a subprocess, exactly as systemd runs it.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "discord_announcer.py")
SECRET = "test-secret-token"   # stands in for the webhook token; must never appear in output


def skin(i, safe=True, restricted=False):
    s = {"id": i, "title": f"TBAS skin {i}", "creator": f"pilot{i}", "description": "",
         "creation_date": "Sat, 01 Jan 2022 00:00:00 GMT", "last_update": "Sat, 01 Jan 2022 00:00:00 GMT",
         "version_state": "Approved", "game_asset": {"display_name": f"Bf 110 E-{i}", "game_module": "Moscow"}}
    if safe:
        s["No_Restricted_Symbols"] = {"preview_images": [{"path": f"{i}01?md5=safe{i}"}], "dds_files": []}
    if restricted:
        s["Restricted_Symbols"] = {"preview_images": [{"path": f"{i}02?md5=restricted{i}"}], "dds_files": []}
    return s


class Fake(BaseHTTPRequestHandler):
    collection = {}
    codes = []       # status codes to answer webhook POSTs with, in order; then 204
    posts = []       # (payload, user_agent) of every webhook POST received

    def do_GET(self):
        body = json.dumps(Fake.collection).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert self.path == f"/api/webhooks/123/{SECRET}", self.path
        Fake.posts.append((payload, self.headers.get("User-Agent")))
        code = Fake.codes.pop(0) if Fake.codes else 204
        self.send_response(code)
        if code == 429:
            self.send_header("Retry-After", "0")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args):
        pass


class AnnouncerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.state = os.path.join(self.dir, "seen.json")
        Fake.posts, Fake.codes = [], []

    def tearDown(self):
        shutil.rmtree(self.dir)

    def serve(self, skins, count=None):
        Fake.collection = {"id": 5, "skins": skins, "skins_count": len(skins) if count is None else count}

    def seed(self, ids):
        with open(self.state, "w") as f:
            json.dump(ids, f)

    def seen(self):
        with open(self.state) as f:
            return json.load(f)

    def run_job(self, webhook=None):
        env = dict(os.environ, PYTHONIOENCODING="utf-8", TBASSYNC_DISCORD_STATE=self.state,
                   TBASSYNC_DISCORD_COLLECTION=f"{self.base}/collection",
                   DISCORD_WEBHOOK_URL=webhook or f" {self.base}/api/webhooks/123/{SECRET}\r ")
        p = subprocess.run([sys.executable, SCRIPT], env=env, capture_output=True, text=True, timeout=60)
        self.assertNotIn(SECRET, p.stdout + p.stderr)
        return p

    def embeds(self, n):
        return Fake.posts[n][0]["embeds"]

    def test_first_run_seeds_and_posts_nothing(self):
        self.serve([skin(1), skin(2), skin(3)])
        p = self.run_job()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(Fake.posts, [])
        self.assertEqual(self.seen(), [1, 2, 3])

    def test_new_skin_posted_once_with_safe_picture(self):
        self.seed([1, 2])
        self.serve([skin(1), skin(2), skin(3, restricted=True)])
        p = self.run_job()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(len(Fake.posts), 1)
        self.assertEqual(self.embeds(0), [{
            "title": "TBAS skin 3", "url": "https://hsd-online.net/skins/3", "author": {"name": "pilot3"},
            "fields": [{"name": "Aircraft", "value": "Bf 110 E-3", "inline": True}],
            "image": {"url": "https://hsd-online.net/api/skins/files/301?md5=safe3"}}])
        self.assertNotIn("Python-urllib", Fake.posts[0][1])
        self.assertEqual(self.seen(), [1, 2, 3])
        self.assertEqual(self.run_job().returncode, 0)   # rerun
        self.assertEqual(len(Fake.posts), 1)

    def test_discord_500_leaves_skin_unseen_and_next_run_retries(self):
        self.seed([1])
        self.serve([skin(1), skin(2)])
        Fake.codes = [500]
        self.assertEqual(self.run_job().returncode, 1)
        self.assertEqual(self.seen(), [1])
        self.assertEqual(self.run_job().returncode, 0)
        self.assertEqual(len(Fake.posts), 2)
        self.assertEqual(self.embeds(1)[0]["url"], "https://hsd-online.net/skins/2")
        self.assertEqual(self.seen(), [1, 2])

    def test_twelve_new_skins_give_two_messages(self):
        self.seed([1])
        self.serve([skin(i) for i in range(13, 0, -1)])
        self.assertEqual(self.run_job().returncode, 0)
        self.assertEqual([len(p[0]["embeds"]) for p in Fake.posts], [10, 2])
        self.assertEqual([e["url"].rsplit("/", 1)[1] for e in self.embeds(0) + self.embeds(1)],
                         [str(i) for i in range(2, 14)])
        self.assertEqual(self.seen(), list(range(1, 14)))

    def test_cut_off_collection_posts_nothing_and_keeps_state(self):
        self.seed([1])
        self.serve([skin(1), skin(2)], count=3)
        with open(self.state, "rb") as f:
            before = f.read()
        self.assertEqual(self.run_job().returncode, 1)
        self.assertEqual(Fake.posts, [])
        with open(self.state, "rb") as f:
            self.assertEqual(f.read(), before)

    def test_cut_off_collection_on_first_run_does_not_seed(self):
        self.serve([skin(1)], count=2)
        self.assertEqual(self.run_job().returncode, 1)
        self.assertFalse(os.path.exists(self.state))

    def test_skin_without_safe_preview_posted_without_picture(self):
        self.seed([1])
        self.serve([skin(1), skin(2, safe=False, restricted=True)])
        self.assertEqual(self.run_job().returncode, 0)
        self.assertNotIn("image", self.embeds(0)[0])
        self.assertNotIn("restricted", json.dumps(Fake.posts))
        self.assertEqual(self.seen(), [1, 2])

    def test_429_is_retried_once(self):
        self.seed([1])
        self.serve([skin(1), skin(2)])
        Fake.codes = [429]
        self.assertEqual(self.run_job().returncode, 0)
        self.assertEqual(len(Fake.posts), 2)
        self.assertEqual(self.seen(), [1, 2])

    def test_second_429_gives_up_and_leaves_skin_unseen(self):
        self.seed([1])
        self.serve([skin(1), skin(2)])
        Fake.codes = [429, 429]
        self.assertEqual(self.run_job().returncode, 1)
        self.assertEqual(len(Fake.posts), 2)
        self.assertEqual(self.seen(), [1])

    def test_skin_that_leaves_and_returns_is_not_reposted(self):
        self.seed([1, 2])
        self.serve([skin(1)])
        self.assertEqual(self.run_job().returncode, 0)
        self.assertEqual(self.seen(), [1, 2])
        self.serve([skin(1), skin(2)])
        self.assertEqual(self.run_job().returncode, 0)
        self.assertEqual(Fake.posts, [])

    def test_corrupt_state_file_posts_nothing(self):
        with open(self.state, "w") as f:
            f.write("[1, 2")
        self.serve([skin(1), skin(2), skin(3)])
        self.assertNotEqual(self.run_job().returncode, 0)
        self.assertEqual(Fake.posts, [])

    def test_bad_webhook_url_is_not_logged(self):
        self.seed([1])
        self.serve([skin(1), skin(2)])
        for bad in (f"nonsense://{SECRET}", f"example.invalid/api/webhooks/123/{SECRET}"):
            p = self.run_job(webhook=bad)   # run_job asserts SECRET is not in the output
            self.assertEqual(p.returncode, 1)
            self.assertIn("Discord post failed", p.stderr)
        self.assertEqual(self.seen(), [1])


if __name__ == "__main__":
    unittest.main()
