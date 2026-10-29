"""Read-only status snapshot and reports."""

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
        "payments_pending": _one(conn, "SELECT COUNT(*) FROM payments WHERE status IN ('AWAITING_PAYMENT','PAYMENT_UNVERIFIED')"),
        "last_verified_payment": _one(conn, "SELECT max(verified_at) FROM payments WHERE status='PAYMENT_VERIFIED'"),
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
    paid_today = _one(conn, "SELECT count(*) FROM ledger_entries WHERE type='receipt' AND status='VERIFIED' AND date >= ?", t)
    from core import challenge
    ch = challenge.summary(conn)
    lines = [f"CHALLENGE: ${ch['cash_usd']:,.0f} of ${ch['target_usd']:,.0f} verified cash"
             + (f", day {ch['day']}/{ch['total_days']}, {'ahead of' if ch['ahead_by_usd'] >= 0 else 'behind'} pace by ${abs(ch['ahead_by_usd']):,.0f}" if ch["state"] == "running" else f" ({ch['state']})")
             + f". Open deals: {ch['deals_open']} (${ch['pipeline_usd']:,.0f}). Leads to contact today: {len(ch['due'])}.", "",
             "WHAT CHANGED"]
    if paid_today:
        lines.append(f"- {paid_today} payment(s) verified today")
    if lines[-1] == "WHAT CHANGED":
        lines.append("- Nothing moved today")
    lines.append("")
    lines += [
        f"Verified revenue today: ${rev_today:.2f}",
        f"Verified expenses today: ${exp:.2f}",
        f"Net today: ${rev_today - exp:.2f}",
        f"Total verified revenue: ${rev_total:.2f}",
        f"Payments pending: {_one(conn, 'SELECT count(*) FROM payments WHERE status IN (?,?)', 'AWAITING_PAYMENT', 'PAYMENT_UNVERIFIED')}",
    ]
    return "\n".join(lines)
