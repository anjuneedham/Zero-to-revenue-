"""Multi-venture workspace: ventures, tasks, decisions, experiments, metrics, effort. Owner-only (the
API layer enforces login); every write is audited. Nothing here can count as revenue: only Treasury's
PAYMENT_VERIFIED does. Free text is stored as data and rendered with textContent."""

import re
import uuid
from datetime import date

from core.audit import audit
from core.db import now

STAGES = ("DECIDE", "RESEARCH", "BUILD", "VALIDATE", "SELL", "SCALE", "KILLED")
TASK_STATUS = ("OPEN", "DOING", "DONE", "BLOCKED", "DROPPED")
TASK_OWNERS = ("founder", "agent", "both")
EXP_STATUS = ("PLANNED", "RUNNING", "SUCCEEDED", "FAILED", "ABANDONED")
VID = re.compile(r"^[a-z0-9_-]{1,40}$")
ID = re.compile(r"^[a-z]{1,4}_[a-f0-9]{12}$")
METRIC = re.compile(r"^[a-z][a-z0-9_]{0,59}$")
MAX_TEXT = 1000


class VentureError(ValueError):
    pass


def _text(v, field, required=True, limit=MAX_TEXT):
    if v is None or v == "":
        if required:
            raise VentureError(f"{field} is required")
        return None
    if not isinstance(v, str):
        raise VentureError(f"{field} must be text")
    v = v.strip()
    if required and not v:
        raise VentureError(f"{field} is required")
    if len(v) > limit:
        raise VentureError(f"{field} is too long")
    return v or None


def _venture(conn, vid):
    if not isinstance(vid, str) or not VID.match(vid):
        raise VentureError("bad venture id")
    row = conn.execute("SELECT * FROM ventures WHERE id=?", (vid,)).fetchone()
    if not row:
        raise VentureError("unknown venture")
    return dict(row)


def _new_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _rows(cur):
    return [dict(r) for r in cur]


def overview(conn) -> dict:
    ventures = _rows(conn.execute("SELECT * FROM ventures ORDER BY (stage='KILLED'), priority, name"))
    for v in ventures:
        t = {r["status"]: r["n"] for r in conn.execute("SELECT status, count(*) n FROM venture_tasks WHERE venture_id=? GROUP BY status", (v["id"],))}
        v["tasks"] = t
        v["open_decisions"] = conn.execute("SELECT count(*) n FROM decisions WHERE venture_id=? AND status='OPEN'", (v["id"],)).fetchone()["n"]
        v["running_experiments"] = conn.execute("SELECT count(*) n FROM experiments WHERE venture_id=? AND status='RUNNING'", (v["id"],)).fetchone()["n"]
        v["metrics"] = _rows(conn.execute(
            "SELECT DISTINCT ON (name) name, value, at, source FROM metrics WHERE venture_id=? ORDER BY name, at DESC, id DESC", (v["id"],)))
    today = date.today().isoweekday()
    alloc = _rows(conn.execute("SELECT a.venture_id, a.weekday, a.focus, v.name FROM venture_allocation a JOIN ventures v ON v.id=a.venture_id ORDER BY a.weekday, v.priority"))
    week = _rows(conn.execute("SELECT venture_id, round(sum(hours)::numeric,1)::float hours, sum(claude_sessions)::int claude_sessions "
                              "FROM effort_logs WHERE day >= ? GROUP BY venture_id", (date.fromordinal(date.today().toordinal() - today + 1).isoformat(),)))
    return {"ventures": ventures, "allocation": alloc, "today_weekday": today, "effort_this_week": week,
            "open_decisions": _rows(conn.execute("SELECT id, venture_id, question, created_at FROM decisions WHERE status='OPEN' ORDER BY created_at")),
            "note": "Effort and Claude usage are self-reported, not enforced. Metrics never count as revenue; only Treasury-verified payments do."}


