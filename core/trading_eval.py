"""Research-only evaluation of recorded trading strategies and runs. Deterministic, read-only, no market data, no orders.

It never says a strategy will make money. It lists what is MISSING or WORRYING in the recorded evidence and which recorded
failure conditions were breached. Modes are kept apart: a backtest is never counted as validation or as paper performance.
"""

MIN_PAPER_RUN_DAYS = 30  # a documented rule of thumb for this checklist, not a statistical guarantee
DEFAULT_MIN_TRADES = 30
MODES = ("backtest", "out_of_sample", "walk_forward", "paper")
LABEL = {"backtest": "BACKTEST (in-sample)", "out_of_sample": "OUT-OF-SAMPLE", "walk_forward": "WALK-FORWARD", "paper": "PAPER"}


def _days(a, b):
    from datetime import date
    try:
        return (date.fromisoformat(b[:10]) - date.fromisoformat(a[:10])).days
    except (ValueError, TypeError):
        return None


def run_warnings(run: dict, strategy: dict) -> list[str]:
    w = []
    need = strategy.get("min_trades") or DEFAULT_MIN_TRADES
    if run["trades"] is None:
        w.append("trade count not recorded")
    elif run["trades"] < need:
        w.append(f"only {run['trades']} trade(s) (< {need}): too few to say anything reliable")
    if run["mode"] != "paper" and run["costs_included"] != 1:
        w.append("costs/fees not confirmed as included: result is probably optimistic")
    if run["mode"] != "paper" and run["slippage_bps"] is None:
        w.append("no slippage assumption recorded")
    if run["max_drawdown_pct"] is None:
        w.append("max drawdown not recorded")
    if run["net_return_pct"] is not None and run["net_return_pct"] > 0 and run["mode"] == "backtest":
        w.append("positive in-sample backtest: not evidence of future profit")
    return w


def evaluate(strategy: dict, runs: list[dict]) -> dict:
    """Returns breached failure conditions, readiness gaps and per-mode counts for one strategy."""
    by_mode = {m: [r for r in runs if r["mode"] == m] for m in MODES}
    breaches = []
    lim = strategy.get("max_drawdown_limit_pct")
    if lim is not None:
        for r in runs:
            if r["max_drawdown_pct"] is not None and r["max_drawdown_pct"] > lim:
                breaches.append(f"{LABEL[r['mode']]} run drawdown {r['max_drawdown_pct']:g}% exceeds your limit of {lim:g}%")
    paper_days = max([d for d in (_days(r["period_start"], r["period_end"]) for r in by_mode["paper"] if r["period_start"] and r["period_end"]) if d is not None], default=None)
    checks = [
        ("hypothesis written down", bool((strategy.get("hypothesis") or "").strip())),
        ("market data source and quality notes recorded", bool((strategy.get("data_notes") or "").strip())),
        ("explicit failure conditions recorded", bool((strategy.get("failure_conditions") or "").strip())),
        ("a maximum drawdown limit set", lim is not None),
        ("risk notes (position sizing, exposure) recorded", bool((strategy.get("risk_notes") or "").strip())),
        ("a backtest with costs and slippage confirmed", any(r["costs_included"] == 1 and r["slippage_bps"] is not None for r in by_mode["backtest"])),
        ("an out-of-sample result", bool(by_mode["out_of_sample"])),
        ("a walk-forward result", bool(by_mode["walk_forward"])),
        (f"a paper run of at least {MIN_PAPER_RUN_DAYS} days", paper_days is not None and paper_days >= MIN_PAPER_RUN_DAYS),
    ]
    missing = [name for name, ok in checks if not ok]
    return {"counts": {m: len(by_mode[m]) for m in MODES}, "breaches": breaches, "checklist": [{"item": n, "done": ok} for n, ok in checks], "missing": missing,
            "verdict": ("A recorded failure condition was breached: consider rejecting or reworking this strategy." if breaches else
                        f"{len(missing)} research step(s) still missing before this strategy deserves serious consideration." if missing else
                        "Every research step on the checklist has a recorded result. This is not a prediction of profit; live trading is outside this system."),
            "paper_days_recorded": paper_days}
