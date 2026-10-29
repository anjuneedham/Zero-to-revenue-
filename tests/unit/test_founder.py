import json
import unittest
from datetime import date

from core import founder
from dashboard.app import handle
from tests.authutil import session
from tests.dbutil import make_conn

TODAY = date(2026, 10, 29)
V = {"a": {"priority": 1}, "b": {"priority": 2}, "c": {"priority": 4}}


def task(id, venture="a", **kw):
    base = dict(id=id, venture_id=venture, title=id, status="TODO", due_date=None, effort_hours=None, impact=None,
                depends_on=None, goal_id=None, goal_title=None, open_blockers=0, created_at="2026-10-01", venture_name=venture)
    return {**base, **kw}


class RankingTest(unittest.TestCase):
    def rank(self, *ts):
        return founder.rank_tasks(list(ts), V, TODAY)

    def test_priority_order_when_nothing_else_is_known(self):
        r = self.rank(task("t_c", "c"), task("t_a", "a"), task("t_b", "b"))
        self.assertEqual([x["id"] for x in r], ["t_a", "t_b", "t_c"])

    def test_overdue_lower_priority_beats_undated_top_priority_and_says_so(self):
        r = self.rank(task("top", "a"), task("late", "c", due_date="2026-10-27"))
        self.assertEqual(r[0]["id"], "late")
        self.assertIn("overdue by 2 day(s)", r[0]["why"])
        rec = founder.recommend(r, [], {k: v for k, v in V.items()})
        self.assertEqual(rec["task_id"], "late")
        self.assertTrue(any("lower-priority" in x for x in rec["risks"]))

    def test_blocked_tasks_are_never_recommended(self):
        r = self.rank(task("dep", "a", status="TODO"), task("child", "a", impact=5, due_date="2026-10-29", depends_on="dep"),
                      task("flagged", "a", status="BLOCKED", impact=5), task("hasblk", "a", impact=5, open_blockers=1))
        self.assertEqual(r[0]["id"], "dep")
        self.assertIn("unblocks 1 other task(s)", r[0]["why"])
        self.assertFalse(any(x["eligible"] for x in r if x["id"] in ("child", "flagged", "hasblk")))
        self.assertEqual(founder.recommend(r, [], V)["task_id"], "dep")

    def test_done_dependency_does_not_block(self):
        r = self.rank(task("dep", status="DONE"), task("child", depends_on="dep"))
        self.assertTrue(r[0]["eligible"])

    def test_missing_data_is_reported_not_invented(self):
        rec = founder.recommend(self.rank(task("x")), [], V)
        self.assertEqual(rec["evidence"], "low")
        self.assertEqual(rec["expected_outcome"], "not recorded")
        self.assertIn("missing: no impact estimate", rec["risks"])

    def test_no_tasks_gives_missing_info_not_a_made_up_action(self):
        rec = founder.recommend([], [], V)
        self.assertIsNone(rec["action"])
        self.assertTrue(rec["missing"])

    def test_all_blocked_points_at_recorded_blocker(self):
        r = self.rank(task("x", status="BLOCKED"))
        rec = founder.recommend(r, [{"venture_id": "a", "description": "no API key", "task_id": "x"}], V)
        self.assertIn("no API key", rec["action"])

    def test_deterministic(self):
        ts = [task("t1", "a", impact=3), task("t2", "a", impact=3)]
        self.assertEqual(self.rank(*ts), self.rank(*reversed(ts)))


class KpiTest(unittest.TestCase):
    K = dict(baseline=0.0, target=100.0, higher_is_better=True)

    def test_progress_trend(self):
        v = founder.kpi_view(self.K, [{"value": 10.0, "recorded_at": "a"}, {"value": 40.0, "recorded_at": "b"}])
        self.assertEqual(v["progress_pct"], 40.0)
        self.assertEqual((v["trend"]["direction"], v["trend"]["good"]), ("up", True))

    def test_no_progress_without_baseline_target_or_span(self):
        r = [{"value": 5.0, "recorded_at": "a"}]
        self.assertIsNone(founder.kpi_view({"baseline": None, "target": 10.0, "higher_is_better": True}, r)["progress_pct"])
        self.assertIsNone(founder.kpi_view({"baseline": 3.0, "target": 3.0, "higher_is_better": True}, r)["progress_pct"])
        self.assertIsNone(founder.kpi_view(self.K, [])["current"])

    def test_lower_is_better_trend_and_clamp(self):
        k = dict(baseline=100.0, target=10.0, higher_is_better=False)
        v = founder.kpi_view(k, [{"value": 50.0, "recorded_at": "a"}, {"value": 20.0, "recorded_at": "b"}])
        self.assertTrue(v["trend"]["good"])
        self.assertEqual(founder.kpi_view(k, [{"value": 500.0, "recorded_at": "a"}])["progress_pct"], 0.0)


class FounderApiTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.tok = session(self.conn)[0]
        self.n = 0

    def call(self, method, path, body=None, token="x"):
        token = self.tok if token == "x" else token
        c, _, out = handle(method, path, f"Bearer {token}" if token else None, self.conn, json.dumps(body).encode() if body is not None else b"")
        return c, json.loads(out)

    def post(self, kind, **body):
        self.n += 1
        return self.call("POST", "/api/founder/" + kind, {"client_key": f"key{self.n:08d}", **body})

    def dash(self):
        c, d = self.call("GET", "/api/founder/dashboard")
        self.assertEqual(c, 200)
        return d

    def test_requires_auth(self):
        for m, p in (("GET", "/api/founder/dashboard"), ("POST", "/api/founder/task"), ("POST", "/api/founder/tasks/x/status")):
            self.assertEqual(self.call(m, p, {}, token=None)[0], 401)
            self.assertEqual(self.call(m, p, {}, token="bad")[0], 401)

    def test_four_businesses_from_data_and_honest_empty_state(self):
        d = self.dash()
        self.assertEqual([c["name"] for c in d["cards"]], ["BuildFlow", "Agriloop", "Fashion Brand", "Trading Bot"])
        self.assertEqual([c["priority"] for c in d["cards"]], [1, 2, 3, 4])
        self.assertTrue(all(c["primary_kpi"] is None and c["next_action"] is None and c["bottleneck"] is None for c in d["cards"]))
        self.assertEqual((d["priorities"], d["kpis"], d["experiments"], d["decisions"], d["blockers"]), ([], [], [], [], []))
        self.assertFalse(d["ai_usage"]["available"])
        self.assertIsNone(d["recommendation"]["action"])

    def test_priority_is_data_driven(self):
        self.conn.execute("UPDATE ventures SET priority=0 WHERE id='trading'")
        self.assertEqual(self.dash()["cards"][0]["name"], "Trading Bot")

    def test_task_lifecycle_and_idempotent_create(self):
        c, r = self.post("task", venture_id="buildflow", title="Ship onboarding", impact=4, due_date="2026-10-30", effort_hours="2")
        self.assertEqual((c, r["created"]), (200, True))
        tid = r["id"]
        body = {"client_key": "dupkey0001", "venture_id": "buildflow", "title": "dup"}
        self.assertTrue(self.call("POST", "/api/founder/task", body)[1]["created"])
        self.assertFalse(self.call("POST", "/api/founder/task", body)[1]["created"])
        d = self.dash()
        self.assertEqual(len(d["priorities"]), 2)
        self.assertEqual(d["recommendation"]["task_id"], tid)
        self.assertEqual(self.call("POST", f"/api/founder/tasks/{tid}/status", {"status": "DONE"})[0], 200)
        d = self.dash()
        self.assertEqual([t["id"] for t in d["done_today"]], [tid])
        self.assertNotIn(tid, [t["id"] for t in d["priorities"]])
        self.assertEqual(self.call("POST", "/api/founder/tasks/nope/status", {"status": "DONE"})[0], 400)
        self.assertEqual(self.call("POST", f"/api/founder/tasks/{tid}/status", {"status": "HACK"})[0], 400)
        n = self.conn.execute("SELECT count(*) n FROM audit_events WHERE action LIKE 'founder.%'").fetchone()["n"]
        self.assertGreaterEqual(n, 3)

    def test_validation(self):
        bad = [("task", dict(venture_id="nope", title="x")), ("task", dict(venture_id="buildflow", title="")),
               ("task", dict(venture_id="buildflow", title="x", impact=9)), ("task", dict(venture_id="buildflow", title="x", due_date="soon")),
               ("task", dict(venture_id="buildflow", title="x", effort_hours="-1")), ("task", dict(venture_id="buildflow", title="x" * 500)),
               ("task", dict(venture_id="buildflow", title=["x"])), ("kpi", dict(venture_id="buildflow", name="n", target="NaN")),
               ("reading", dict(kpi_id="nope", value=1)), ("blocker", dict(venture_id="buildflow", description=""))]
        for kind, body in bad:
            self.assertEqual(self.post(kind, **body)[0], 400, (kind, body))
        self.assertEqual(self.call("POST", "/api/founder/task", {"venture_id": "buildflow", "title": "no key"})[0], 400)
        self.assertEqual(self.call("POST", "/api/founder/nothing", {})[0], 404)

    def test_business_isolation_of_references(self):
        _, g = self.post("goal", venture_id="buildflow", title="Launch")
        _, t = self.post("task", venture_id="buildflow", title="A")
        self.assertEqual(self.post("task", venture_id="agriloop", title="B", goal_id=g["id"])[0], 400)
        self.assertEqual(self.post("task", venture_id="agriloop", title="B", depends_on=t["id"])[0], 400)
        self.assertEqual(self.post("blocker", venture_id="agriloop", description="x", task_id=t["id"])[0], 400)
        self.assertEqual(self.post("task", venture_id="buildflow", title="C", goal_id=g["id"], depends_on=t["id"])[0], 200)

    def test_blockers_kpis_experiments_decisions_roundtrip(self):
        _, t = self.post("task", venture_id="agriloop", title="Find farmers", impact=5)
        _, b = self.post("blocker", venture_id="agriloop", task_id=t["id"], description="No contact list", impact="No outreach")
        d = self.dash()
        self.assertEqual(d["blockers"][0]["kind"], "recorded")
        self.assertFalse(d["priorities"][0]["eligible"])
        self.assertIn("No contact list", d["recommendation"]["action"])
        self.assertEqual(next(c for c in d["cards"] if c["id"] == "agriloop")["bottleneck"]["description"], "No contact list")
        self.assertEqual(self.call("POST", f"/api/founder/blockers/{b['id']}/resolve", {})[0], 200)
        self.assertEqual(self.call("POST", f"/api/founder/blockers/{b['id']}/resolve", {})[0], 400)
        self.assertEqual(self.dash()["blockers"], [])
        _, k = self.post("kpi", venture_id="buildflow", name="Signups", unit="users", baseline=0, target=100, is_primary=True)
        self.post("reading", kpi_id=k["id"], value=10)
        self.post("reading", kpi_id=k["id"], value=30)
        bf = next(c for c in self.dash()["cards"] if c["id"] == "buildflow")
        self.assertEqual((bf["primary_kpi"]["current"], bf["primary_kpi"]["progress_pct"]), (30.0, 30.0))
        self.post("experiment", venture_id="buildflow", name="Landing page A/B", hypothesis="Shorter copy converts")
        self.post("decision", venture_id="fashion", title="Pause fashion", rationale="Focus")
        d = self.dash()
        self.assertEqual(d["experiments"][0]["name"], "Landing page A/B")
        self.assertEqual(d["decisions"][0]["venture_name"], "Fashion Brand")

    def test_ai_usage_only_from_real_rows(self):
        from core.db import now
        self.conn.execute("INSERT INTO llm_usage(at,agent,model,purpose,input_tokens,output_tokens,cost_usd,status) VALUES (?, 'scout','m','enrich',100,50,0.002,'DONE')", (now(),))
        u = self.dash()["ai_usage"]
        self.assertTrue(u["available"])
        self.assertEqual((u["month"]["requests"], u["month"]["input_tokens"], u["monthly_cap_usd"]), (1, 100, None))

    def test_one_section_failing_does_not_break_the_dashboard(self):
        self.conn.execute("ALTER TABLE experiments RENAME TO experiments_x")
        d = self.dash()
        self.assertIn("error", d["experiments"])
        self.assertEqual(len(d["cards"]), 4)
        self.assertNotIn("experiments_x", json.dumps(d))  # no internals leaked

    def test_user_text_is_returned_as_data(self):
        _, t = self.post("task", venture_id="buildflow", title="<img src=x onerror=alert(1)>")
        self.assertEqual(self.dash()["priorities"][0]["title"], "<img src=x onerror=alert(1)>")


if __name__ == "__main__":
    unittest.main()
