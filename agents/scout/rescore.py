"""Re-apply the current scoring rules to opportunities already in the database.
Only ever DOWNGRADES (QUALIFIED/IN_PROGRESS -> REVIEW_REQUIRED) and cancels the unstarted work
that depended on them. Never promotes, and never touches anything the owner already approved.
Runs once per RULES_VERSION (recorded in settings), so it is idempotent."""

from agents.scout.evaluate import RawItem, evaluate
from core.audit import audit
from core.db import now
from core.queue import queue

RULES_VERSION = "4"
KEY = "scout_rules_version"


def _item(r) -> RawItem:
    f = lambda v: float(v) if v is not None else None
    return RawItem(title=r["title"], source=r["source"] or "", source_url=r["source_url"], organization=r["organization"] or "",
                   category=r["category"] or "bounty", deadline=r["deadline"],
                   required_skills=[x for x in (r["required_skills"] or "").split(",") if x],
                   required_capital=f(r["required_capital"]), expected_payment=f(r["expected_payment"]),
                   payment_asset=r["payment_asset"] or "", payment_method=r["payment_method"] or "")


def rescore(conn) -> dict:
    cur = conn.execute("SELECT value FROM settings WHERE key=?", (KEY,)).fetchone()
    if cur and cur["value"] == RULES_VERSION:
        return {"skipped": True, "downgraded": 0}
    downgraded = cancelled = 0
    for r in conn.execute("SELECT * FROM opportunities WHERE status IN ('QUALIFIED','IN_PROGRESS','REVIEW_REQUIRED','DISCOVERED')").fetchall():
        ev = evaluate(_item(r))
        conn.execute("UPDATE opportunities SET opportunity_score=?, risk_score=?, confidence=?, scam_indicators=?, "
                     "missing_information=?, recommended_action=? WHERE id=?",
                     (ev.score, ev.risk, ev.row["confidence"], ev.row["scam_indicators"], ev.row["missing_information"],
                      ev.row["recommended_action"], r["id"]))
        if r["status"] in ("QUALIFIED", "IN_PROGRESS") and ev.row["status"] == "REVIEW_REQUIRED":
            downgraded += 1
            conn.execute("UPDATE opportunities SET status='REVIEW_REQUIRED' WHERE id=?", (r["id"],))
            for t in conn.execute("SELECT id, status FROM tasks WHERE opportunity_id=?", (r["id"],)).fetchall():
                if t["status"] not in ("COMPLETED", "FAILED", "CANCELLED"):
                    queue.set_status(conn, t["id"], "CANCELLED", detail="rescored: no longer qualified")
                    cancelled += 1
                conn.execute("UPDATE user_actions SET status='REJECTED', resolved_at=? WHERE task_id=? AND status='OPEN'", (now(), t["id"]))
                conn.execute("UPDATE submissions SET status='CANCELLED' WHERE task_id=? AND status='DRAFT'", (t["id"],))
    conn.execute("INSERT INTO settings(key, value, updated_at) VALUES (?,?,?) ON CONFLICT (key) DO UPDATE "
                 "SET value=EXCLUDED.value, updated_at=EXCLUDED.updated_at", (KEY, RULES_VERSION, now()))
    audit(conn, "scout", "scout.rescore", RULES_VERSION, f"downgraded={downgraded} cancelled_tasks={cancelled}")
    return {"skipped": False, "downgraded": downgraded, "cancelled_tasks": cancelled}
