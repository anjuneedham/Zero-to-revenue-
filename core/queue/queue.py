"""Durable DB-backed task queue with leases and idempotency (spec sections 22, 23, 37)."""

import uuid
from datetime import datetime, timedelta, timezone

from core.audit import audit
from core.db import now
from core.orchestrator.killswitch import is_paused

TERMINAL = {"COMPLETED", "FAILED", "CANCELLED"}


def _event(conn, task_id, event, detail=None):
    conn.execute("INSERT INTO task_events(task_id,event,detail,created_at) VALUES (?,?,?,?)",
                 (task_id, event, detail, now()))


def enqueue(conn, owner_agent, kind, idempotency_key, *, inputs=None, priority=5,
            risk="LOW", opportunity_id=None, max_attempts=3) -> str:
    """Returns the task id; a repeated idempotency key returns the existing task
    (also under concurrent callers: the unique key arbitrates)."""
    tid = "task_" + uuid.uuid4().hex[:12]
    t = now()
    cur = conn.execute(
        "INSERT INTO tasks(id,opportunity_id,owner_agent,kind,status,priority,risk,created_at,updated_at,"
        "max_attempts,idempotency_key,inputs) VALUES (?,?,?,?, 'QUEUED',?,?,?,?,?,?,?) "
        "ON CONFLICT (idempotency_key) DO NOTHING",
        (tid, opportunity_id, owner_agent, kind, priority, risk, t, t, max_attempts, idempotency_key, inputs))
    if cur.rowcount == 0:
        return conn.execute("SELECT id FROM tasks WHERE idempotency_key=?", (idempotency_key,)).fetchone()["id"]
    _event(conn, tid, "enqueued")
    return tid


def claim(conn, agent, lease_seconds=300):
    """Atomically claim the next task for `agent`. Returns None when paused or empty.
    FOR UPDATE SKIP LOCKED lets concurrent workers each take a different task.
    Expired leases are reclaimed; attempts are counted on every claim."""
    if is_paused(conn):
        return None
    t = now()
    until = (datetime.now(timezone.utc) + timedelta(seconds=lease_seconds)).isoformat()
    with conn.transaction():
        row = conn.execute(
            "SELECT id, attempts FROM tasks WHERE owner_agent=? AND attempts < max_attempts AND "
            "(status='QUEUED' OR (status='IN_PROGRESS' AND lease_until < ?)) "
            "ORDER BY priority, created_at LIMIT 1 FOR UPDATE SKIP LOCKED", (agent, t)).fetchone()
        if row is None:
            return None
        conn.execute("UPDATE tasks SET status='IN_PROGRESS', attempts=attempts+1, lease_until=?, updated_at=? WHERE id=?",
                     (until, t, row["id"]))
        _event(conn, row["id"], "claimed", f"attempt {row['attempts'] + 1}")
    return conn.execute("SELECT * FROM tasks WHERE id=?", (row["id"],)).fetchone()


def set_status(conn, task_id, status, *, detail=None, blocked_reason=None):
    cur = conn.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
    if cur is None:
        raise KeyError(task_id)
    if cur["status"] in TERMINAL:
        raise ValueError(f"task {task_id} is {cur['status']} and cannot change")
    conn.execute("UPDATE tasks SET status=?, blocked_reason=?, lease_until=NULL, updated_at=? WHERE id=?",
                 (status, blocked_reason, now(), task_id))
    _event(conn, task_id, f"status.{status}", detail)


def fail(conn, task_id, error, *, transient: bool):
    """Transient -> retry (until max_attempts); permanent -> FAILED (spec 38)."""
    row = conn.execute("SELECT attempts,max_attempts FROM tasks WHERE id=?", (task_id,)).fetchone()
    if transient and row["attempts"] < row["max_attempts"]:
        set_status(conn, task_id, "QUEUED", detail=f"retry after: {error}")
    else:
        set_status(conn, task_id, "FAILED", detail=error)
        audit(conn, "queue", "task.failed", task_id, error)
