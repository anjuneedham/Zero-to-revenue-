"""One scheduler tick (spec sections 24, 30, 38). Called by Vercel Cron via /api/cron.
Respects the kill switch, records every failure, alerts the owner on agent failures."""

import os
from datetime import datetime, timedelta, timezone

from agents.operator import run as operator
from agents.scout.run import run_scout
from agents.treasury.run import check_balances
from core.db import now
from core.notifications.service import alert
from core.orchestrator.killswitch import is_paused
from core.reports import daily_report


def _hours(name, default):
    try:
        return max(1, int(os.environ.get(name, default)))
    except ValueError:
        return default


def _scout_due(conn, at: datetime) -> bool:
    last = conn.execute("SELECT max(started_at) m FROM agent_runs WHERE agent='scout'").fetchone()["m"]
    return last is None or datetime.fromisoformat(last) <= at - timedelta(hours=_hours("SCOUT_EVERY_HOURS", 6))


def _guard(conn, name, fn, out):
    try:
        out[name] = fn()
    except Exception as e:
        out[name] = {"error": f"{type(e).__name__}: {str(e)[:150]}"}
        conn.execute("UPDATE agents SET status='error' WHERE name=?", (name,))
        alert(conn, "MEDIUM", f"fail:{name}:{now()[:13]}", f"{name.title()} agent failed", out[name]["error"])


def tick(conn, scout_sources=None, rpc=None) -> dict:
    if is_paused(conn):
        return {"ran": False, "reason": "paused"}
    at = datetime.now(timezone.utc)
    out = {"ran": True, "at": at.isoformat()}
    if _scout_due(conn, at):
        _guard(conn, "scout", lambda: run_scout(conn, scout_sources), out)
    _guard(conn, "operator", lambda: operator.run(conn), out)
    _guard(conn, "treasury", lambda: check_balances(conn, rpc), out)
    soon = (at + timedelta(hours=24)).isoformat()
    for o in conn.execute("SELECT id, title, deadline FROM opportunities WHERE deadline IS NOT NULL AND deadline > ? "
                          "AND deadline < ? AND status IN ('QUALIFIED','APPROVED','IN_PROGRESS')", (at.isoformat(), soon)):
        alert(conn, "HIGH", f"deadline:{o['id']}", "Deadline under 24 hours", f"{o['title'][:120]} is due {o['deadline']}.")
    today = at.date().isoformat()
    last = conn.execute("SELECT value FROM settings WHERE key='last_daily_summary'").fetchone()
    if last is None or last["value"] != today:
        alert(conn, "MEDIUM", f"daily:{today}", "Founder OS daily report", daily_report(conn))
        conn.execute("INSERT INTO settings(key, value, updated_at) VALUES ('last_daily_summary', ?, ?) "
                     "ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=EXCLUDED.updated_at", (today, now()))
        out["daily_report"] = True
    return out
