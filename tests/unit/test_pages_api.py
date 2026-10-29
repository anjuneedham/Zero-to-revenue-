import json
import os
import unittest
from unittest import mock

import dashboard.app as dash
from tests.authutil import session
from tests.dbutil import make_conn
from tests.unit.test_payments import ENV


class StaticTest(unittest.TestCase):
    def test_serves_allowed_assets(self):
        for p, mime in (("/css/fonts.css", "text/css"), ("/fonts/inter.woff2", "font/woff2"), ("/sw.js", "text/javascript"),
                        ("/manifest.webmanifest", "application/manifest+json"), ("/icon-192.png", "image/png")):
            ct, body = dash.static_file(p)
            self.assertEqual(ct, mime)
            self.assertTrue(body)

    def test_blocks_traversal_wrong_types_and_directories(self):
        for p in ("/js/../../core/db.py", "/fonts/../../../etc/passwd", "/css/..%2f..%2fcore/db.py", "/js/", "/js/nope.js",
                  "/core/db.py", "/dashboard/app.py", "/../x", "/data/../app.py", "//etc/passwd", "/fonts/LICENSE.txt"):
            self.assertIsNone(dash.static_file(p), p)
        self.assertEqual(dash.handle("GET", "/js/../../core/db.py", None, None)[0], 404)

    def test_csp_allows_only_self_fonts(self):
        csp = dash.HEADERS["Content-Security-Policy"]
        self.assertIn("font-src 'self'", csp)
        self.assertNotIn("http", csp)
        self.assertIn("script-src 'self';", csp)


class PagesApiTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.env = mock.patch.dict(os.environ, ENV, clear=True)
        self.env.start()
        self.tok, _, _ = session(self.conn)

    def tearDown(self):
        self.env.stop()

    def call(self, method, path, body=None, auth=True):
        c, _, out = dash.handle(method, path, f"Bearer {self.tok}" if auth else None, self.conn,
                                json.dumps(body).encode() if body is not None else b"")
        return c, json.loads(out)

    def test_all_new_endpoints_require_login(self):
        for m, p in (("GET", "/api/payments/overview"), ("GET", "/api/payments"), ("GET", "/api/plan"), ("POST", "/api/plan")):
            self.assertEqual(self.call(m, p, auth=False)[0], 401, p)

    def test_auth_state_reports_local_or_live(self):
        self.assertEqual(self.call("GET", "/api/auth/state", auth=False)[1]["mode"], "LOCAL")
        with mock.patch.dict(os.environ, {"VERCEL": "1"}):
            self.assertEqual(self.call("GET", "/api/auth/state", auth=False)[1]["mode"], "LIVE")

    def test_payments_overview_shows_verified_revenue_and_safety_flags(self):
        d = self.call("GET", "/api/payments/overview")[1]
        self.assertEqual((d["ledger"], d["revenue_usd"], d["paypal"]), ([], 0, False))
        self.assertFalse(d["safety"]["signing"] or d["safety"]["spending"] or d["safety"]["trading"])
        pid = self.call("POST", "/api/payments/manual", {"title": "Annual plan", "amount": "500"})[1]["payment_id"]
        done = {"status": "COMPLETED", "purchase_units": [{"payments": {"captures": [{"amount": {"value": "500", "currency_code": "USD"}}]}}]}
        with mock.patch("core.payments.paypal.get_order", return_value=done):
            self.assertEqual(self.call("POST", f"/api/payments/{pid}/paypal/verify", {"order_id": "ORD1"})[0], 200)
        d = self.call("GET", "/api/payments/overview")[1]
        self.assertEqual((d["revenue_usd"], d["ledger"][0]["status"]), (500.0, "VERIFIED"))
        with mock.patch.dict(os.environ, {"PAYPAL_CLIENT_ID": "a", "PAYPAL_CLIENT_SECRET": "b"}):
            self.assertTrue(self.call("GET", "/api/payments/overview")[1]["paypal"])

    def test_plan_ticks_roundtrip_and_validation(self):
        self.assertEqual(self.call("GET", "/api/plan")[1], {"ticks": {}})
        self.assertIn("storage", self.call("POST", "/api/plan", {"id": "storage", "done": True})[1]["ticks"])
        self.assertIn("storage", self.call("GET", "/api/plan")[1]["ticks"])
        self.assertEqual(self.call("POST", "/api/plan", {"id": "storage", "done": False})[1], {"ticks": {}})
        for bad in ({"id": "Bad Id!", "done": True}, {"id": "x", "done": "yes"}, {"done": True}, {"id": "a" * 61, "done": True}):
            self.assertEqual(self.call("POST", "/api/plan", bad)[0], 400, bad)
        for i in range(300):
            self.conn.execute("INSERT INTO settings(key,value,updated_at) VALUES ('plan_ticks', '{}', 'x') ON CONFLICT (key) DO NOTHING")
        big = {f"i{i}": "t" for i in range(300)}
        self.conn.execute("UPDATE settings SET value=? WHERE key='plan_ticks'", (json.dumps(big),))
        self.assertEqual(self.call("POST", "/api/plan", {"id": "one-more", "done": True})[0], 400)


if __name__ == "__main__":
    unittest.main()
