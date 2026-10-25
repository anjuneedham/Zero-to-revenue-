"""End-to-end: real HTTP server -> Vercel handler -> real Postgres, owner token required."""

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
from core.auth.firebase_auth import OwnerAuth
from tests import dbutil
from tests.unit.test_phase1 import AuthTest, OWNER, PROJECT


class VercelEntryTest(AuthTest):
    def setUp(self):
        dbutil.require_db()
        self.schema = "t_" + uuid.uuid4().hex[:10]
        admin = db.connect(dbutil.URL)
        admin.execute(f'CREATE SCHEMA "{self.schema}"')
        dbutil._schemas.append(self.schema)
        # search_path via libpq options so every per-request connection uses the test schema
        sep = "&" if "?" in dbutil.URL else "?"
        url = f"{dbutil.URL}{sep}options=-csearch_path%3D{self.schema}"
        self.env = mock.patch.dict(os.environ, {"DATABASE_URL": url})
        self.env.start()
        from api import index
        index._migrated = False
        index.auth = OwnerAuth(PROJECT, OWNER, cert_fetcher=lambda: self.certs)
        self.srv = HTTPServer(("127.0.0.1", 0), index.handler)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.srv.server_port}"

    def tearDown(self):
        self.srv.shutdown()
        self.env.stop()

    def call(self, method, path, token=None):
        req = urllib.request.Request(self.base + path, method=method, data=b"" if method == "POST" else None)
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def test_full_flow(self):
        self.assertEqual(self.call("GET", "/api/status")[0], 401)
        self.assertEqual(self.call("GET", "/api/status", self.token(email="evil@example.com"))[0], 401)
        t = self.token()
        code, s = self.call("GET", "/api/status", t)
        self.assertEqual((code, s["paused"]), (200, False))
        self.assertEqual(self.call("POST", "/api/pause", t)[1], {"paused": True})
        # state persists across requests (each request = a fresh DB connection)
        self.assertTrue(self.call("GET", "/api/status", t)[1]["paused"])
        self.call("POST", "/api/resume", t)
        self.assertFalse(self.call("GET", "/api/status", t)[1]["paused"])


del AuthTest
if __name__ == "__main__":
    unittest.main()
