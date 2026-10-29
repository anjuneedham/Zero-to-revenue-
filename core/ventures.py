"""Venture workspace: each venture's tasks, decisions and experiments (migration 008; tables are venture_tasks, venture_decisions, venture_experiments). Owner-only, no side effects
outside the database: nothing here sends, spends or contacts anyone."""

import uuid
from datetime import date

from core.audit import audit
from core.db import now

TASK_STATUS = ("todo", "doing", "blocked", "done")
PRIORITY = ("high", "normal", "low")
DECISION_STATUS = ("decided", "reversed")
EXPERIMENT_CLOSE = ("won", "lost", "inconclusive", "stopped")


class VentureError(ValueError):
    pass


def _text(v, field, n, required=False):
    v = (v or "").strip() if isinstance(v, str) or v is None else str(v).strip()
    if required and not v:
        raise VentureError(f"{field} is required")
    return v[:n]


def _venture(conn, vid, required=True):
    if not vid and not required:
        return None
    if conn.execute("SELECT 1 FROM ventures WHERE id=?", (vid,)).fetchone() is None:
        raise VentureError("unknown venture")
    return vid


def overview(conn) -> dict:
    ventures = [dict(r) for r in conn.execute("SELECT id,name,kind,status,plan_day,notes FROM ventures ORDER BY position, id")]
    by = {v["id"]: dict(v, tasks=[], experiments=[], decisions=[]) for v in ventures}
    for r in conn.execute("SELECT id,venture_id,title,status,priority,due_date,notes FROM venture_tasks WHERE status<>'done' "
                          "ORDER BY (priority='high') DESC, due_date NULLS LAST, created_at"):
        by[r["venture_id"]]["tasks"].append(dict(r))
    for r in conn.execute("SELECT id,venture_id,hypothesis,metric,created_at FROM venture_experiments WHERE status='running' ORDER BY created_at"):
        by[r["venture_id"]]["experiments"].append(dict(r))
    shared = []
    for r in conn.execute("SELECT id,venture_id,title,context,created_at FROM venture_decisions WHERE status='open' ORDER BY created_at"):
        (by[r["venture_id"]]["decisions"] if r["venture_id"] in by else shared).append(dict(r))
    recent = [dict(r) for r in conn.execute(
        "SELECT id,venture_id,title,decision,status,decided_at FROM venture_decisions WHERE status<>'open' ORDER BY decided_at DESC NULLS LAST LIMIT 10")]
    return {"ventures": list(by.values()), "shared_decisions": shared, "recent_decisions": recent,
            "weekday": date.today().strftime("%a")}


def add_task(conn, owner, venture_id, title, priority="normal", due_date="", notes=""):
    _venture(conn, venture_id)
    if priority not in PRIORITY:
        raise VentureError("priority must be high, normal or low")
    due = _text(due_date, "due date", 10)
    if due:
        try:
            date.fromisoformat(due)
        except ValueError:
            raise VentureError("due date must look like 2026-11-05") from None
    tid = "vt_" + uuid.uuid4().hex[:12]
    conn.execute("INSERT INTO venture_tasks(id,venture_id,title,priority,due_date,notes,created_at) VALUES (?,?,?,?,?,?,?)",
                 (tid, venture_id, _text(title, "title", 200, True), priority, due or None, _text(notes, "notes", 1000) or None, now()))
    audit(conn, owner, "venture.task_add", tid, venture_id)
    return {"id": tid}


def set_task_status(conn, owner, task_id, status):
    if status not in TASK_STATUS:
        raise VentureError("unknown task status")
    if not conn.execute("UPDATE venture_tasks SET status=?, done_at=? WHERE id=?",
                        (status, now() if status == "done" else None, task_id)).rowcount:
        raise VentureError("task not found")
    audit(conn, owner, "venture.task_status", task_id, status)
    return {"ok": True}


def add_decision(conn, owner, venture_id, title, context=""):
    _venture(conn, venture_id, required=False)
    did = "dec_" + uuid.uuid4().hex[:12]
    conn.execute("INSERT INTO venture_decisions(id,venture_id,title,context,created_at) VALUES (?,?,?,?,?)",
                 (did, venture_id or None, _text(title, "title", 200, True), _text(context, "context", 1000) or None, now()))
    audit(conn, owner, "venture.decision_add", did, venture_id or "os")
    return {"id": did}


def decide(conn, owner, decision_id, decision, status="decided"):
    if status not in DECISION_STATUS:
        raise VentureError("status must be decided or reversed")
    text = _text(decision, "decision", 1000, True)
    if not conn.execute("UPDATE venture_decisions SET decision=?, status=?, decided_at=? WHERE id=?", (text, status, now(), decision_id)).rowcount:
        raise VentureError("decision not found")
    audit(conn, owner, "venture.decision", decision_id, status)
    return {"ok": True}


def add_experiment(conn, owner, venture_id, hypothesis, metric):
    _venture(conn, venture_id)
    eid = "exp_" + uuid.uuid4().hex[:12]
    conn.execute("INSERT INTO venture_experiments(id,venture_id,hypothesis,metric,created_at) VALUES (?,?,?,?,?)",
                 (eid, venture_id, _text(hypothesis, "hypothesis", 300, True), _text(metric, "metric", 200, True), now()))
    audit(conn, owner, "venture.experiment_add", eid, venture_id)
    return {"id": eid}


def close_experiment(conn, owner, experiment_id, status, result=""):
    if status not in EXPERIMENT_CLOSE:
        raise VentureError("status must be won, lost, inconclusive or stopped")
    if not conn.execute("UPDATE venture_experiments SET status=?, result=?, closed_at=? WHERE id=? AND status='running'",
                        (status, _text(result, "result", 1000) or None, now(), experiment_id)).rowcount:
        raise VentureError("running experiment not found")
    audit(conn, owner, "venture.experiment_close", experiment_id, status)
    return {"ok": True}
