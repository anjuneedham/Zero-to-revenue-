import json
import unittest

from core import db
from dashboard.app import handle
from tests.unit.test_phase1 import AuthTest, OWNER, PROJECT, make_conn
from core.auth.firebase_auth import OwnerAuth


class DashboardTest(AuthTest):
    def setUp(self):
        self.conn = make_conn()
        self.a = self.auth()

    def call(self, method, path, token=None):
        code, _, body = handle(method, path, f"Bearer {token}" if token else None, self.conn, self.a)
        return code, json.loads(body) if body[:1] in b"{[" else body.decode()

    def test_page_is_public_but_labelled_mock_and_api_requires_auth(self):
        code, html = self.call("GET", "/")
        self.assertEqual(code, 200)
        self.assertIn("MOCK", html)
        for path, m in (("/api/status", "GET"), ("/api/pause", "POST"), ("/api/resume", "POST")):
            self.assertEqual(self.call(m, path)[0], 401)
            self.assertEqual(self.call(m, path, "garbage")[0], 401)

    def test_non_owner_token_rejected(self):
        self.assertEqual(self.call("GET", "/api/status", self.token(email="evil@example.com"))[0], 401)

    def test_status_pause_resume_roundtrip_with_audit(self):
        t = self.token()
        code, s = self.call("GET", "/api/status", t)
        self.assertEqual((code, s["paused"], s["verified_revenue_usd"]), (200, False, 0))
        self.assertEqual(self.call("POST", "/api/pause", t)[1], {"paused": True})
        self.assertTrue(self.call("GET", "/api/status", t)[1]["paused"])
        self.call("POST", "/api/resume", t)
        actions = [r[0] for r in self.conn.execute("select action from audit_events")]
        self.assertEqual(actions, ["kill_switch.pause", "kill_switch.resume"])

    def test_only_verified_receipts_count_as_revenue(self):
        ins = "INSERT INTO ledger_entries(entry_id,date,type,usd_value,status) VALUES (?,?,?,?,?)"
        self.conn.execute(ins, ("1", "d", "receipt", 25, "VERIFIED"))
        self.conn.execute(ins, ("2", "d", "receipt", 100, "PENDING"))
        self.conn.execute(ins, ("3", "d", "self_transfer", 50, "VERIFIED"))
        self.assertEqual(self.call("GET", "/api/status", self.token())[1]["verified_revenue_usd"], 25)

    def test_unknown_route_and_no_inner_html(self):
        self.assertEqual(self.call("GET", "/nope")[0], 404)
        self.assertNotIn("innerHTML", self.call("GET", "/")[1])


del AuthTest  # avoid re-running the inherited auth tests here
if __name__ == "__main__":
    unittest.main()


class PwaTest(unittest.TestCase):
    def test_pwa_assets_served_and_api_never_cached(self):
        a = OwnerAuth(PROJECT, OWNER)
        for path, ctype in (("/manifest.webmanifest", "application/manifest+json"),
                            ("/sw.js", "text/javascript"), ("/icon-512.png", "image/png")):
            code, ct, body = handle("GET", path, None, None, a)
            self.assertEqual((code, ct), (200, ctype))
            self.assertTrue(body)
        sw = handle("GET", "/sw.js", None, None, a)[2].decode()
        self.assertIn('startsWith("/api/")', sw)
        manifest = json.loads(handle("GET", "/manifest.webmanifest", None, None, a)[2])
        self.assertEqual(manifest["display"], "standalone")

    def test_vercel_entry_refuses_api_without_postgres(self):
        from api import index
        self.assertFalse(index.HAS_PERSISTENT_DB)
