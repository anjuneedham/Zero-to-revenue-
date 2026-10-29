import json
import unittest

from core import trading_eval as te
from dashboard.app import handle
from tests.authutil import session
from tests.dbutil import make_conn


def run(mode="backtest", **kw):
    base = dict(mode=mode, trades=100, net_return_pct=12.0, max_drawdown_pct=8.0, costs_included=1, slippage_bps=2.0, period_start=None, period_end=None)
    return {**base, **kw}


FULL = dict(hypothesis="mean reversion after spikes", data_notes="Deriv ticks, gaps checked", failure_conditions="stop if paper DD > 15%", risk_notes="1% risk per trade",
            max_drawdown_limit_pct=15.0, min_trades=None)


class EvalTest(unittest.TestCase):
    def test_empty_strategy_lists_everything_missing_and_never_claims_success(self):
        e = te.evaluate({}, [])
        self.assertEqual(len(e["missing"]), len(e["checklist"]))
        self.assertIn("still missing", e["verdict"])

    def test_complete_evidence_still_makes_no_profit_claim(self):
        runs = [run(), run("out_of_sample"), run("walk_forward"), run("paper", period_start="2026-08-01", period_end="2026-09-15")]
        e = te.evaluate(FULL, runs)
        self.assertEqual(e["missing"], [])
        self.assertIn("not a prediction of profit", e["verdict"])
        self.assertIn("outside this system", e["verdict"])

    def test_backtest_alone_is_not_validation(self):
        e = te.evaluate(FULL, [run()])
        self.assertIn("an out-of-sample result", e["missing"])
        self.assertIn("a walk-forward result", e["missing"])

    def test_paper_needs_enough_days_and_costs_are_not_required_for_paper(self):
        short = te.evaluate(FULL, [run("paper", period_start="2026-10-01", period_end="2026-10-10", costs_included=None, slippage_bps=None)])
        self.assertTrue(any("paper run" in m for m in short["missing"]))
        self.assertEqual(short["paper_days_recorded"], 9)
        self.assertEqual(te.run_warnings(run("paper", costs_included=None, slippage_bps=None), FULL), [])

    def test_breach_of_recorded_drawdown_limit(self):
        e = te.evaluate(FULL, [run("paper", max_drawdown_pct=22.0)])
        self.assertEqual(len(e["breaches"]), 1)
        self.assertIn("PAPER", e["breaches"][0])
        self.assertIn("breached", e["verdict"])
        self.assertEqual(te.evaluate({**FULL, "max_drawdown_limit_pct": None}, [run(max_drawdown_pct=99.0)])["breaches"], [])

    def test_run_warnings(self):
        w = te.run_warnings(run(trades=5, costs_included=0, slippage_bps=None, max_drawdown_pct=None), FULL)
        joined = " ".join(w)
        for needle in ("only 5 trade", "costs/fees", "slippage", "drawdown not recorded", "not evidence of future profit"):
            self.assertIn(needle, joined)
        self.assertIn("trade count not recorded", " ".join(te.run_warnings(run(trades=None), FULL)))
        self.assertNotIn("not evidence", " ".join(te.run_warnings(run("out_of_sample"), FULL)))


class TradingApiTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.tok = session(self.conn)[0]

    def call(self, method, path, body=None):
        c, _, out = handle(method, path, f"Bearer {self.tok}", self.conn, json.dumps(body).encode() if body is not None else b"")
        return c, json.loads(out)

    def make(self, biz, entity, **body):
        c, r = self.call("POST", f"/api/founder/businesses/{biz}/{entity}", body)
        self.assertEqual(c, 201, r)
        return r

    def lab(self):
        return self.call("GET", "/api/founder/workspace/trading")[1]["research_lab"]

    def test_empty_lab_and_no_live_trading_anywhere(self):
        lab = self.lab()
        self.assertEqual(lab["strategies"], [])
        self.assertIn("no live mode", lab["live_trading"])
        self.assertNotIn("research_lab", self.call("GET", "/api/founder/workspace/buildflow")[1])

    def test_live_mode_and_live_status_cannot_be_stored(self):
        s = self.make("trading", "trading-strategies", name="S1")
        for bad in ({"strategy_id": s["id"], "mode": "live"}, {"strategy_id": s["id"], "mode": "paper ", "trades": -1}):
            self.assertEqual(self.call("POST", "/api/founder/businesses/trading/trading-runs", bad)[0], 400, bad)
        for status in ("live", "deployed", "funded"):
            self.assertEqual(self.call("POST", "/api/founder/businesses/trading/trading-strategies", {"name": "x", "status": status})[0], 400, status)
        with self.assertRaises(Exception):  # the database itself refuses it too
            self.conn.execute("INSERT INTO trading_runs(id,business_id,strategy_id,mode,created_at) VALUES ('x','biz_trading',?,'live','t')", (s["id"],))

    def test_runs_are_append_only_and_modes_stay_separate(self):
        s = self.make("trading", "trading-strategies", name="S1", **{"max_drawdown_limit_pct": 15, "failure_conditions": "x"})
        r = self.make("trading", "trading-runs", strategy_id=s["id"], mode="backtest", trades=200, net_return_pct=40, max_drawdown_pct=9, costs_included=True, slippage_bps=1)
        self.make("trading", "trading-runs", strategy_id=s["id"], mode="paper", trades=10, net_return_pct=-3, max_drawdown_pct=20, period_start="2026-10-01", period_end="2026-10-10")
        self.assertEqual(self.call("POST", f"/api/founder/trading-runs/{r['id']}", {"net_return_pct": 99})[0], 400)
        st = self.lab()["strategies"][0]
        self.assertEqual(st["evaluation"]["counts"], {"backtest": 1, "out_of_sample": 0, "walk_forward": 0, "paper": 1})
        self.assertEqual(len(st["evaluation"]["breaches"]), 1)
        self.assertTrue(any(x["mode_label"] == "PAPER" and x["warnings"] for x in st["runs"]))
        self.assertIn("breached", st["evaluation"]["verdict"])

    def test_isolation_and_validation(self):
        s = self.make("trading", "trading-strategies", name="S1")
        self.assertEqual(self.call("POST", "/api/founder/businesses/agriloop/trading-runs", {"strategy_id": s["id"], "mode": "paper"})[0], 400)
        for body in ({"name": "x", "max_drawdown_limit_pct": 0}, {"name": "x", "max_drawdown_limit_pct": 150}, {"name": "x", "min_trades": 0}, {"name": ""}):
            self.assertEqual(self.call("POST", "/api/founder/businesses/trading/trading-strategies", body)[0], 400, body)
        self.assertEqual(self.call("POST", "/api/founder/businesses/trading/trading-runs", {"strategy_id": s["id"], "mode": "paper", "max_drawdown_pct": 150})[0], 400)


if __name__ == "__main__":
    unittest.main()
