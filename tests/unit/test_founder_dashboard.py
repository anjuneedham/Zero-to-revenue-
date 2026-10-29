import json
import os
import unittest
from datetime import date
from unittest import mock

from core import founder_dashboard as fd
from dashboard.app import handle
from tests.authutil import session
from tests.dbutil import make_conn

TODAY = date(2026, 10, 29)
B = {"a": {"priority": 1}, "b": {"priority": 2}, "c": {"priority": 4}}


def task(id, biz="a", **kw):
    base = dict(id=id, business_id=biz, title=id, status="todo", priority=3, due_date=None, effort_hours=None, impact=None, depends_on=None,
                goal_id=None, goal_title=None, open_blockers=0, created_at="2026-10-01", business_name=biz)
    return {**base, **kw}


class RankingTest(unittest.TestCase):
    def rank(self, *ts):
        return fd.rank_tasks(list(ts), B, TODAY)

    def test_business_priority_order_when_nothing_else_is_known(self):
        self.assertEqual([x["id"] for x in self.rank(task("t_c", "c"), task("t_a", "a"), task("t_b", "b"))], ["t_a", "t_b", "t_c"])

    def test_overdue_lower_priority_beats_undated_top_priority_and_says_so(self):
        r = self.rank(task("top", "a"), task("late", "c", due_date="2026-10-27"))
        self.assertEqual(r[0]["id"], "late")
        self.assertIn("overdue by 2 day(s)", r[0]["why"])
        rec = fd.recommend(r, [], B)
        self.assertEqual(rec["task_id"], "late")
        self.assertTrue(any("lower-priority" in x for x in rec["risks"]))

    def test_task_priority_is_neutral_at_default(self):
        r = self.rank(task("lo", priority=5), task("mid", priority=3), task("hi", priority=1))
        self.assertEqual([x["id"] for x in r], ["hi", "mid", "lo"])
        self.assertNotIn("you set its priority", " ".join(r[1]["why"]))

    def test_blocked_tasks_are_never_recommended(self):
        r = self.rank(task("dep"), task("child", impact=5, due_date="2026-10-29", depends_on="dep"),
                      task("flagged", status="blocked", impact=5), task("hasblk", impact=5, open_blockers=1))
        self.assertEqual(r[0]["id"], "dep")
        self.assertIn("unblocks 1 other task(s)", r[0]["why"])
        self.assertFalse(any(x["eligible"] for x in r if x["id"] in ("child", "flagged", "hasblk")))
        self.assertEqual(fd.recommend(r, [], B)["task_id"], "dep")

    def test_done_or_cancelled_dependency_does_not_block_and_closed_tasks_are_skipped(self):
        r = self.rank(task("dep", status="done"), task("gone", status="cancelled"), task("child", depends_on="dep"))
        self.assertEqual([x["id"] for x in r], ["child"])
        self.assertTrue(r[0]["eligible"])

    def test_missing_data_is_reported_not_invented(self):
        rec = fd.recommend(self.rank(task("x")), [], B)
        self.assertEqual((rec["evidence"], rec["expected_outcome"]), ("low", "not recorded"))
        self.assertIn("missing: no impact estimate", rec["risks"])

    def test_no_tasks_gives_missing_info_not_a_made_up_action(self):
        rec = fd.recommend([], [], B)
        self.assertIsNone(rec["action"])
        self.assertTrue(rec["missing"])

    def test_all_blocked_points_at_recorded_blocker(self):
        rec = fd.recommend(self.rank(task("x", status="blocked")), [{"business_id": "a", "description": "no API key", "work_task_id": "x"}], B)
        self.assertIn("no API key", rec["action"])

    def test_deterministic(self):
        ts = [task("t1", impact=3), task("t2", impact=3)]
        self.assertEqual(self.rank(*ts), self.rank(*reversed(ts)))