def venture_detail(conn, vid) -> dict:
    v = _venture(conn, vid)
    return {"venture": v,
            "tasks": _rows(conn.execute("SELECT * FROM venture_tasks WHERE venture_id=? ORDER BY (status IN ('DONE','DROPPED')), due_at NULLS LAST, created_at", (vid,))),
            "decisions": _rows(conn.execute("SELECT * FROM decisions WHERE venture_id=? ORDER BY created_at DESC LIMIT 50", (vid,))),
            "experiments": _rows(conn.execute("SELECT * FROM experiments WHERE venture_id=? ORDER BY created_at DESC LIMIT 50", (vid,))),
            "metrics": _rows(conn.execute("SELECT name, value, at, source FROM metrics WHERE venture_id=? ORDER BY at DESC, id DESC LIMIT 100", (vid,))),
            "effort": _rows(conn.execute("SELECT day, hours, claude_sessions, note FROM effort_logs WHERE venture_id=? ORDER BY day DESC, id DESC LIMIT 30", (vid,)))}


def set_stage(conn, owner, vid, stage, reason=None) -> dict:
    v = _venture(conn, vid)
    if stage not in STAGES:
        raise VentureError("bad stage")
    reason = _text(reason, "reason", required=(stage == "KILLED"))
    conn.execute("UPDATE ventures SET stage=? WHERE id=?", (stage, vid))
    audit(conn, owner, "venture.stage", vid, f"{v['stage']} -> {stage}" + (f": {reason}" if reason else ""))
    if stage == "KILLED":  # killing a venture is itself a recorded decision, never silent
        conn.execute("INSERT INTO decisions(id, venture_id, question, decision, rationale, status, decided_at, created_at) "
                     "VALUES (?,?,?,?,?,'DECIDED',?,?)", (_new_id("dec"), vid, f"Kill {v['name']}?", "Killed", reason, now(), now()))
    return {"id": vid, "stage": stage}


def add_task(conn, owner, vid, title, who="founder", due_at=None, note=None) -> dict:
    _venture(conn, vid)
    title = _text(title, "title", limit=200)
    if who not in TASK_OWNERS:
        raise VentureError("bad owner")
    due = _text(due_at, "due_at", required=False, limit=10)
    if due:
        try:
            date.fromisoformat(due)
        except ValueError:
            raise VentureError("due_at must be YYYY-MM-DD")
    tid = _new_id("vt")
    conn.execute("INSERT INTO venture_tasks(id, venture_id, title, owner, status, due_at, note, created_at, updated_at) VALUES (?,?,?,?, 'OPEN', ?,?,?,?)",
                 (tid, vid, title, who, due, _text(note, "note", required=False), now(), now()))
    audit(conn, owner, "venture.task_add", tid, f"{vid}: {title[:80]}")
    return {"id": tid}


def update_task(conn, owner, tid, status=None, note=None) -> dict:
    if not isinstance(tid, str) or not ID.match(tid):
        raise VentureError("bad task id")
    row = conn.execute("SELECT * FROM venture_tasks WHERE id=?", (tid,)).fetchone()
    if not row:
        raise VentureError("unknown task")
    if status is not None and status not in TASK_STATUS:
        raise VentureError("bad status")
    note = _text(note, "note", required=False)
    if status == "BLOCKED" and not (note or row["note"]):
        raise VentureError("say what it is blocked on")
    conn.execute("UPDATE venture_tasks SET status=COALESCE(?, status), note=COALESCE(?, note), updated_at=? WHERE id=?", (status, note, now(), tid))
    audit(conn, owner, "venture.task_update", tid, f"{row['status']} -> {status or row['status']}")
    return {"id": tid, "status": status or row["status"]}


def add_decision(conn, owner, question, vid=None, decision=None, rationale=None) -> dict:
    if vid:
        _venture(conn, vid)
    question = _text(question, "question", limit=300)
    decision = _text(decision, "decision", required=False)
    did = _new_id("dec")
    conn.execute("INSERT INTO decisions(id, venture_id, question, decision, rationale, status, decided_at, created_at) VALUES (?,?,?,?,?,?,?,?)",
                 (did, vid or None, question, decision, _text(rationale, "rationale", required=False),
                  "DECIDED" if decision else "OPEN", now() if decision else None, now()))
    audit(conn, owner, "venture.decision_add", did, question[:100])
    return {"id": did}


