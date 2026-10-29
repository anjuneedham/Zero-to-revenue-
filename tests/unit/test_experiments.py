"""Phase 9: experiment lifecycle, results, decisions, learning write-back, growth funnels. No model is involved anywhere."""

import json
import unittest

from core import experiments, founder, growth
from dashboard.app import handle
from tests.authutil import session
from tests.dbutil import make_conn


class Base(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.tok = session(self.conn)[0]

    def call(self, method, path, body=None):
        code, _, raw = handle(method, path, f"Bearer {self.tok}", self.conn, json.dumps(body).encode() if body is not None else b"")
        return code, json.loads(raw)

    def mk(self, ent, slug="buildflow", **body):
        code, d = self.call("POST", f"/api/founder/businesses/{slug}/{ent}", body)
        self.assertEqual(code, 201, d)
        return d

    def exp(self, **kw):
        base = {"hypothesis": "Shorter hero copy lifts signups", "success_metric": "signup rate", "duration_days": 14, "baseline_value": 2, "target_value": 4}
        return self.mk("experiments", **{**base, **kw})

    def act(self, eid, action, body=None):
        return self.call("POST", f"/api/growth/experiments/{eid}/{action}", body or {})

    def rows(self, sql, p=()):
        return [dict(r) for r in self.conn.execute(sql, p).fetchall()]

    GOOD = {"outcome": "succeeded", "decision": "scale", "learnings": "Short copy beat long copy", "result_value": 4.5, "sample_size": 120}


class LifecycleTest(Base):
    def test_new_experiments_are_always_proposed_and_status_cannot_be_edited(self):
        e = self.mk("experiments", hypothesis="h", status="succeeded")  # a requested status is ignored
        self.assertEqual(e["status"], "proposed")
        code, d = self.call("POST", f"/api/founder/experiments/{e['id']}", {"status": "running"})
        self.assertEqual(code, 400)
        self.assertEqual(self.call("POST", f"/api/founder/experiments/{e['id']}", {"hypothesis": "h2", "duration_days": 3})[0], 200)

    def test_start_needs_metric_and_duration_then_locks_the_plan(self):
        bare = self.mk("experiments", hypothesis="h")
        self.assertEqual(self.act(bare["id"], "start")[0], 400)
        self.call("POST", f"/api/founder/experiments/{bare['id']}", {"success_metric": "m"})
        self.assertEqual(self.act(bare["id"], "start")[0], 400)  # still no duration
        e = self.exp()
        code, r = self.act(e["id"], "start")
        self.assertEqual((code, r["status"], r["ends_on"] is not None), (200, "running", True))
        self.assertEqual(self.act(e["id"], "start")[0], 400)  # cannot start twice
        for field in ({"hypothesis": "moved goalposts"}, {"target_value": 1}, {"duration_days": 1}, {"success_metric": "x"}):
            self.assertEqual(self.call("POST", f"/api/founder/experiments/{e['id']}", field)[0], 400, field)
        self.assertEqual(self.call("POST", f"/api/founder/experiments/{e['id']}", {"next_action": "check Friday"})[0], 200)
        with self.assertRaises(Exception) as cm:  # DB trigger is the backstop
            self.conn.execute("UPDATE experiments SET hypothesis='x' WHERE id=?", (e["id"],))
        self.assertIn("plan", str(cm.exception))

    def test_database_blocks_illegal_status_moves_and_non_proposed_inserts(self):
        e = self.exp()
        with self.assertRaises(Exception):
            self.conn.execute("UPDATE experiments SET status='succeeded' WHERE id=?", (e["id"],))  # proposed -> succeeded
        with self.assertRaises(Exception):
            self.conn.execute("INSERT INTO experiments(id,business_id,hypothesis,status,created_at,updated_at) VALUES ('x','biz_buildflow','h','running','t','t')")

    def test_baseline_defaults_to_linked_kpi_current_value(self):
        k = self.mk("kpis", name="Signup rate", unit="%", current_value=2.5)
        e = self.mk("experiments", hypothesis="h", success_metric="m", duration_days=7, kpi_id=k["id"])
        r = self.act(e["id"], "start")[1]
        self.assertEqual((r["baseline_value"], r["kpi_name"]), (2.5, "Signup rate"))
        # a KPI of another business cannot be linked
        other = self.mk("kpis", slug="agriloop", name="x")
        self.assertEqual(self.call("POST", "/api/founder/businesses/buildflow/experiments", {"hypothesis": "h", "kpi_id": other["id"]})[0], 400)

    def test_conclude_records_result_decision_and_locks_it(self):
        e = self.exp()
        self.assertEqual(self.act(e["id"], "conclude", self.GOOD)[0], 400)  # not running yet
        self.act(e["id"], "start")
        code, r = self.act(e["id"], "conclude", self.GOOD)
        self.assertEqual((code, r["status"], r["decision"], r["evaluation"]["code"]), (200, "succeeded", "scale", "met"))
        self.assertIn("One result from one run", " ".join(r["evaluation"]["warnings"]))
        dec = self.rows("SELECT * FROM decisions WHERE experiment_id=?", (e["id"],))
        self.assertEqual((len(dec), dec[0]["status"], dec[0]["decision"].startswith("scale")), (1, "decided", True))
        with self.assertRaises(Exception):
            self.conn.execute("UPDATE experiments SET result_value=99 WHERE id=?", (e["id"],))
        self.assertEqual(self.act(e["id"], "conclude", self.GOOD)[0], 400)  # cannot conclude twice
        self.assertEqual(self.act(e["id"], "abandon", {"reason": "x"})[0], 400)

    def test_outcome_may_not_contradict_the_numbers(self):
        e = self.exp()
        self.act(e["id"], "start")
        code, d = self.act(e["id"], "conclude", {**self.GOOD, "result_value": 1.0})
        self.assertEqual(code, 400)
        self.assertIn("worse than baseline", d["error"])
        self.assertEqual(self.act(e["id"], "conclude", {**self.GOOD, "outcome": "failed"})[0], 400)  # target was met
        self.assertEqual(self.act(e["id"], "conclude", {**self.GOOD, "outcome": "inconclusive", "decision": "scale"})[0], 400)  # scale needs success
        self.assertEqual(self.act(e["id"], "conclude", {**self.GOOD, "outcome": "inconclusive", "decision": "iterate"})[0], 200)

    def test_conclude_validation(self):
        e = self.exp()
        self.act(e["id"], "start")
        for bad in ({"outcome": "great"}, {"decision": "maybe"}, {"learnings": ""}, {"result_value": None}, {"sample_size": -1}, {"result_value": "abc"}):
            body = {**self.GOOD, **bad}
            self.assertEqual(self.act(e["id"], "conclude", body)[0], 400, bad)
        self.assertEqual(self.rows("SELECT status FROM experiments WHERE id=?", (e["id"],))[0]["status"], "running")  # nothing half-applied
        self.assertEqual(self.rows("SELECT count(*) AS n FROM decisions")[0]["n"], 0)

    def test_direction_down_metrics_are_read_the_right_way_round(self):
        k = self.mk("kpis", name="Churn", direction="down", current_value=10)
        e = self.mk("experiments", hypothesis="h", success_metric="m", duration_days=7, kpi_id=k["id"], target_value=6)
        self.act(e["id"], "start")
        self.assertEqual(self.act(e["id"], "conclude", {**self.GOOD, "result_value": 12})[0], 400)  # churn went up: not a success
        self.assertEqual(self.act(e["id"], "conclude", {**self.GOOD, "result_value": 5})[1]["evaluation"]["code"], "met")

    def test_abandon_needs_a_reason_and_works_from_proposed_or_running(self):
        a, b = self.exp(), self.exp(hypothesis="h2")
        self.assertEqual(self.act(a["id"], "abandon", {})[0], 400)
        self.assertEqual(self.act(a["id"], "abandon", {"reason": "no traffic"})[1]["status"], "abandoned")
        self.act(b["id"], "start")
        self.assertEqual(self.act(b["id"], "abandon", {"reason": "bug"})[1]["abandon_reason"], "bug")

    def test_warnings_for_missing_sample_early_end(self):
        e = self.exp(min_sample=100)
        self.act(e["id"], "start")
        r = self.act(e["id"], "conclude", {**self.GOOD, "sample_size": 20})[1]
        w = " ".join(r["evaluation"]["warnings"])
        self.assertIn("below the minimum", w)
        self.assertIn("before the planned duration", w)
        e2 = self.exp(hypothesis="h2")
        self.act(e2["id"], "start")
        no_sample = {k: v for k, v in self.GOOD.items() if k != "sample_size"}
        self.assertIn("No sample size", " ".join(self.act(e2["id"], "conclude", no_sample)[1]["evaluation"]["warnings"]))

    def test_unknown_ids_404_and_auth_required(self):
        self.assertEqual(self.act("nope", "start")[0], 404)
        self.assertEqual(handle("GET", "/api/growth/buildflow", None, self.conn)[0], 401)
        self.assertEqual(self.call("GET", "/api/growth/nope")[0], 404)


class LearningTest(Base):
    def test_learning_is_written_back_as_assumed_evidence_with_an_internal_source(self):
        e = self.exp()
        self.act(e["id"], "start")
        r = self.act(e["id"], "conclude", self.GOOD)[1]
        kn = self.rows("SELECT * FROM knowledge WHERE id=?", (r["learning_knowledge_id"],))[0]
        self.assertEqual((kn["business_id"], kn["tags"]), ("biz_buildflow", "experiment"))
        ev = self.rows("SELECT * FROM evidence WHERE knowledge_id=?", (kn["id"],))[0]
        self.assertEqual(ev["label"], "assumed")  # never verified without an independent source
        src = self.rows("SELECT * FROM sources WHERE id=?", (ev["source_id"],))[0]
        self.assertEqual((src["kind"], src["reliability"]), ("internal", "unknown"))
        ov = self.call("GET", "/api/knowledge/buildflow")[1]
        self.assertEqual(next(k for k in ov["knowledge"] if k["id"] == kn["id"])["trust"], "assumed")
        # the other business sees none of it
        self.assertEqual(self.call("GET", "/api/knowledge/agriloop")[1]["knowledge"], [])
        # promoting it still needs a real source via the normal evidence flow
        self.assertEqual(self.call("POST", f"/api/founder/evidence/{ev['id']}", {"label": "verified", "source_id": None})[0], 400)


class GrowthTest(Base):
    def test_buildflow_funnel_uses_only_recorded_numbers(self):
        f = growth.funnel(self.conn, "buildflow")
        self.assertIsNone(next(s for s in f["stages"] if s["key"] == "views")["value"])  # untracked is null, not 0
        self.assertIsNone(f["rates"][0]["rate_pct"])
        self.mk("content-items", platform="tiktok", status="posted", views=1000, signups=20)
        self.mk("content-items", platform="tiktok", status="posted", views=500)  # no signups recorded: excluded from the rate
        self.mk("content-items", platform="tiktok", status="idea", views=9999, signups=999)  # not posted: ignored
        f = growth.funnel(self.conn, "buildflow")
        st = {s["key"]: s["value"] for s in f["stages"]}
        self.assertEqual((st["posts"], st["views"], st["signups"]), (2, 1500, 20))
        r = f["rates"][0]
        self.assertEqual((r["rate_pct"], r["sample"], r["small_sample"]), (2.0, 1, True))

    def test_funnels_are_scoped_per_business_and_trading_has_none(self):
        self.mk("content-items", platform="tiktok", status="posted", views=10, signups=1)
        self.assertEqual({s["key"]: s["value"] for s in growth.funnel(self.conn, "fashion")["stages"]}["sales"], 0)
        t = growth.funnel(self.conn, "trading")
        self.assertIsNone(t["stages"])
        self.assertIn("no growth funnel", t["reason"])
        with self.assertRaises(founder.NotFound):
            growth.funnel(self.conn, "nope")

    def test_agriloop_and_fashion_funnels(self):
        f1 = self.mk("market-parties", slug="agriloop", name="A", role="farmer", status="active")
        self.mk("market-parties", slug="agriloop", name="B", role="farmer", status="lead")
        self.mk("market-parties", slug="agriloop", name="C", role="buyer", status="onboarded")
        st = {s["key"]: s["value"] for s in growth.funnel(self.conn, "agriloop")["stages"]}
        self.assertEqual((st["farmers"], st["farmers_onboarded"], st["farmers_active"], st["buyers_onboarded"]), (2, 1, 1, 1))
        p = self.mk("shop-products", slug="fashion", name="Tee")
        for ref in ("c1", "c1", "c2"):
            self.mk("shop-sales", slug="fashion", product_id=p["id"], quantity=1, revenue=10, currency="USD", customer_ref=ref)
        fz = growth.funnel(self.conn, "fashion")
        self.assertEqual({s["key"]: s["value"] for s in fz["stages"]}["repeat_customers"], 1)
        self.assertEqual(fz["rates"][0]["rate_pct"], 50.0)

    def test_api_returns_funnel_experiments_and_ready_flag(self):
        e = self.exp(duration_days=1)
        self.act(e["id"], "start")
        self.conn.execute("ALTER TABLE experiments DISABLE TRIGGER experiments_lifecycle")
        self.conn.execute("UPDATE experiments SET started_at='2020-01-01T00:00:00+00:00' WHERE id=?", (e["id"],))
        d = self.call("GET", "/api/growth/buildflow")[1]
        self.assertEqual((d["counts"]["running"], d["ready_to_conclude"], d["funnel"]["business"]), (1, [e["id"]], "buildflow"))
        self.assertEqual(self.call("GET", "/api/growth/agriloop")[1]["experiments"], [])


class MigrationTest(unittest.TestCase):
    def test_experiments_carry_new_columns_and_inconclusive_status(self):
        conn = make_conn()
        cols = {r["column_name"] for r in conn.execute("SELECT column_name FROM information_schema.columns WHERE table_name='experiments' AND table_schema=current_schema()")}
        self.assertLessEqual({"kpi_id", "duration_days", "min_sample", "sample_size", "result_value", "decision", "learning_knowledge_id"}, cols)


if __name__ == "__main__":
    unittest.main()
