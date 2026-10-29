"""Read-only status snapshot and reports (spec sections 27, 29)."""

import os
from datetime import datetime, timedelta, timezone

from core.db import money
from core.orchestrator.killswitch import is_paused


def _one(conn, sql, *a):
    return conn.execute(sql, a).fetchone()[0]


def status_snapshot(conn) -> dict:
    # Only a fully verified receipt with a USD valuation counts toward USD revenue (spec 16/18).
    revenue = _one(conn, "SELECT COALESCE(SUM(usd_value),0) FROM ledger_entries WHERE type='receipt' AND status='VERIFIED'")
    unvalued = _one(conn, "SELECT count(*) FROM ledger_entries WHERE type='receipt' AND status='VERIFIED' AND usd_value IS NULL")
    return {
        "mode": "LIVE" if os.environ.get("VERCEL") else "LOCAL",
        "paused": is_paused(conn),
        "verified_revenue_usd": money(revenue),
        "verified_receipts_without_usd_value": unvalued,
        "agents": [dict(r) for r in conn.execute("SELECT name,status,last_run_at,mode FROM agents ORDER BY name")],
        "tasks": {r["status"]: r["n"] for r in conn.execute("SELECT status, COUNT(*) n FROM tasks GROUP BY status")},
        "opportunities": {r["status"]: r["n"] for r in conn.execute("SELECT status, COUNT(*) n FROM opportunities GROUP BY status")},
        "open_user_actions": [dict(r) for r in conn.execute(
            "SELECT action_id,title,why_required,exact_action,deadline,risk,verified_url,status,kind FROM user_actions "
            "WHERE status IN ('OPEN','APPROVED') ORDER BY created_at")],
        "payments_pending": _one(conn, "SELECT COUNT(*) FROM payments WHERE status IN ('AWAITING_PAYMENT','PAYMENT_UNVERIFIED')"),
        "health": {
            "scout_opportunities_today": _one(conn, "SELECT count(*) FROM opportunities WHERE discovered_at >= ?", _today()),
            "operator_waiting_for_you": _one(conn, "SELECT count(*) FROM tasks WHERE status='WAITING_FOR_USER'"),
            "operator_completed": _one(conn, "SELECT count(*) FROM tasks WHERE status='COMPLETED'"),
            "operator_failed": _one(conn, "SELECT count(*) FROM tasks WHERE status='FAILED'"),
            "treasury_last_check": _one(conn, "SELECT max(at) FROM wallet_balances"),
            "treasury_last_verified_payment": _one(conn, "SELECT max(verified_at) FROM payments WHERE status='PAYMENT_VERIFIED'"),
        },
    }


def _today() -> str:
    n = datetime.now(timezone.utc)
    return datetime(n.year, n.month, n.day, tzinfo=timezone.utc).isoformat()


def daily_report(conn) -> str:
    t = _today()
    y = (datetime.now(timezone.utc) - timedelta(days=1))
    y = datetime(y.year, y.month, y.day, tzinfo=timezone.utc).isoformat()
    rev_today = money(_one(conn, "SELECT COALESCE(SUM(usd_value),0) FROM ledger_entries WHERE type='receipt' AND status='VERIFIED' AND date >= ?", t))
    rev_total = money(_one(conn, "SELECT COALESCE(SUM(usd_value),0) FROM ledger_entries WHERE type='receipt' AND status='VERIFIED'"))
    exp = money(_one(conn, "SELECT COALESCE(SUM(usd_value),0) FROM ledger_entries WHERE type='expense' AND status='VERIFIED' AND date >= ?", t))
    top = conn.execute("SELECT title, expected_payment, payment_asset, source_url FROM opportunities WHERE status='QUALIFIED' "
                       "ORDER BY opportunity_score DESC LIMIT 1").fetchone()
    qualified_new = _one(conn, "SELECT count(*) FROM opportunities WHERE status='QUALIFIED' AND discovered_at >= ?", t)
    paid_today = _one(conn, "SELECT count(*) FROM ledger_entries WHERE type='receipt' AND status='VERIFIED' AND date >= ?", t)
    moved = conn.execute(
        "SELECT title, 'now ' || status AS what FROM opportunities WHERE discovered_at < ? AND "
        "status IN ('APPROVED','AWAITING_PAYMENT','PAYMENT_VERIFIED') ORDER BY discovered_at DESC LIMIT 5", (t,)).fetchall()
    from core import challenge
    ch = challenge.summary(conn)
    lines = [f"CHALLENGE: ${ch['cash_usd']:,.0f} of ${ch['target_usd']:,.0f} verified cash"
             + (f", day {ch['day']}/{ch['total_days']}, {'ahead of' if ch['ahead_by_usd'] >= 0 else 'behind'} pace by ${abs(ch['ahead_by_usd']):,.0f}" if ch["state"] == "running" else f" ({ch['state']})")
             + f". Open deals: {ch['deals_open']} (${ch['pipeline_usd']:,.0f}). Leads to contact today: {len(ch['due'])}.", "",
             "PIN MOVERS (what actually changed)"]
    if paid_today:
        lines.append(f"- {paid_today} payment(s) verified today")
    if qualified_new:
        lines.append(f"- {qualified_new} new opportunity(ies) qualified today")
    for m in moved:
        lines.append(f"- {m['title'][:80]}: {m['what']}")
    if lines[-1].startswith("PIN MOVERS"):
        lines.append("- Nothing moved today")
    lines.append("")
    lines += [
        f"Verified revenue today: ${rev_today:.2f}",
        f"Verified expenses today: ${exp:.2f}",
        f"Net today: ${rev_today - exp:.2f}",
        f"Total verified revenue: ${rev_total:.2f}",
        f"Opportunities discovered today: {_one(conn, 'SELECT count(*) FROM opportunities WHERE discovered_at >= ?', t)}",
        f"Opportunities qualified (open): {_one(conn, 'SELECT count(*) FROM opportunities WHERE status=?', 'QUALIFIED')}",
        f"Tasks completed: {_one(conn, 'SELECT count(*) FROM tasks WHERE status=?', 'COMPLETED')}",
        f"Tasks submitted / awaiting payment: {_one(conn, 'SELECT count(*) FROM tasks WHERE status=?', 'AWAITING_PAYMENT')}",
        f"Payments pending: {_one(conn, 'SELECT count(*) FROM payments WHERE status IN (?,?)', 'AWAITING_PAYMENT', 'PAYMENT_UNVERIFIED')}",
        f"User actions required: {_one(conn, 'SELECT count(*) FROM user_actions WHERE status IN (?,?)', 'OPEN', 'APPROVED')}",
        f"Agent failures today: {_one(conn, 'SELECT count(*) FROM agent_runs WHERE outcome=? AND started_at >= ?', 'error', t)}",
        f"Top opportunity: {(top['title'][:80] + ' - $' + str(top['expected_payment']) + ' ' + (top['payment_asset'] or '') + ' claimed, ' + (top['source_url'] or '')) if top else 'none yet'}",
        "Next priority: " + ("review the open actions" if _one(conn, "SELECT count(*) FROM user_actions WHERE status='OPEN'") else "let Scout find work"),
    ]
    return "\n".join(lines)
