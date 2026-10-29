import json
import os
import unittest
from unittest import mock

import dashboard.app as dash
from core import db
from tests.authutil import session
from tests.dbutil import make_conn
from tests.unit.test_phases_3_6 import ENV

SLUGS = {"buildflow", "agriloop", "fashion", "trading"}


class FounderOSTest(unittest.TestCase):
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

    def biz(self, slug="buildflow", ent="projects", body=None):
        return self.call("POST", f"/api/founder/businesses/{slug}/{ent}", body)

    # --- schema / migration -------------------------------------------------
    def test_all_core_tables_exist_and_legacy_tables_survive(self):
        have = {r["table_name"] for r in self.conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema=current_schema()")}
        new = {"businesses", "projects", "goals", "work_tasks", "kpis", "kpi_readings", "experiments", "research",
               "knowledge", "decisions", "prompts", "ai_usage", "automations"}
        legacy = {"tasks", "agents", "opportunities", "leads", "payments", "audit_events"}
        self.assertLessEqual(new | legacy, have)

    def test_migration_is_idempotent(self):
        self.assertEqual(db.migrate(self.conn), [])

    def test_four_businesses_seeded(self):
        c, d = self.call("GET", "/api/founder/businesses")
        self.assertEqual(c, 200)
        self.assertEqual({b["slug"] for b in d["businesses"]}, SLUGS)
        self.assertEqual(len(d["businesses"]), 4)

    def test_legacy_agents_untouched(self):
        names = {r["name"] for r in self.conn.execute("SELECT name FROM agents")}
        self.assertEqual(names, {"scout", "operator", "treasury"})

    # --- auth ---------------------------------------------------------------
    def test_requires_login(self):
        for m, p in (("GET", "/api/founder/businesses"), ("GET", "/api/founder/knowledge"),
                     ("POST", "/api/founder/businesses/trading/goals")):
            self.assertEqual(self.call(m, p, {}, auth=False)[0], 401, p)

    # --- CRUD ---------------------------------------------------------------
    def test_business_summary_and_scoped_lists(self):
        self.biz("buildflow", "projects", {"name": "Launch"})
        self.biz("agriloop", "projects", {"name": "Prisma adapter"})
        c, d = self.call("GET", "/api/founder/businesses/buildflow")
        self.assertEqual(d["counts"]["projects"], 1)
        c, d = self.call("GET", "/api/founder/businesses/agriloop/projects")
        self.assertEqual([p["name"] for p in d["projects"]], ["Prisma adapter"])

    def test_unknown_business_404(self):
        self.assertEqual(self.call("GET", "/api/founder/businesses/nope")[0], 404)
        self.assertEqual(self.biz("nope", "goals", {"title": "x"})[0], 404)

    def test_every_entity_can_be_created(self):
        bodies = {"projects": {"name": "p"}, "goals": {"title": "g", "target_value": "10.5"}, "work-tasks": {"title": "t"},
                  "kpis": {"name": "MRR", "unit": "USD"}, "experiments": {"hypothesis": "h"}, "research": {"title": "r"},
                  "knowledge": {"title": "k", "body": "b"}, "decisions": {"title": "d"},
                  "prompts": {"name": "scout", "body": "..."}, "ai-usage": {"model": "claude-sonnet-5-5", "cost_usd": 0.01},
                  "automations": {"name": "weekly review"}}
        for ent, body in bodies.items():
            c, d = self.biz("trading", ent, body)
            self.assertEqual(c, 201, (ent, d))
            self.assertTrue(d["business_id"])

    def test_global_entities_without_business(self):
        c, d = self.call("POST", "/api/founder/knowledge", {"title": "Rule", "body": "Ship weekly"})
        self.assertEqual(c, 201)
        self.assertIsNone(d["business_id"])
        self.assertEqual(self.call("POST", "/api/founder/goals", {"title": "x"})[0], 400)  # needs a business

    def test_validation(self):
        for ent, body in (("projects", {}), ("projects", {"name": "x", "status": "bogus"}), ("projects", {"name": "x", "evil": 1}),
                          ("work-tasks", {"title": "x", "priority": 9}), ("work-tasks", {"title": "x", "priority": "1"}),
                          ("goals", {"title": "x", "target_value": "NaN"}), ("goals", {"title": "x", "target_value": "abc"}),
                          ("ai-usage", {"model": "m", "input_tokens": -1}), ("projects", {"name": "x" * 5000})):
            self.assertEqual(self.biz("buildflow", ent, body)[0], 400, (ent, body))

    def test_parent_must_be_same_business(self):
        pid = self.biz("agriloop", "projects", {"name": "p"})[1]["id"]
        self.assertEqual(self.biz("buildflow", "work-tasks", {"title": "t", "project_id": pid})[0], 400)
        self.assertEqual(self.biz("agriloop", "work-tasks", {"title": "t", "project_id": pid})[0], 201)

    def test_task_update_completion_and_immutability(self):
        t = self.biz("buildflow", "work-tasks", {"title": "t"})[1]
        c, d = self.call("POST", f"/api/founder/work-tasks/{t['id']}", {"status": "done"})
        self.assertEqual(c, 200)
        self.assertTrue(d["completed_at"])
        d = self.call("POST", f"/api/founder/work-tasks/{t['id']}", {"status": "todo"})[1]
        self.assertIsNone(d["completed_at"])
        self.assertEqual(self.call("POST", f"/api/founder/work-tasks/{t['id']}", {"business": "trading"})[0], 400)
        u = self.biz("buildflow", "ai-usage", {"model": "m"})[1]
        self.assertEqual(self.call("POST", f"/api/founder/ai-usage/{u['id']}", {"cost_usd": 1})[0], 400)
        self.assertEqual(self.call("POST", "/api/founder/work-tasks/missing", {"status": "done"})[0], 404)

    def test_duplicate_kpi_and_prompt_version_are_clean_400(self):
        self.biz("buildflow", "kpis", {"name": "MRR"})
        self.assertEqual(self.biz("buildflow", "kpis", {"name": "MRR"})[0], 400)
        self.call("POST", "/api/founder/prompts", {"name": "p", "body": "a"})
        c, d = self.call("POST", "/api/founder/prompts", {"name": "p", "body": "b"})
        self.assertEqual(c, 400)
        self.assertNotIn("psycopg", json.dumps(d))

    def test_kpi_readings_update_current_value_and_keep_history(self):
        k = self.biz("buildflow", "kpis", {"name": "Paying customers"})[1]
        self.call("POST", f"/api/founder/kpis/{k['id']}/readings", {"value": 1})
        c, d = self.call("POST", f"/api/founder/kpis/{k['id']}/readings", {"value": 3, "note": "wk2"})
        self.assertEqual((c, float(d["current_value"])), (200, 3.0))
        n = self.conn.execute("SELECT count(*) AS n FROM kpi_readings WHERE kpi_id=?", (k["id"],)).fetchone()["n"]
        self.assertEqual(n, 2)
        self.assertEqual(self.call("POST", f"/api/founder/kpis/{k['id']}/readings", {"value": "x"})[0], 400)

    def test_writes_are_audited_and_automations_default_off(self):
        a = self.biz("trading", "automations", {"name": "nightly"})[1]
        self.assertEqual((a["enabled"], a["requires_approval"]), (0, 1))
        n = self.conn.execute("SELECT count(*) AS n FROM audit_events WHERE action='founder.automations.create'").fetchone()["n"]
        self.assertEqual(n, 1)

    def test_bad_json_and_oversize(self):
        c, _, out = dash.handle("POST", "/api/founder/businesses/trading/goals", f"Bearer {self.tok}", self.conn, b"{nope")
        self.assertEqual(c, 400)
        c, _, _ = dash.handle("POST", "/api/founder/businesses/trading/goals", f"Bearer {self.tok}", self.conn, b"x" * 9000)
        self.assertEqual(c, 400)


if __name__ == "__main__":
    unittest.main()
