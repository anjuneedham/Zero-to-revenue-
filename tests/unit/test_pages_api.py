import json
import os
import unittest
from unittest import mock

import dashboard.app as dash
from agents.operator import run as operator
from agents.scout.run import run_scout
from agents.treasury import run as treasury
from tests.authutil import session
from tests.dbutil import make_conn
from tests.unit.test_phases_3_6 import ENV, TX, FakeChain, native_payment
from tests.unit.test_scout import good
from tests.unit.test_scout_db import Source


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
        for m, p in (("GET", "/api/scout/overview"), ("GET", "/api/operator/board"), ("GET", "/api/treasury/overview"),
                     ("GET", "/api/plan"), ("POST", "/api/plan")):
            self.assertEqual(self.call(m, p, auth=False)[0], 401, p)

    def test_auth_state_reports_local_or_live(self):
        self.assertEqual(self.call("GET", "/api/auth/state", auth=False)[1]["mode"], "LOCAL")
        with mock.patch.dict(os.environ, {"VERCEL": "1"}):
            self.assertEqual(self.call("GET", "/api/auth/state", auth=False)[1]["mode"], "LIVE")

    def test_scout_overview(self):
        run_scout(self.conn, [Source([good()])])
        c, d = self.call("GET", "/api/scout/overview")
        self.assertEqual(c, 200)
        self.assertEqual(d["runs"][0]["outcome"], "ok")
        self.assertEqual(d["counts"], {"QUALIFIED": 1})
        self.assertEqual({s["name"] for s in d["sources"]}, {"superteam-earn", "github-bounty-label"})
        self.assertFalse(d["ai"]["enabled"])
        self.assertIn("ANTHROPIC_API_KEY", d["ai"]["missing"])  # names only, never values
        self.assertNotIn("test-key", json.dumps(d))

    def test_operator_board(self):
        run_scout(self.conn, [Source([good()])])
        operator.step(self.conn)
        d = self.call("GET", "/api/operator/board")[1]
        t = d["tasks"][0]
        self.assertEqual((t["status"], t["kind"], t["title"][:5]), ("WAITING_FOR_USER", "research_opportunity", "Build"))
        self.assertTrue(t["action_id"])
        self.assertTrue(d["events"])
        self.assertIn("Submit anything", d["cannot"])

    def test_treasury_overview_after_checks(self):
        d = self.call("GET", "/api/treasury/overview")[1]
        self.assertEqual([c["chain_id"] for c in d["chains"]], [56, 8453])
        self.assertIsNone(d["chains"][0]["balance"])
        treasury.check_balances(self.conn, FakeChain(balance=10**17))
        d = self.call("GET", "/api/treasury/overview")[1]
        self.assertEqual(d["chains"][0]["balance"], 0.1)
        self.assertEqual(len(d["chains"][0]["history"]), 1)
        self.assertEqual(d["address"], ENV["OWNER_WALLET_ADDRESS"])
        self.assertEqual((d["safety"]["wallet_mode"], d["safety"]["signing"], d["safety"]["spending"]), ("READ_ONLY", False, False))

    def test_treasury_ledger_has_explorer_link_and_unconfigured_chains_explain_themselves(self):
        run_scout(self.conn, [Source([good()])])
        operator.step(self.conn)
        from core import actions
        aid = self.conn.execute("select action_id from user_actions").fetchone()[0]
        actions.approve(self.conn, aid, "owner")
        actions.mark_submitted(self.conn, aid, "owner")
        pid = self.conn.execute("select id from payments").fetchone()[0]
        treasury.verify_payment(self.conn, pid, 56, TX, native_payment())
        d = self.call("GET", "/api/treasury/overview")[1]
        self.assertEqual(d["ledger"][0]["tx_url"], f"https://bscscan.com/tx/{TX}")
        with mock.patch.dict(os.environ, {"OWNER_WALLET_CHAIN_IDS": ""}):
            d = self.call("GET", "/api/treasury/overview")[1]
            self.assertEqual(d["chains"], [])
            self.assertIn("not configured", d["problem"])

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
