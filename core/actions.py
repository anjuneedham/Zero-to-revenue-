"""Owner decisions on USER_ACTIONs (spec sections 12, 13, 37). The owner submits work
themselves on the platform; the system only records the decision and proof."""

from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from core.audit import audit
from core.db import now
from core.events.events import emit
from core.queue import queue

APPROVAL_VALID_DAYS = 7


class ActionError(ValueError):
    pass


def _get(conn, action_id):
    a = conn.execute("SELECT * FROM user_actions WHERE action_id=?", (action_id,)).fetchone()
    if a is None:
        raise ActionError("action not found")
    return a


def _opp_for(conn, a):
    t = conn.execute("SELECT opportunity_id FROM tasks WHERE id=?", (a["task_id"],)).fetchone()
    return t["opportunity_id"] if t else None


def approve(conn, action_id, owner):
    a = _get(conn, action_id)
    if a["status"] != "OPEN":
        raise ActionError(f"action is {a['status']}")
    conn.execute("UPDATE user_actions SET status='APPROVED' WHERE action_id=? AND status='OPEN'", (action_id,))
    if a["submission_id"]:
        conn.execute("UPDATE submissions SET status='APPROVED', approved_by=?, approved_at=? WHERE id=?",
                     (owner, now(), a["submission_id"]))
    opp = _opp_for(conn, a)
    if opp:
        conn.execute("UPDATE opportunities SET status='APPROVED' WHERE id=?", (opp,))
    audit(conn, owner, "action.approve", action_id)


def reject(conn, action_id, owner):
    a = _get(conn, action_id)
    if a["status"] not in ("OPEN", "APPROVED"):
        raise ActionError(f"action is {a['status']}")
    conn.execute("UPDATE user_actions SET status='REJECTED', resolved_at=? WHERE action_id=?", (now(), action_id))
    if a["submission_id"]:
        conn.execute("UPDATE submissions SET status='CANCELLED' WHERE id=?", (a["submission_id"],))
    if a["task_id"]:
        try:
            queue.set_status(conn, a["task_id"], "CANCELLED", detail="owner rejected")
        except ValueError:
            pass
    opp = _opp_for(conn, a)
    if opp:
        conn.execute("UPDATE opportunities SET status='REJECTED' WHERE id=?", (opp,))
    audit(conn, owner, "action.reject", action_id)


def mark_submitted(conn, action_id, owner, proof_url=""):
    """Owner confirms they submitted. Requires a still-valid approval."""
    a = _get(conn, action_id)
    if a["status"] != "APPROVED":
        raise ActionError("approve the action before marking it submitted")
    sub = conn.execute("SELECT * FROM submissions WHERE id=?", (a["submission_id"],)).fetchone()
    if sub is None or not sub["approved_at"]:
        raise ActionError("no approved submission")
    approved = datetime.fromisoformat(sub["approved_at"])
    if datetime.now(timezone.utc) - approved > timedelta(days=APPROVAL_VALID_DAYS):
        raise ActionError("approval expired; review and approve again")
    if proof_url and urlsplit(proof_url).scheme != "https":
        raise ActionError("proof link must be an https URL")
    conn.execute("UPDATE submissions SET status='SUBMITTED', submitted_at=?, proof=? WHERE id=?",
                 (now(), proof_url[:500] or None, sub["id"]))
    conn.execute("UPDATE user_actions SET status='DONE', resolved_at=? WHERE action_id=?", (now(), action_id))
    queue.set_status(conn, a["task_id"], "AWAITING_PAYMENT", detail="owner submitted")
    opp_id = _opp_for(conn, a)
    if opp_id:
        opp = conn.execute("SELECT expected_payment, payment_asset FROM opportunities WHERE id=?", (opp_id,)).fetchone()
        conn.execute("UPDATE opportunities SET status='AWAITING_PAYMENT' WHERE id=?", (opp_id,))
        conn.execute("INSERT INTO payments(id, opportunity_id, expected_amount, asset, status, created_at) "
                     "VALUES (?,?,?,?, 'AWAITING_PAYMENT', ?) ON CONFLICT DO NOTHING",
                     ("pay_" + opp_id, opp_id, opp["expected_payment"], opp["payment_asset"], now()))
        emit(conn, "payment.pending", "operator", {"opportunity_id": opp_id})
    audit(conn, owner, "action.submitted", action_id, proof_url[:200] or None)
