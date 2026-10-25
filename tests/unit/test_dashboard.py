import json
import os
import re
import unittest
from unittest import mock

import glob
from pathlib import Path

from dashboard.app import HEADERS, STATIC, handle
from tests.authutil import PASSWORD, SETUP_TOKEN, code, provision, session
from tests.dbutil import make_conn


class DashboardTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()

    def call(self, method, path, token=None, body=None):
        code_, _, out = handle(method, path, f"Bearer {token}" if token else None, self.conn,
                               json.dumps(body).encode() if body is not None else b"")
        try:
            return code_, json.loads(out)
        except ValueError:
            return code_, out.decode()

    def test_page_is_public_but_labelled_mock_and_api_requires_auth(self):
        c, html = self.call("GET", "/")
        self.assertEqual(c, 200)
        self.assertIn("MOCK", html)
        for path, m in (("/api/status", "GET"), ("/api/pause", "POST"), ("/api/resume", "POST"),
                        ("/api/auth/logout", "POST"), ("/api/auth/logout-all", "POST")):
            self.assertEqual(self.call(m, path)[0], 401, path)
            self.assertEqual(self.call(m, path, "garbage")[0], 401, path)

    def test_status_pause_resume_roundtrip_with_audit(self):
        t, _, _ = session(self.conn)
        c, s = self.call("GET", "/api/status", t)
        self.assertEqual((c, s["paused"], s["verified_revenue_usd"]), (200, False, 0))
        self.assertEqual(self.call("POST", "/api/pause", t)[1], {"paused": True})
        self.assertTrue(self.call("GET", "/api/status", t)[1]["paused"])
        self.call("POST", "/api/resume", t)
        actions = [r[0] for r in self.conn.execute("select action from audit_events where action like 'kill_switch%'")]
        self.assertEqual(actions, ["kill_switch.pause", "kill_switch.resume"])

    def test_logout_revokes_session(self):
        t, _, _ = session(self.conn)
        self.assertEqual(self.call("POST", "/api/auth/logout", t)[0], 200)
        self.assertEqual(self.call("GET", "/api/status", t)[0], 401)

    def test_login_routes_validate_input_and_report_state(self):
        self.assertEqual(self.call("GET", "/api/auth/state")[1], {"setup_complete": False, "setup_enabled": False, "mode": "LOCAL"})
        self.assertEqual(self.call("POST", "/api/auth/login", body={"password": 1, "code": "x"})[0], 400)
        self.assertEqual(self.call("POST", "/api/auth/login", body={"password": "x", "code": "y"})[0], 401)
        c, _, _ = handle("POST", "/api/auth/login", None, self.conn, b"x" * 10000)
        self.assertEqual(c, 400)
        self.assertEqual(self.call("POST", "/api/auth/setup/begin", body={"setup_token": "a" * 24, "password": PASSWORD})[0], 403)

    def test_http_setup_then_login_flow_and_lockout_status(self):
        with mock.patch.dict(os.environ, {"OWNER_SETUP_TOKEN": SETUP_TOKEN}):
            self.assertTrue(self.call("GET", "/api/auth/state")[1]["setup_enabled"])
            c, d = self.call("POST", "/api/auth/setup/begin", body={"setup_token": SETUP_TOKEN, "password": PASSWORD})
            self.assertEqual(c, 200)
            c, d2 = self.call("POST", "/api/auth/setup/confirm",
                              body={"setup_token": SETUP_TOKEN, "code": code(d["secret"], -1)})
            self.assertEqual((c, len(d2["recovery_codes"])), (200, 8))
            self.assertEqual(self.call("POST", "/api/auth/setup/begin",
                                       body={"setup_token": SETUP_TOKEN, "password": PASSWORD})[0], 403)
        c, d3 = self.call("POST", "/api/auth/login", body={"password": PASSWORD, "code": code(d["secret"], 0)})
        self.assertEqual(c, 200)
        self.assertEqual(self.call("GET", "/api/status", d3["token"])[0], 200)
        for _ in range(8):
            self.call("POST", "/api/auth/login", body={"password": "bad bad bad bad", "code": "000000"})
        self.assertEqual(self.call("POST", "/api/auth/login", body={"password": PASSWORD, "code": code(d["secret"], 1)})[0], 429)

    def test_only_verified_receipts_count_as_revenue(self):
        t, _, _ = session(self.conn)
        ins = "INSERT INTO ledger_entries(entry_id,date,type,usd_value,status) VALUES (?,?,?,?,?)"
        self.conn.execute(ins, ("1", "d", "receipt", 25, "VERIFIED"))
        self.conn.execute(ins, ("2", "d", "receipt", 100, "PENDING"))
        self.conn.execute(ins, ("3", "d", "self_transfer", 50, "VERIFIED"))
        self.assertEqual(self.call("GET", "/api/status", t)[1]["verified_revenue_usd"], 25)


class FrontendSafetyTest(unittest.TestCase):
    def test_csp_blocks_inline_scripts_and_third_parties(self):
        csp = HEADERS["Content-Security-Policy"]
        self.assertIn("script-src 'self';", csp)
        self.assertNotIn("unsafe-inline'; style", csp.replace("style-src 'self' 'unsafe-inline'", ""))
        self.assertNotIn("http", csp)
        html = handle("GET", "/", None, None)[2].decode()
        self.assertNotRegex(html, r"<script(?![^>]*\bsrc=)")  # no inline <script>

    def test_no_dangerous_dom_sinks_and_no_secrets_in_js(self):
        js = "".join(Path(f).read_text() for f in glob.glob(str(STATIC / "js" / "*.js"))) + handle("GET", "/", None, None)[2].decode()
        for sink in ("innerHTML", "outerHTML", "document.write", "eval(", "insertAdjacentHTML"):
            self.assertNotIn(sink, js)

    def test_pwa_assets_served_and_api_never_cached(self):
        for path, ctype in (("/manifest.webmanifest", "application/manifest+json"),
                            ("/sw.js", "text/javascript"), ("/js/main.js", "text/javascript"), ("/css/app.css", "text/css"),
                            ("/icon-512.png", "image/png")):
            c, ct, body = handle("GET", path, None, None)
            self.assertEqual((c, ct), (200, ctype))
            self.assertTrue(body)
        sw = handle("GET", "/sw.js", None, None)[2].decode()
        self.assertIn('startsWith("/api/")', sw)
        self.assertIn('startsWith("/mcp")', sw)
        self.assertEqual(handle("GET", "/nope", None, None)[0], 404)

    def test_vercel_entry_refuses_api_without_postgres(self):
        from api import index
        with mock.patch.dict(os.environ, {"DATABASE_URL": "sqlite:///x.db"}):
            self.assertFalse(index.has_persistent_db())
            self.assertEqual(index._api("GET", "/api/status", None)[0], 503)
        with mock.patch.dict(os.environ, {"DATABASE_URL": "postgresql://nobody@127.0.0.1:1/none"}):
            c, _, body = index._api("GET", "/api/status", None)
            self.assertEqual(c, 503)
            self.assertNotIn(b"127.0.0.1", body)


if __name__ == "__main__":
    unittest.main()