def resolve_decision(conn, owner, did, decision, rationale=None) -> dict:
    if not isinstance(did, str) or not ID.match(did):
        raise VentureError("bad decision id")
    decision = _text(decision, "decision")
    row = conn.execute("SELECT status FROM decisions WHERE id=?", (did,)).fetchone()
    if not row:
        raise VentureError("unknown decision")
    if row["status"] == "DECIDED":
        raise VentureError("already decided; log a new decision to change course")
    conn.execute("UPDATE decisions SET decision=?, rationale=?, status='DECIDED', decided_at=? WHERE id=?",
                 (decision, _text(rationale, "rationale", required=False), now(), did))
    audit(conn, owner, "venture.decision_resolve", did, decision[:100])
    return {"id": did, "status": "DECIDED"}


def add_experiment(conn, owner, vid, hypothesis, metric=None, success_threshold=None) -> dict:
    _venture(conn, vid)
    hypothesis = _text(hypothesis, "hypothesis", limit=400)
    eid = _new_id("exp")
    conn.execute("INSERT INTO experiments(id, venture_id, hypothesis, metric, success_threshold, status, created_at) VALUES (?,?,?,?,?, 'PLANNED', ?)",
                 (eid, vid, hypothesis, _text(metric, "metric", required=False, limit=100),
                  _text(success_threshold, "success_threshold", required=False, limit=200), now()))
    audit(conn, owner, "venture.experiment_add", eid, f"{vid}: {hypothesis[:80]}")
    return {"id": eid}


def update_experiment(conn, owner, eid, status, result=None) -> dict:
    if not isinstance(eid, str) or not ID.match(eid):
        raise VentureError("bad experiment id")
    if status not in EXP_STATUS:
        raise VentureError("bad status")
    row = conn.execute("SELECT status FROM experiments WHERE id=?", (eid,)).fetchone()
    if not row:
        raise VentureError("unknown experiment")
    closing = status in ("SUCCEEDED", "FAILED", "ABANDONED")
    result = _text(result, "result", required=closing)  # a closed experiment must say what was learned
    conn.execute("UPDATE experiments SET status=?, result=COALESCE(?, result), closed_at=? WHERE id=?",
                 (status, result, now() if closing else None, eid))
    audit(conn, owner, "venture.experiment_update", eid, f"{row['status']} -> {status}")
    return {"id": eid, "status": status}


def record_metric(conn, owner, vid, name, value, source="owner") -> dict:
    _venture(conn, vid)
    if not isinstance(name, str) or not METRIC.match(name):
        raise VentureError("metric name must be lowercase letters, digits, underscores")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value or abs(value) > 1e12:
        raise VentureError("value must be a number")
    if source not in ("owner", "agent"):
        raise VentureError("bad source")
    conn.execute("INSERT INTO metrics(venture_id, name, value, source, at) VALUES (?,?,?,?,?)", (vid, name, float(value), source, now()))
    audit(conn, owner, "venture.metric", vid, f"{name}={value}")
    return {"ok": True}


def log_effort(conn, owner, vid, hours, claude_sessions=0, note=None, day=None) -> dict:
    _venture(conn, vid)
    day = day or date.today().isoformat()
    try:
        date.fromisoformat(day)
    except (ValueError, TypeError):
        raise VentureError("day must be YYYY-MM-DD")
    for v, f, hi in ((hours, "hours", 24), (claude_sessions, "claude_sessions", 1000)):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= hi:
            raise VentureError(f"{f} out of range")
    conn.execute("INSERT INTO effort_logs(venture_id, day, hours, claude_sessions, note) VALUES (?,?,?,?,?)",
                 (vid, day, float(hours), int(claude_sessions), _text(note, "note", required=False, limit=300)))
    audit(conn, owner, "venture.effort", vid, f"{hours}h, {int(claude_sessions)} claude sessions (self-reported)")
    return {"ok": True}
