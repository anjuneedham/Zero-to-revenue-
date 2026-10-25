"""Read-only status snapshot for the dashboard (spec sections 27, 29)."""

from core.db import money
from core.orchestrator.killswitch import is_paused


def status_snapshot(conn) -> dict:
    one = lambda sql, *a: conn.execute(sql, a).fetchone()[0]
    # Only a fully verified receipt counts as revenue (spec section 16/18).
    revenue = one("SELECT COALESCE(SUM(usd_value),0) FROM ledger_entries WHERE type='receipt' AND status='VERIFIED'")
    return {
        "mode": "MOCK",
        "paused": is_paused(conn),
        "verified_revenue_usd": money(revenue),
        "agents": [dict(r) for r in conn.execute("SELECT name,status,last_run_at,mode FROM agents ORDER BY name")],
        "tasks": {r["status"]: r["n"] for r in conn.execute("SELECT status, COUNT(*) n FROM tasks GROUP BY status")},
        "opportunities": {r["status"]: r["n"] for r in conn.execute("SELECT status, COUNT(*) n FROM opportunities GROUP BY status")},
        "open_user_actions": [dict(r) for r in conn.execute(
            "SELECT action_id,title,why_required,exact_action,deadline,risk,verified_url FROM user_actions "
            "WHERE status='OPEN' ORDER BY created_at")],
        "payments_pending": one("SELECT COUNT(*) FROM payments WHERE status IN ('AWAITING_PAYMENT','PAYMENT_UNVERIFIED')"),
    }
