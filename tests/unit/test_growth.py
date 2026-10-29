"""Phase 9: experiment lifecycle, decision/learning write-back, funnels from real data. No model is involved."""

import json
import unittest
from datetime import datetime, timedelta, timezone

from core import founder, growth, knowledge
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

    def exp(self, slug="buildflow", **kw):
        code, d = self.call("POST", f"/api/founder/businesses/{slug}/experiments", {"hypothesis": "Shorter hooks raise signups", "success_metric": "signups/week", "duration_days": 14, **kw})
        self.assertEqual(code, 201, d)
        return d

    def rows(self, sql, p=()):
        return [dict(r) for r in self.conn.execute(sql, p).fetchall()]


class Lifecycle(Base):
    def test_new_experiment_is_proposed_and_status_is_locked(self):
        e = self.exp()
        self.assertEqual(e["status"], "proposed")
        for body in ({"status": "running"}, {"result": "won"}, {"learnings": "x"}):
            code, d = self.call("POST", f"/api/founder/experiments/{e['id']}", body)
            self.assertEqual(code, 400, body)
        code, _ = self.call("POST", "/api/founder/businesses/buildflow/experiments", {"hypothesis": "h", "status": "succeeded"})
        self.assertEqual(code, 400)
        code, _ = self.call("POST", f"/api/founder/experiments/{e['id']}", {"success_metric": "new metric"})
        self.assertEqual(code, 200)

    def test_start_needs_metric_and_duration(self):
        code, e = self.call("POST", "/api/founder/businesses/buildflow/experiments", {"hypothesis": "h"})
        self.assertEqual(code, 201)
        code, d = self.call("POST", f"/api/growth/experiments/{e['id']}/start")
        self.assertEqual(code, 400)
        self.call("POST", f"/api/founder/experiments/{e['id']}", {"success_metric": "m"})
        code, d = self.call("POST", f"/api/growth/experiments/{e['id']}/start")
        self.assertEqual(code, 400, d)  # still no duration
        self.call("POST", f"/api/founder/experiments/{e['id']}", {"duration_days": 7})
        code, d = self.call("POST", f"/api/growth/experiments/{e['id']}/start")
        self.assertEqual(code, 200, d)
        self.assertEqual((d["status"], bool(d["started_at"]), bool(d["ends_at"])), ("running", True, True))
        self.assertEqual(self.call("POST", f"/api/growth/experiments/{e['id']}/start")[0], 400)  # not twice

    def test_start_snapshots_kpi_baseline_only_if_recorded(self):
        k = self.call("POST", "/api/founder/businesses/buildflow/kpis", {"name": "Signups"})[1]
        e = self.exp(metric_kpi_id=k["id"])
        self.assertIsNone(self.call("POST", f"/api/growth/experiments/{e['id']}/start")[1]["baseline_value"])  # KPI had no value: stays null, not 0
        k2 = self.call("POST", "/api/founder/businesses/buildflow/kpis", {"name": "Trials"})[1]
        self.call("POST", f"/api/founder/kpis/{k2['id']}/readings", {"value": 12})
        e2 = self.exp(metric_kpi_id=k2["id"])
        self.assertEqual(float(self.call("POST", f"/api/growth/experiments/{e2['id']}/start")[1]["baseline_value"]), 12.0)

    def test_metric_kpi_must_be_same_business(self):
        k = self.call("POST", "/api/founder/businesses/agriloop/kpis", {"name": "Farmers"})[1]
        code, d = self.call("POST", "/api/founder/businesses/buildflow/experiments", {"hypothesis": "h", "metric_kpi_id": k["id"]})
        self.assertEqual(code, 400, d)

    def test_conclude_requires_running_and_complete_fields(self):
        e = self.exp()
        full = {"outcome": "succeeded", "result": "Signups up", "decision": "adopt", "learnings": "Short hooks work"}
        self.assertEqual(self.call("POST", f"/api/growth/experiments/{e['id']}/conclude", full)[0], 400)  # still proposed
        self.call("POST", f"/api/growth/experiments/{e['id']}/start")
        for bad in ({**full, "outcome": "won"}, {**full, "decision": "ship"}, {**full, "result": ""}, {**full, "learnings": ""}, {**full, "result_value": "abc"}):
            self.assertEqual(self.call("POST", f"/api/growth/experiments/{e['id']}/conclude", bad)[0], 400, bad)
        self.assertEqual(self.rows("SELECT status FROM experiments WHERE id=?", (e["id"],))[0]["status"], "running")
        self.assertEqual(self.rows("SELECT count(*) AS n FROM knowledge WHERE tags LIKE '%experiment%'")[0]["n"], 0)

    def test_conclude_writes_decision_and_assumed_learning(self):
        e = self.exp()
        self.call("POST", f"/api/growth/experiments/{e['id']}/start")
        code, d = self.call("POST", f"/api/growth/experiments/{e['id']}/conclude",
                            {"outcome": "failed", "result": "No change", "result_value": 3, "decision": "stop", "decision_rationale": "No lift in 14 days", "learnings": "Hook length is not the lever"})
        self.assertEqual(code, 200, d)
        self.assertEqual((d["experiment"]["status"], d["experiment"]["result_source"], d["evidence_label"]), ("failed", "entered", "assumed"))
        dec = self.rows("SELECT * FROM decisions WHERE id=?", (d["decision_id"],))[0]
        self.assertEqual((dec["business_id"], dec["status"], dec["decision"]), ("biz_buildflow", "decided", "stop"))
        kn = self.rows("SELECT * FROM knowledge WHERE id=?", (d["knowledge_id"],))[0]
        self.assertEqual(kn["business_id"], "biz_buildflow")
        ev = self.rows("SELECT * FROM evidence WHERE knowledge_id=?", (kn["id"],))[0]
        self.assertEqual((ev["label"], ev["source_id"]), ("assumed", None))  # an experiment result is never "verified" by itself
        self.assertEqual(knowledge.overview(self.conn, "buildflow")["knowledge"][0]["trust"], "assumed")
        self.assertEqual(self.call("POST", f"/api/growth/experiments/{e['id']}/conclude", {"outcome": "failed", "result": "r", "decision": "stop", "learnings": "l"})[0], 400)  # once only
        self.assertEqual(self.rows("SELECT count(*) AS n FROM decisions WHERE id=?", (d["decision_id"],))[0]["n"], 1)
        self.assertEqual(self.rows("SELECT count(*) AS n FROM audit_events WHERE action='growth.experiment.conclude'")[0]["n"], 1)

    def test_conclude_with_source_is_verified_and_source_must_match_business(self):
        e = self.exp()
        self.call("POST", f"/api/growth/experiments/{e['id']}/start")
        other = self.call("POST", "/api/founder/businesses/agriloop/sources", {"title": "Other biz"})[1]
        body = {"outcome": "succeeded", "result": "Up 20%", "decision": "adopt", "learnings": "Works", "source_id": other["id"]}
        self.assertEqual(self.call("POST", f"/api/growth/experiments/{e['id']}/conclude", body)[0], 400)
        mine = self.call("POST", "/api/founder/businesses/buildflow/sources", {"title": "Analytics export", "reliability": "high"})[1]
        code, d = self.call("POST", f"/api/growth/experiments/{e['id']}/conclude", {**body, "source_id": mine["id"]})
        self.assertEqual((code, d["evidence_label"]), (200, "verified"), d)

    def test_result_value_falls_back_to_recorded_kpi_and_says_so(self):
        k = self.call("POST", "/api/founder/businesses/buildflow/kpis", {"name": "Signups"})[1]
        e = self.exp(metric_kpi_id=k["id"])
        self.call("POST", f"/api/growth/experiments/{e['id']}/start")
        self.call("POST", f"/api/founder/kpis/{k['id']}/readings", {"value": 40})
        d = self.call("POST", f"/api/growth/experiments/{e['id']}/conclude", {"outcome": "succeeded", "result": "r", "decision": "iterate", "learnings": "l"})[1]
        self.assertEqual((float(d["experiment"]["result_value"]), d["experiment"]["result_source"]), (40.0, "kpi"))
        e2 = self.exp()  # no KPI, no value entered: stays null
        self.call("POST", f"/api/growth/experiments/{e2['id']}/start")
        d2 = self.call("POST", f"/api/growth/experiments/{e2['id']}/conclude", {"outcome": "succeeded", "result": "r", "decision": "iterate", "learnings": "l"})[1]
        self.assertIsNone(d2["experiment"]["result_value"])

    def test_abandon(self):
        e = self.exp()
        self.assertEqual(self.call("POST", f"/api/growth/experiments/{e['id']}/abandon", {})[0], 400)  # reason required
        code, d = self.call("POST", f"/api/growth/experiments/{e['id']}/abandon", {"reason": "No traffic to test with"})
        self.assertEqual((code, d["status"]), (200, "abandoned"))
        self.assertEqual(self.call("POST", f"/api/growth/experiments/{e['id']}/abandon", {"reason": "again"})[0], 400)
        self.assertEqual(self.call("POST", f"/api/growth/experiments/{e['id']}/start")[0], 400)

    def test_overdue_is_flagged_not_auto_concluded(self):
        e = self.exp(duration_days=1)
        self.call("POST", f"/api/growth/experiments/{e['id']}/start")
        old = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        self.conn.execute("UPDATE experiments SET started_at=? WHERE id=?", (old, e["id"]))
        o = self.call("GET", "/api/growth/buildflow")[1]
        self.assertEqual(o["overdue"], [e["id"]])
        self.assertEqual(o["experiments"][0]["status"], "running")

    def test_unknown_ids_and_auth(self):
        self.assertEqual(self.call("POST", "/api/growth/experiments/nope/start")[0], 404)
        self.assertEqual(self.call("GET", "/api/growth/nobiz")[0], 404)
        code, _, _ = handle("GET", "/api/growth/buildflow", "", self.conn, b"")
        self.assertEqual(code, 401)