class KpiTest(unittest.TestCase):
    K = dict(baseline_value=0.0, target_value=100.0, direction="up", current_value=None)

    def test_progress_trend(self):
        v = fd.kpi_view(self.K, [{"value": 10.0, "recorded_at": "a"}, {"value": 40.0, "recorded_at": "b"}])
        self.assertEqual(v["progress_pct"], 40.0)
        self.assertEqual((v["trend"]["direction"], v["trend"]["good"]), ("up", True))

    def test_no_progress_without_baseline_target_or_span(self):
        r = [{"value": 5.0, "recorded_at": "a"}]
        self.assertIsNone(fd.kpi_view({**self.K, "baseline_value": None}, r)["progress_pct"])
        self.assertIsNone(fd.kpi_view({**self.K, "baseline_value": 3.0, "target_value": 3.0}, r)["progress_pct"])
        self.assertIsNone(fd.kpi_view(self.K, [])["current"])

    def test_falls_back_to_current_value_when_there_is_no_history(self):
        v = fd.kpi_view({**self.K, "current_value": 7.0, "updated_at": "t"}, [])
        self.assertEqual((v["current"], v["last_updated"], v["trend"]), (7.0, "t", None))

    def test_lower_is_better_trend_and_clamp(self):
        k = dict(baseline_value=100.0, target_value=10.0, direction="down", current_value=None)
        v = fd.kpi_view(k, [{"value": 50.0, "recorded_at": "a"}, {"value": 20.0, "recorded_at": "b"}])
        self.assertTrue(v["trend"]["good"])
        self.assertEqual(fd.kpi_view(k, [{"value": 500.0, "recorded_at": "a"}])["progress_pct"], 0.0)


class DashboardApiTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.tok = session(self.conn)[0]

    def call(self, method, path, body=None, token="x"):
        token = self.tok if token == "x" else token
        c, _, out = handle(method, path, f"Bearer {token}" if token else None, self.conn, json.dumps(body).encode() if body is not None else b"")
        return c, json.loads(out)

    def make(self, biz, entity, **body):
        c, r = self.call("POST", f"/api/founder/businesses/{biz}/{entity}", body)
        self.assertEqual(c, 201, r)
        return r

    def dash(self):
        c, d = self.call("GET", "/api/founder/dashboard")
        self.assertEqual(c, 200)
        return d

    def test_requires_auth(self):
        for tok in (None, "bad"):
            self.assertEqual(self.call("GET", "/api/founder/dashboard", token=tok)[0], 401)

    def test_four_businesses_from_data_and_honest_empty_state(self):
        d = self.dash()
        self.assertEqual([(c["name"], c["priority"]) for c in d["cards"]], [("BuildFlow", 1), ("Agriloop", 2), ("Fashion", 3), ("Trading", 4)])
        self.assertTrue(all(c["primary_kpi"] is None and c["next_action"] is None and c["bottleneck"] is None and c["objective"] is None for c in d["cards"]))
        self.assertEqual((d["priorities"], d["kpis"], d["experiments"], d["decisions"], d["blockers"], d["goals"]), ([], [], [], [], [], []))
        self.assertFalse(d["ai_usage"]["available"])
        self.assertIsNone(d["recommendation"]["action"])

    def test_priority_is_data_driven(self):
        self.conn.execute("UPDATE businesses SET priority=0+1, name=name WHERE slug='trading'")
        self.conn.execute("UPDATE businesses SET priority=9 WHERE slug='buildflow'")
        names = [c["name"] for c in self.dash()["cards"]]
        self.assertEqual(names[-1], "BuildFlow")
        self.assertIn("Trading", names[:2])

    def test_task_flow_with_ranking_inputs_and_done_today(self):
        t = self.make("buildflow", "work-tasks", title="Ship onboarding", impact=4, due_date="2026-10-30", effort_hours=2, next_step="Open the signup form")
        self.make("agriloop", "work-tasks", title="Other")
        d = self.dash()
        self.assertEqual(len(d["priorities"]), 2)
        self.assertEqual((d["recommendation"]["task_id"], d["recommendation"]["next_step"]), (t["id"], "Open the signup form"))
        self.assertEqual(d["recommendation"]["business"], "BuildFlow")
        self.assertEqual(self.call("POST", f"/api/founder/work-tasks/{t['id']}", {"status": "done"})[0], 200)
        d = self.dash()
        self.assertEqual([x["id"] for x in d["done_today"]], [t["id"]])
        self.assertNotIn(t["id"], [x["id"] for x in d["priorities"]])

    def test_invalid_ranking_inputs_rejected_by_the_api(self):
        for body in ({"title": "x", "impact": 9}, {"title": "x", "effort_hours": -1}, {"title": "x", "impact": "high"}):
            self.assertEqual(self.call("POST", "/api/founder/businesses/buildflow/work-tasks", body)[0], 400, body)

    def test_business_isolation_of_references(self):
        g = self.make("buildflow", "goals", title="Launch")
        t = self.make("buildflow", "work-tasks", title="A")
        for entity, body in (("work-tasks", {"title": "B", "goal_id": g["id"]}), ("work-tasks", {"title": "B", "depends_on": t["id"]}),
                             ("blockers", {"description": "x", "work_task_id": t["id"]})):
            self.assertEqual(self.call("POST", f"/api/founder/businesses/agriloop/{entity}", body)[0], 400, (entity, body))
        self.assertEqual(self.call("POST", "/api/founder/businesses/buildflow/work-tasks", {"title": "C", "goal_id": g["id"], "depends_on": t["id"]})[0], 201)

    def test_blockers_kpis_experiments_decisions_roundtrip(self):
        t = self.make("agriloop", "work-tasks", title="Find farmers", impact=5)
        b = self.make("agriloop", "blockers", work_task_id=t["id"], description="No contact list", impact="No outreach")
        d = self.dash()
        self.assertEqual(d["blockers"][0]["kind"], "recorded")
        self.assertFalse(d["priorities"][0]["eligible"])
        self.assertIn("No contact list", d["recommendation"]["action"])
        self.assertEqual(next(c for c in d["cards"] if c["slug"] == "agriloop")["bottleneck"]["description"], "No contact list")
        self.assertEqual(self.call("POST", f"/api/founder/blockers/{b['id']}", {"status": "resolved"})[0], 200)
        self.assertEqual(self.dash()["blockers"], [])
        k = self.make("buildflow", "kpis", name="Signups", unit="users", baseline_value=0, target_value=100, is_primary=True)
        self.call("POST", f"/api/founder/kpis/{k['id']}/readings", {"value": 10})
        self.call("POST", f"/api/founder/kpis/{k['id']}/readings", {"value": 30})
        bf = next(c for c in self.dash()["cards"] if c["slug"] == "buildflow")
        self.assertEqual((bf["primary_kpi"]["current"], bf["primary_kpi"]["progress_pct"]), (30.0, 30.0))
        self.make("buildflow", "goals", title="First 10 paying users")
        self.make("buildflow", "experiments", hypothesis="Shorter copy converts", status="running", review_date="2026-11-05", success_metric="signup rate")
        self.make("buildflow", "experiments", hypothesis="Old test", status="failed")
        self.make("fashion", "decisions", title="Pause fashion", rationale="Focus", status="decided")
        d = self.dash()
        self.assertEqual([e["hypothesis"] for e in d["experiments"]], ["Shorter copy converts"])
        self.assertEqual((d["decisions"][0]["business_name"], d["decisions"][0]["decided_at"] is not None), ("Fashion", True))
        self.assertEqual(next(c for c in d["cards"] if c["slug"] == "buildflow")["objective"], "First 10 paying users")

    def test_cross_business_decision_is_shown_as_all_businesses(self):
        self.call("POST", "/api/founder/decisions", {"title": "Weekly rhythm"})
        self.assertEqual(self.dash()["decisions"][0]["business_name"], "All businesses")

    def test_ai_usage_only_from_real_rows_and_ledgers_are_separate(self):
        from core.db import now
        self.conn.execute("INSERT INTO llm_usage(at,agent,model,purpose,input_tokens,output_tokens,cost_usd,status) VALUES (?, 'scout','m','enrich',100,50,0.002,'DONE')", (now(),))
        self.call("POST", "/api/founder/ai-usage", {"model": "m2", "input_tokens": 10, "output_tokens": 5, "cost_usd": 0.5, "business": "buildflow"})
        u = self.dash()["ai_usage"]
        self.assertTrue(u["available"])
        self.assertEqual([(s["name"], s["month"]["requests"]) for s in u["sources"]], [("Scout (llm_usage)", 1), ("Founder OS (ai_usage)", 1)])
        self.assertEqual(u["by_business"][0]["business_name"], "BuildFlow")
        self.assertIsNone(u["monthly_cap_usd"])

    def test_one_section_failing_does_not_break_the_dashboard(self):
        self.conn.execute("ALTER TABLE experiments RENAME TO experiments_x")
        d = self.dash()
        self.assertIn("error", d["experiments"])
        self.assertEqual(len(d["cards"]), 4)
        self.assertNotIn("experiments_x", json.dumps(d))

    def test_user_text_is_returned_as_data(self):
        self.make("buildflow", "work-tasks", title="<img src=x onerror=alert(1)>")
        self.assertEqual(self.dash()["priorities"][0]["title"], "<img src=x onerror=alert(1)>")


class AuthDisabledTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()

    def get(self, env, drop=()):
        with mock.patch.dict(os.environ, env, clear=False):
            for k in drop:
                os.environ.pop(k, None)
            return handle("GET", "/api/founder/dashboard", None, self.conn)[0]

    def test_skip_login_only_when_opted_in_and_not_production(self):
        self.assertEqual(self.get({}, drop=("AUTH_DISABLED", "VERCEL_ENV")), 401)
        self.assertEqual(self.get({"AUTH_DISABLED": "1", "VERCEL_ENV": "preview"}), 200)
        self.assertEqual(self.get({"AUTH_DISABLED": "1"}, drop=("VERCEL_ENV",)), 200)
        self.assertEqual(self.get({"AUTH_DISABLED": "1", "VERCEL_ENV": "production"}), 401)
        self.assertEqual(self.get({"AUTH_DISABLED": "true", "VERCEL_ENV": "preview"}), 401)


if __name__ == "__main__":
    unittest.main()


class EarlyDraftRepairTest(unittest.TestCase):
    """A database that already ran the early draft's 007_founder.sql must still migrate, keeping its data."""

    def test_migrate_after_early_draft_schema(self):
        from pathlib import Path
        from tests.dbutil import URL, require_db
        import uuid
        from core import db
        require_db()
        schema = "t_early_" + uuid.uuid4().hex[:8]
        admin = db.connect(URL)
        admin.execute(f'CREATE SCHEMA "{schema}"')
        admin.close()
        conn = db.connect(URL, schema=schema)
        try:
            # recreate the state of the shared database: migrations 001-006 + the early draft applied
            for f in sorted(db.MIGRATIONS.glob("00[1-6]_*.sql")):
                conn.raw.execute(f.read_text())
            conn.execute("CREATE TABLE schema_migrations (name TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
            for f in sorted(db.MIGRATIONS.glob("00[1-6]_*.sql")):
                conn.execute("INSERT INTO schema_migrations VALUES (?, ?)", (f.name, "x"))
            conn.raw.execute((Path(__file__).parents[1] / "fixtures" / "early_007_founder.sql").read_text())
            conn.execute("INSERT INTO schema_migrations VALUES ('007_founder.sql', 'x')")
            conn.execute("INSERT INTO goals(id, venture_id, title, created_at) VALUES ('g1','buildflow','kept','x')")
            applied = db.migrate(conn)
            self.assertEqual(applied[:3], ["007_a_retire_early_dashboard_schema.sql", "007_founder_os_core.sql", "008_founder_dashboard.sql"])  # later migrations may follow
            self.assertEqual(conn.execute("SELECT title FROM early_goals").fetchone()["title"], "kept")
            self.assertEqual(conn.execute("SELECT count(*) n FROM businesses").fetchone()["n"], 4)
            self.assertEqual(conn.execute("SELECT count(*) n FROM goals").fetchone()["n"], 0)
            self.assertEqual(db.migrate(conn), [])
        finally:
            conn.close()
            admin = db.connect(URL)
            admin.execute(f'DROP SCHEMA "{schema}" CASCADE')
            admin.close()
