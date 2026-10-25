"""End-to-end: real HTTP server -> Vercel handler -> real Postgres -> setup, login, kill switch."""

import json
import os
import threading
import unittest
import urllib.error
import urllib.request
import uuid
from http.server import HTTPServer
from unittest import mock

from core import db
from tests import dbutil
from tests.authutil import PASSWORD, SETUP_TOKEN, code


class VercelEntryTest(unittest.TestCase):
    def setUp(self):
        dbutil.require_db()
        self.schema = "t_" + uuid.uuid4().hex[:10]
        admin = db.connect(dbutil.URL)
        admin.execute(f'CREATE SCHEMA "{self.schema}"')
        dbutil._schemas.append(self.schema)
        sep = "&" if "?" in dbutil.URL else "?"
        url = f"{dbutil.URL}{sep}options=-csearch_path%3D{self.schema}"
        self.env = mock.patch.dict(os.environ, {"DATABASE_URL": url, "OWNER_SETUP_TOKEN": SETUP_TOKEN})
        self.env.start()
        from api import index
        index._migrated = False
        self.srv = HTTPServer(("127.0.0.1", 0), index.handler)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.srv.server_port}"

    def tearDown(self):
        self.srv.shutdown()
        self.env.stop()

    def call(self, method, path, token=None, body=None):
        req = urllib.request.Request(self.base + path, method=method,
                                     data=json.dumps(body).encode() if body is not None else (b"" if method == "POST" else None))
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def test_full_flow(self):
        self.assertEqual(self.call("GET", "/api/status")[0], 401)
        self.assertEqual(self.call("GET", "/api/auth/state")[1], {"setup_complete": False, "setup_enabled": True})
        c, d = self.call("POST", "/api/auth/setup/begin", body={"setup_token": SETUP_TOKEN, "password": PASSWORD})
        self.assertEqual(c, 200)
        self.assertEqual(self.call("POST", "/api/auth/setup/confirm",
                                   body={"setup_token": SETUP_TOKEN, "code": code(d["secret"], -1)})[0], 200)
        self.assertEqual(self.call("POST", "/api/auth/login", body={"password": PASSWORD, "code": "000000"})[0], 401)
        c, s = self.call("POST", "/api/auth/login", body={"password": PASSWORD, "code": code(d["secret"], 0)})
        self.assertEqual(c, 200)
        t = s["token"]
        self.assertEqual(self.call("GET", "/api/status", t)[1]["paused"], False)
        self.assertEqual(self.call("POST", "/api/pause", t)[1], {"paused": True})
        # state + session persist across requests (each request = fresh DB connection)
        self.assertTrue(self.call("GET", "/api/status", t)[1]["paused"])
        self.call("POST", "/api/resume", t)
        self.assertFalse(self.call("GET", "/api/status", t)[1]["paused"])
        self.call("POST", "/api/auth/logout-all", t)
        self.assertEqual(self.call("GET", "/api/status", t)[0], 401)


if __name__ == "__main__":
    unittest.main()