class Funnels(Base):
    def mk(self, ent, slug="buildflow", **b):
        code, d = self.call("POST", f"/api/founder/businesses/{slug}/{ent.replace(chr(95), chr(45))}", b)
        self.assertEqual(code, 201, d)
        return d

    def test_empty_business_has_no_funnels_and_no_invented_numbers(self):
        o = self.call("GET", "/api/growth/buildflow")[1]
        self.assertEqual(o["funnels"], [])

    def test_content_funnel_counts_real_rows_and_skips_unentered_metrics(self):
        for st in ("idea", "scripted", "posted", "posted"):
            self.mk("content_items", platform="tiktok", status=st)
        posted = self.rows("SELECT id FROM content_items WHERE status='posted' ORDER BY id")
        self.call("POST", f"/api/founder/content-items/{posted[0]['id']}", {"views": 1000, "signups": 10})
        f = next(x for x in self.call("GET", "/api/growth/buildflow")[1]["funnels"] if x["name"] == "Content to signups")
        by = {s["label"]: s["count"] for s in f["steps"]}
        self.assertEqual((by["idea"], by["scripted"], by["filmed"], by["posted"]), (4, 3, 2, 2))
        self.assertEqual((by["views (posts where entered)"], by["signups (posts where entered)"]), (1000, 10))
        self.assertEqual((f["coverage"]["posted"], f["coverage"]["posts_with_views"]), (2, 1))

    def test_marketplace_funnels_are_per_role_and_business_scoped(self):
        self.mk("market_parties", "agriloop", name="F1", role="farmer", status="lead")
        self.mk("market_parties", "agriloop", name="F2", role="farmer", status="active")
        self.mk("market_parties", "agriloop", name="B1", role="buyer", status="lead")
        fs = {x["name"]: x for x in self.call("GET", "/api/growth/agriloop")[1]["funnels"]}
        self.assertEqual([s["count"] for s in fs["Farmer onboarding"]["steps"]], [2, 1, 1])
        self.assertEqual([s["count"] for s in fs["Buyer onboarding"]["steps"]], [1, 0, 0])
        self.assertEqual(self.call("GET", "/api/growth/buildflow")[1]["funnels"], [])  # no leak across businesses

    def test_shop_totals_come_from_rows(self):
        self.mk("shop_campaigns", "fashion", name="Reel push", status="done", spend=50, orders=3, attributed_revenue=120)
        f = next(x for x in self.call("GET", "/api/growth/fashion")[1]["funnels"] if x["name"] == "Shop campaigns")
        self.assertEqual((float(f["totals"]["spend"]), f["totals"]["orders"]), (50.0, 3))

    def test_kpi_trend_change_needs_two_readings(self):
        k = self.mk("kpis", name="MRR")
        self.call("POST", f"/api/founder/kpis/{k['id']}/readings", {"value": 10})
        self.assertIsNone(self.call("GET", "/api/growth/buildflow")[1]["kpis"][0]["change"])
        self.call("POST", f"/api/founder/kpis/{k['id']}/readings", {"value": 25})
        self.assertEqual(float(self.call("GET", "/api/growth/buildflow")[1]["kpis"][0]["change"]), 15.0)


class Migration(Base):
    def test_migration_applies_and_old_rows_remain_valid(self):
        cols = {r["column_name"] for r in self.rows("SELECT column_name FROM information_schema.columns WHERE table_name='experiments' AND table_schema=current_schema()")}
        for c in ("metric_kpi_id", "duration_days", "result_value", "decision", "decision_id", "knowledge_id"):
            self.assertIn(c, cols)
        with self.assertRaises(Exception):  # CHECK duration_days BETWEEN 1 AND 365
            self.conn.execute("INSERT INTO experiments(id,business_id,hypothesis,duration_days,created_at,updated_at) VALUES ('x','biz_buildflow','h',0,'t','t')")


if __name__ == "__main__":
    unittest.main()
