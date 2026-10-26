"""Operator (spec sections 9-12). Turns qualified opportunities into DRAFT deliverables inside the
database, then blocks on the owner. It never submits, signs, pays or contacts anyone."""

import json
import uuid
from urllib.parse import urlsplit

from agents.operator import drafts
from core.db import now
from core.events.events import emit
from core.notifications.service import alert
from core.orchestrator.killswitch import is_paused
from core.policy.policy import Action, Agent, authorize
from core.queue import queue


def _safe_url(url: str) -> str | None:
    return url if url and urlsplit(url).scheme == "https" else None


def step(conn) -> dict:
    """Process at most one task. Returns what happened."""
    d = authorize(Agent.OPERATOR, Action.CREATE_DELIVERABLE, paused=is_paused(conn))
    if not d.allowed:
        return {"ran": False, "reason": d.reason}
    task = queue.claim(conn, "operator")
    if task is None:
        return {"ran": True, "task": None}
    conn.execute("UPDATE agents SET status='online', last_run_at=? WHERE name='operator'", (now(),))
    try:
        if task["kind"] != "research_opportunity":
            queue.fail(conn, task["id"], f"unknown task kind {task['kind']}", transient=False)
            return {"ran": True, "task": task["id"], "result": "failed"}
        opp = conn.execute("SELECT * FROM opportunities WHERE id=?", (task["opportunity_id"],)).fetchone()
        if opp is None or opp["status"] != "QUALIFIED":
            queue.set_status(conn, task["id"], "CANCELLED", detail="opportunity missing or no longer qualified")
            return {"ran": True, "task": task["id"], "result": "cancelled"}
        opp = dict(opp)
        content = drafts.draft(opp)
        plan = drafts.plan(opp)
        conn.execute("INSERT INTO deliverables(id, task_id, path, summary, created_at, content) VALUES (?,?,?,?,?,?) "
                     "ON CONFLICT DO NOTHING",
                     ("dlv_" + task["id"], task["id"], None, "Draft submission + plan", now(), content))
        sub_id = "sub_" + opp["id"]
        conn.execute("INSERT INTO submissions(id, task_id, idempotency_key, status) VALUES (?,?,?, 'DRAFT') "
                     "ON CONFLICT DO NOTHING", (sub_id, task["id"], f"submit:{opp['id']}"))
        action_id = "ua_" + task["id"]
        steps = "\n".join(f"{i}. {s}" for i, s in enumerate(plan, 1))
        conn.execute(
            "INSERT INTO user_actions(action_id, task_id, title, why_required, exact_action, deadline, estimated_value, "
            "risk, verified_url, status, created_at, kind, submission_id) VALUES (?,?,?,?,?,?,?,?,?, 'OPEN', ?, 'review_submission', ?) "
            "ON CONFLICT DO NOTHING",
            (action_id, task["id"], f"Review and submit: {opp['title']}"[:200],
             "Submitting needs your own account and your approval. The system never submits for you.",
             steps, opp.get("deadline"), opp.get("expected_payment"),
             "HIGH" if (opp.get("risk_score") or 0) > 35 else "LOW", _safe_url(opp["source_url"]), now(), sub_id))
        queue.set_status(conn, task["id"], "WAITING_FOR_USER", detail="draft ready", blocked_reason="owner review and submission")
        conn.execute("UPDATE tasks SET outputs=?, next_action=? WHERE id=?",
                     (json.dumps({"deliverable": "dlv_" + task["id"], "submission": sub_id}), "owner: review and submit", task["id"]))
        conn.execute("UPDATE opportunities SET status='IN_PROGRESS' WHERE id=?", (opp["id"],))
        emit(conn, "task.completed", "operator", {"task_id": task["id"], "submission_required": True})
        alert(conn, "HIGH", f"action:{action_id}", "Action required",
              f"Draft ready to review: {opp['title'][:120]}. Claimed pay (unverified): {(f"{float(opp['expected_payment']):g} {opp.get('payment_asset') or ''}".strip()) if opp.get('expected_payment') else 'n/a'}.")
        return {"ran": True, "task": task["id"], "result": "waiting_for_user", "action_id": action_id}
    except Exception as e:  # recorded and retried; never swallowed
        queue.fail(conn, task["id"], f"{type(e).__name__}: {str(e)[:200]}", transient=True)
        conn.execute("UPDATE agents SET status='error' WHERE name='operator'")
        return {"ran": True, "task": task["id"], "result": "error", "error": str(e)[:200]}


def run(conn, max_tasks: int = 40) -> list[dict]:
    out = []
    for _ in range(max_tasks):
        r = step(conn)
        out.append(r)
        if not r.get("ran") or r.get("task") is None:
            break
    return out
