"""One scheduler tick (spec sections 24, 30, 38). Called by Vercel Cron via /api/cron.
Respects the kill switch, records every failure, alerts the owner when a job fails."""

from datetime import datetime, timezone

from core.db import now
from core.notifications.service import alert
from core.orchestrator.killswitch import is_paused
from core import weekly
from core.reports import daily_report


def _guard(conn, name, fn, out):
    try:
        out[name] = fn()
    except Exception as e:
        out[name] = {"error": f"{type(e).__name__}: {str(e)[:150]}"}
        alert(conn, "MEDIUM", f"fail:{name}:{now()[:13]}", f"Scheduled job failed: {name}", out[name]["error"])


def tick(conn) -> dict:
    if is_paused(conn):
        return {"ran": False, "reason": "paused"}
    at = datetime.now(timezone.utc)
    out = {"ran": True, "at": at.isoformat()}
    today = at.date().isoformat()
    last = conn.execute("SELECT value FROM settings WHERE key='last_daily_summary'").fetchone()
    if last is None or last["value"] != today:
        alert(conn, "MEDIUM", f"daily:{today}", "Founder OS daily report", daily_report(conn))
        conn.execute("INSERT INTO settings(key, value, updated_at) VALUES ('last_daily_summary', ?, ?) "
                     "ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=EXCLUDED.updated_at", (today, now()))
        out["daily_report"] = True
    # Sunday: the weekly learning report, once per ISO week (the daily cron may fire more than once or be retried).
    week = weekly.iso_week(at.date())
    wk = conn.execute("SELECT value FROM settings WHERE key='last_weekly_report'").fetchone()
    if at.weekday() == 6 and (wk is None or wk["value"] != week):
        _guard(conn, "weekly_report", lambda: alert(conn, "MEDIUM", f"weekly:{week}", "Weekly report: replies, onboardings, paid",
                                                    weekly.render_text(weekly.report(conn))) or True, out)
        if out.get("weekly_report") is True:
            conn.execute("INSERT INTO settings(key, value, updated_at) VALUES ('last_weekly_report', ?, ?) "
                         "ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=EXCLUDED.updated_at", (week, now()))
    return out
