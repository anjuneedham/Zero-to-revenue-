import json
import os
import unittest
from pathlib import Path
from unittest import mock

import dashboard.app as dash
from core import db, ventures as v
from tests.authutil import session
from tests.dbutil import make_conn
from tests.unit.test_phases_3_6 import ENV

ROOT = Path(__file__).resolve().parents[2]


class VenturesCoreTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()

    def test_migration_seeds_four_ventures_and_weekly_plan(self):
        ids = {r["id"] for r in self.conn.execute("SELECT id FROM ventures")}
        self.assertEqual(ids, {"buildflow", "agriloop", "ecommerce", "trading"})
        days = {(r["venture_id"], r["weekday"]) for r in self.conn.execute("SELECT * FROM venture_allocation")}
        self.assertEqual(days, {("buildflow", 1), ("agriloop", 2), ("trading", 3), ("ecommerce", 4), ("buildflow", 5), ("agriloop", 6)})

    def test_migration_is_idempotent_and_reversible(self):
        self.assertEqual(db.migrate(self.conn), [])
        self.conn.execute("INSERT INTO ventures(id,name,created_at) VALUES ('x','X','t')")
        seed = (ROOT / "database/migrations/007_ventures.sql").read_text().split("INSERT INTO ventures", 1)[1]
        self.conn.raw.execute("INSERT INTO ventures" + seed)  # seed block is conflict-safe: no duplicates, no error
        self.assertEqual(self.conn.execute("SELECT count(*) n FROM ventures").fetchone()["n"], 5)
        self.conn.raw.execute((ROOT / "database/migrations/down/007_ventures_down.sql").read_text())
        self.assertIsNone(self.conn.execute("SELECT to_regclass('ventures') r").fetchone()["r"])
        self.assertEqual(self.conn.execute("SELECT count(*) n FROM opportunities").fetchone()["n"], 0)  # old tables untouched

    def test_down_script_is_not_picked_up_by_the_runner(self):
        self.assertEqual([f.name for f in db.MIGRATIONS.glob("*.sql")].count("007_ventures_down.sql"), 0)

    def test_task_lifecycle_and_validation(self):
        t = v.add_task(self.conn, "o", "buildflow", "Enable Storage", "founder", "2026-11-01")["id"]
        v.update_task(self.conn, "o", t, "DOING")
        with self.assertRaises(v.VentureError):
            v.update_task(self.conn, "o", t, "BLOCKED")  # needs a reason
        v.update_task(self.conn, "o", t, "BLOCKED", "waiting on card")
        v.update_task(self.conn, "o", t, "DONE")
        self.assertEqual(v.venture_detail(self.conn, "buildflow")["tasks"][0]["status"], "DONE")
        for bad in (dict(title=""), dict(title="x" * 201), dict(title="ok", who="bot"), dict(title="ok", due_at="soon")):
            with self.assertRaises(v.VentureError):
                v.add_task(self.conn, "o", "buildflow", bad["title"], bad.get("who", "founder"), bad.get("due_at"))
        with self.assertRaises(v.VentureError):
            v.add_task(self.conn, "o", "nope", "t")
        with self.assertRaises(v.VentureError):
            v.add_task(self.conn, "o", "x'; drop table ventures;--", "t")

    def test_killing_a_venture_needs_a_reason_and_logs_a_decision(self):
        with self.assertRaises(v.VentureError):
            v.set_stage(self.conn, "o", "trading", "KILLED")
        v.set_stage(self.conn, "o", "trading", "KILLED", "negative expectancy")
        d = v.venture_detail(self.conn, "trading")["decisions"][0]
        self.assertEqual((d["decision"], d["rationale"], d["status"]), ("Killed", "negative expectancy", "DECIDED"))
        self.assertEqual(v.overview(self.conn)["ventures"][-1]["id"], "trading")  # killed sorts last
        with self.assertRaises(v.VentureError):
            v.set_stage(self.conn, "o", "trading", "LAUNCHED")

    def test_decisions_resolve_once(self):
        d = v.add_decision(self.conn, "o", "Which store is the brand?", "ecommerce")["id"]
        self.assertEqual(len(v.overview(self.conn)["open_decisions"]), 1)
        v.resolve_decision(self.conn, "o", d, "Kadeform", "single hero product")
        with self.assertRaises(v.VentureError):
            v.resolve_decision(self.conn, "o", d, "Other")
        self.assertEqual(v.overview(self.conn)["open_decisions"], [])

    def test_experiments_must_record_what_was_learned(self):
        e = v.add_experiment(self.conn, "o", "buildflow", "DM 20 plumbers", "replies", ">=3")["id"]
        v.update_experiment(self.conn, "o", e, "RUNNING")
        with self.assertRaises(v.VentureError):
            v.update_experiment(self.conn, "o", e, "FAILED")
        v.update_experiment(self.conn, "o", e, "FAILED", "0 replies; wrong channel")
        row = v.venture_detail(self.conn, "buildflow")["experiments"][0]
        self.assertEqual((row["status"], row["result"]), ("FAILED", "0 replies; wrong channel"))
        self.assertIsNotNone(row["closed_at"])

    def test_metrics_latest_value_and_validation(self):
        v.record_metric(self.conn, "o", "buildflow", "contractors_contacted", 5)
        v.record_metric(self.conn, "o", "buildflow", "contractors_contacted", 9)
        m = v.overview(self.conn)["ventures"][0]["metrics"]
        self.assertEqual([(x["name"], x["value"]) for x in m], [("contractors_contacted", 9.0)])
        for name, val in (("Bad Name", 1), ("ok", "1"), ("ok", True), ("ok", float("nan")), ("ok", 1e13)):
            with self.assertRaises(v.VentureError):
                v.record_metric(self.conn, "o", "buildflow", name, val)

    def test_metrics_do_not_touch_revenue(self):
        v.record_metric(self.conn, "o", "buildflow", "revenue_usd", 5000)
        self.assertEqual(self.conn.execute("SELECT count(*) n FROM ledger_entries").fetchone()["n"], 0)
        self.assertEqual(self.conn.execute("SELECT count(*) n FROM payments").fetchone()["n"], 0)

    def test_effort_is_bounded_and_labelled_self_reported(self):
        v.log_effort(self.conn, "o", "agriloop", 3.5, 2, "fixed adapter")
        self.assertEqual(self.conn.execute("SELECT source FROM effort_logs").fetchone()["source"], "self_reported")
        for h, s in ((25, 0), (-1, 0), (1, -1), (True, 0)):
            with self.assertRaises(v.VentureError):
                v.log_effort(self.conn, "o", "agriloop", h, s)
        with self.assertRaises(v.VentureError):
            v.log_effort(self.conn, "o", "agriloop", 1, 0, None, "yesterday")
        eff = v.overview(self.conn)["effort_this_week"]
        self.assertEqual(eff[0]["hours"], 3.5)

    def test_every_write_is_audited(self):
        t = v.add_task(self.conn, "owner1", "buildflow", "x")["id"]
        v.update_task(self.conn, "owner1", t, "DONE")
        v.add_decision(self.conn, "owner1", "q")
        acts = [r["action"] for r in self.conn.execute("SELECT action FROM audit_events WHERE actor='owner1' ORDER BY id")]
        self.assertEqual(acts, ["venture.task_add", "venture.task_update", "venture.decision_add"])


class VenturesApiTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.env = mock.patch.dict(os.environ, ENV, clear=True)
        self.env.start()
        self.tok, _, _ = session(self.conn)

    def tearDown(self):
        self.env.stop()

    def call(self, method, path, body=None, auth=True, raw=None):
        c, _, out = dash.handle(method, path, f"Bearer {self.tok}" if auth else None, self.conn,
                                raw if raw is not None else (json.dumps(body).encode() if body is not None else b""))
        return c, json.loads(out)

    def test_requires_login(self):
        for m, p in (("GET", "/api/ventures"), ("GET", "/api/ventures/buildflow"), ("POST", "/api/ventures/buildflow/tasks"),
                     ("POST", "/api/decisions"), ("POST", "/api/tasks/vt_000000000000")):
            self.assertEqual(self.call(m, p, auth=False)[0], 401, p)

    def test_end_to_end(self):
        c, d = self.call("GET", "/api/ventures")
        self.assertEqual((c, [x["id"] for x in d["ventures"]]), (200, ["buildflow", "agriloop", "ecommerce", "trading"]))
        c, t = self.call("POST", "/api/ventures/buildflow/tasks", {"title": "Call 5 contractors", "owner": "founder"})
        self.assertEqual(c, 200)
        self.assertEqual(self.call("POST", "/api/tasks/" + t["id"], {"status": "DONE"})[0], 200)
        c, _ = self.call("POST", "/api/ventures/buildflow/metrics", {"name": "demos", "value": 2})
        self.assertEqual(c, 200)
        c, _ = self.call("POST", "/api/ventures/buildflow/effort", {"hours": 2, "claude_sessions": 1})
        self.assertEqual(c, 200)
        c, e = self.call("POST", "/api/ventures/buildflow/experiments", {"hypothesis": "WhatsApp beats email"})
        self.assertEqual(self.call("POST", "/api/experiments/" + e["id"], {"status": "RUNNING"})[0], 200)
        c, dec = self.call("POST", "/api/decisions", {"venture_id": "ecommerce", "question": "Which brand?"})
        self.assertEqual(self.call("POST", "/api/decisions/" + dec["id"], {"decision": "Kadeform"})[0], 200)
        c, detail = self.call("GET", "/api/ventures/buildflow")
        self.assertEqual((detail["tasks"][0]["status"], detail["metrics"][0]["name"], len(detail["experiments"])), ("DONE", "demos", 1))

    def test_bad_input_is_a_400_not_a_500(self):
        self.assertEqual(self.call("POST", "/api/ventures/buildflow/tasks", {"title": ""})[0], 400)
        self.assertEqual(self.call("POST", "/api/ventures/buildflow/tasks", raw=b"not json")[0], 400)
        self.assertEqual(self.call("POST", "/api/ventures/buildflow/tasks", raw=b"[1]")[0], 400)
        self.assertEqual(self.call("POST", "/api/ventures/buildflow/tasks", raw=b"x" * 5000)[0], 400)
        self.assertEqual(self.call("POST", "/api/ventures/buildflow/stage", {"stage": "KILLED"})[0], 400)
        self.assertEqual(self.call("GET", "/api/ventures/nope")[0], 400)
        self.assertEqual(self.call("POST", "/api/ventures/buildflow/metrics", {"name": "a", "value": "x"})[0], 400)
        self.assertEqual(self.call("GET", "/api/ventures/buildflow/tasks")[0], 404)

    def test_script_in_text_is_stored_verbatim_as_data(self):
        c, t = self.call("POST", "/api/ventures/buildflow/tasks", {"title": "<script>alert(1)</script>"})
        self.assertEqual(self.call("GET", "/api/ventures/buildflow")[1]["tasks"][0]["title"], "<script>alert(1)</script>")
        js = (ROOT / "dashboard/static/js/ventures.js").read_text()
        self.assertNotIn("innerHTML", js)


class VenturesUiTest(unittest.TestCase):
    def test_page_is_wired_and_cached(self):
        self.assertIn("/js/ventures.js", (ROOT / "dashboard/pages/index.html").read_text())
        self.assertIn("/js/ventures.js", (ROOT / "dashboard/static/sw.js").read_text())
        self.assertIn('"ventures"', (ROOT / "dashboard/static/js/main.js").read_text())
        self.assertIsNotNone(dash.static_file("/js/ventures.js"))
