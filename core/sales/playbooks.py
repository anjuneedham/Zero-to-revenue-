"""Editable playbooks and the runs that execute them.

A playbook is plain data (name, fields, ordered steps). A run copies the steps when it starts, so editing a
playbook later never rewrites what you actually did. One live task per run points at the next incomplete step."""

import json

from core.db import now
from core.sales import pipeline
from core.sales.events import NotFound, log, new_id, text
from core.sales.seed import BUILTIN

LIST_FIELDS = ("prerequisites", "recommended_actions", "example_messages", "common_mistakes")
TEXT_FIELDS = ("name", "objective", "intended_user", "when_to_use", "expected_outcome", "completion_criteria", "next_recommended")
MAX_STEPS = 40


def ensure_seed(conn) -> None:
    """Insert any built-in playbook that is missing. Never touches ones that exist (owner edits are kept)."""
    have = {r["builtin_slug"] for r in conn.execute("SELECT builtin_slug FROM playbooks WHERE builtin_slug IS NOT NULL")}
    stamp = now()
    for b in BUILTIN:
        if b["slug"] in have:
            continue
        steps = [{"id": f"s{i}", **s} for i, s in enumerate(b["steps"], 1)]
        conn.execute("INSERT INTO playbooks(id,name,builtin_slug,objective,intended_user,when_to_use,prerequisites,steps,recommended_actions,"
                     "example_messages,expected_outcome,completion_criteria,common_mistakes,next_recommended,created_at,updated_at) "
                     "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT (builtin_slug) DO NOTHING",
                     ("pb_" + b["slug"].replace("-", "_"), b["name"], b["slug"], b["objective"], b["intended_user"], b["when_to_use"],
                      json.dumps(b["prerequisites"]), json.dumps(steps), json.dumps(b["recommended_actions"]),
                      json.dumps(b["example_messages"]), b["expected_outcome"], b["completion_criteria"],
                      json.dumps(b["common_mistakes"]), b["next_recommended"], stamp, stamp))


def _load(row) -> dict:
    d = dict(row)
    for f in LIST_FIELDS + ("steps",):
        d[f] = json.loads(d[f] or "[]")
    return d


def get(conn, pid) -> dict:
    r = conn.execute("SELECT * FROM playbooks WHERE id=?", (pid,)).fetchone()
    if not r:
        raise NotFound("playbook not found")
    return _load(r)


def list_all(conn, include_archived=False) -> list[dict]:
    ensure_seed(conn)
    q = "SELECT * FROM playbooks" + ("" if include_archived else " WHERE archived=FALSE") + " ORDER BY (builtin_slug IS NULL), name"
    stats = {r["playbook_id"]: r for r in conn.execute(
        "SELECT playbook_id, count(*) runs, count(*) FILTER (WHERE status='completed') completed FROM playbook_runs GROUP BY playbook_id")}
    out = []
    for r in conn.execute(q):
        d = _load(r)
        s = stats.get(d["id"])
        d["runs"], d["runs_completed"] = (s["runs"], s["completed"]) if s else (0, 0)
        out.append(d)
    return out


def _clean(data: dict, cur: dict | None = None) -> dict:
    out = {}
    for f in TEXT_FIELDS:
        if f in data:
            out[f] = text(data[f], 2000, f) or ""
    for f in LIST_FIELDS:
        if f in data:
            v = data[f]
            if not isinstance(v, list) or len(v) > 30:
                raise ValueError(f"{f.replace('_', ' ')} must be a list of up to 30 items")
            out[f] = [t for t in (text(x, 1500, f) for x in v) if t]
    if "steps" in data:
        v = data["steps"]
        if not isinstance(v, list) or not v or len(v) > MAX_STEPS:
            raise ValueError(f"a playbook needs 1 to {MAX_STEPS} steps")
        used, steps = set(), []
        for s in v:
            if not isinstance(s, dict):
                raise ValueError("bad step")
            title = text(s.get("title"), 200, "step title")
            if not title:
                raise ValueError("every step needs a title")
            sid = s.get("id") if isinstance(s.get("id"), str) and s.get("id") and len(s["id"]) <= 20 and s["id"] not in used else new_id("st")[:12]
            used.add(sid)
            steps.append({"id": sid, "title": title, "instruction": text(s.get("instruction"), 1500, "instruction") or ""})
        out["steps"] = steps
    if "name" in out and not out["name"]:
        raise ValueError("a playbook needs a name")
    return out


def create(conn, data: dict, parent_id=None) -> dict:
    ensure_seed(conn)
    f = _clean(data)
    if not f.get("name"):
        raise ValueError("a playbook needs a name")
    f.setdefault("steps", [{"id": "s1", "title": "First step", "instruction": ""}])
    pid, stamp = new_id("pb"), now()
    cols = {"id": pid, "parent_id": parent_id, "created_at": stamp, "updated_at": stamp}
    cols.update({k: json.dumps(v) if isinstance(v, list) else v for k, v in f.items()})
    conn.execute(f"INSERT INTO playbooks({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", tuple(cols.values()))
    return get(conn, pid)


def update(conn, pid, data: dict) -> dict:
    cur = get(conn, pid)
    f = _clean(data, cur)
    if not f:
        return cur
    sets = ", ".join(f"{k}=?" for k in f) + ", version=version+1, updated_at=?"
    conn.execute(f"UPDATE playbooks SET {sets} WHERE id=?",
                 (*[json.dumps(v) if isinstance(v, list) else v for v in f.values()], now(), pid))
    return get(conn, pid)


def duplicate(conn, pid, name=None) -> dict:
    src = get(conn, pid)
    data = {k: src[k] for k in TEXT_FIELDS + LIST_FIELDS + ("steps",)}
    data["name"] = text(name, 200, "name") or src["name"] + " (copy)"
    return create(conn, data, parent_id=pid)


def set_archived(conn, pid, archived: bool) -> dict:
    get(conn, pid)
    conn.execute("UPDATE playbooks SET archived=?, updated_at=? WHERE id=?", (bool(archived), now(), pid))
    return get(conn, pid)


# ---------------------------------------------------------------- runs ----------------------------------------------

def _run(row) -> dict:
    d = dict(row)
    d["steps"], d["progress"] = json.loads(d["steps"]), json.loads(d["progress"] or "{}")
    d["done_count"] = sum(1 for s in d["steps"] if s["id"] in d["progress"])
    d["next_step"] = next((s for s in d["steps"] if s["id"] not in d["progress"]), None)
    return d


def get_run(conn, rid) -> dict:
    r = conn.execute("SELECT r.*, l.business AS lead_business, l.name AS lead_name FROM playbook_runs r "
                     "LEFT JOIN leads l ON l.id=r.lead_id WHERE r.id=?", (rid,)).fetchone()
    if not r:
        raise NotFound("playbook run not found")
    return _run(r)


def runs_for_lead(conn, lead_id) -> list[dict]:
    return [_run(r) for r in conn.execute(
        "SELECT r.*, NULL AS lead_business, NULL AS lead_name FROM playbook_runs r WHERE lead_id=? ORDER BY started_at DESC", (lead_id,))]


def list_runs(conn, playbook_id=None, limit=100) -> list[dict]:
    q = ("SELECT r.*, l.business AS lead_business, l.name AS lead_name FROM playbook_runs r LEFT JOIN leads l ON l.id=r.lead_id")
    args = []
    if playbook_id:
        q += " WHERE r.playbook_id=?"
        args.append(playbook_id)
    return [_run(r) for r in conn.execute(q + " ORDER BY r.started_at DESC LIMIT ?", (*args, min(limit, 300)))]


def _sync_task(conn, run: dict) -> None:
    """Exactly one open task per in-progress run, pointing at the next incomplete step."""
    open_t = conn.execute("SELECT id, step_id FROM sales_tasks WHERE run_id=? AND status='open'", (run["id"],)).fetchall()
    nxt = run["next_step"] if run["status"] == "in_progress" else None
    for t in open_t:
        if not nxt or t["step_id"] != nxt["id"]:
            conn.execute("UPDATE sales_tasks SET status='skipped', outcome='superseded', completed_at=? WHERE id=?", (now(), t["id"]))
    if nxt and not any(t["step_id"] == nxt["id"] for t in open_t):
        pipeline.create_task(conn, {"lead_id": run["lead_id"], "title": f"{nxt['title']} ({run['playbook_name']})", "detail": nxt["instruction"],
                                    "kind": "playbook", "playbook_id": run["playbook_id"], "run_id": run["id"], "step_id": nxt["id"]})


def start_run(conn, playbook_id, lead_id=None) -> dict:
    ensure_seed(conn)
    pb = get(conn, playbook_id)
    if pb["archived"]:
        raise ValueError("that playbook is archived")
    if lead_id:
        lead = pipeline.get_lead(conn, lead_id)
        if lead["playbook_run_id"]:
            raise ValueError("this prospect already has a playbook in progress; finish or abandon it first")
    rid = new_id("run")
    conn.execute("INSERT INTO playbook_runs(id,playbook_id,playbook_name,playbook_version,lead_id,steps,started_at) VALUES (?,?,?,?,?,?,?)",
                 (rid, pb["id"], pb["name"], pb["version"], lead_id, json.dumps(pb["steps"]), now()))
    if lead_id:
        conn.execute("UPDATE leads SET playbook_run_id=?, updated_at=? WHERE id=?", (rid, now(), lead_id))
    run = get_run(conn, rid)
    _sync_task(conn, run)
    log(conn, lead_id, "playbook_started", f"Playbook started: {pb['name']}", {"playbook_id": pb["id"], "version": pb["version"]}, run_id=rid)
    return get_run(conn, rid)


def set_step(conn, rid, step_id, done: bool, note=None) -> dict:
    run = get_run(conn, rid)
    if run["status"] != "in_progress":
        raise ValueError("this playbook run is " + run["status"])
    step = next((s for s in run["steps"] if s["id"] == step_id), None)
    if not step:
        raise NotFound("step not found")
    prog = run["progress"]
    note = text(note, 1000)
    if done:
        prog[step_id] = {"done_at": now(), "note": note}
        # close the live task for this step (if any) as done
        for t in conn.execute("SELECT id FROM sales_tasks WHERE run_id=? AND step_id=? AND status='open'", (rid, step_id)).fetchall():
            pipeline.close_task(conn, t["id"], "done", note)
    else:
        prog.pop(step_id, None)
    conn.execute("UPDATE playbook_runs SET progress=? WHERE id=?", (json.dumps(prog), rid))
    log(conn, run["lead_id"], "step_completed" if done else "step_reopened",
        ("Step done: " if done else "Step reopened: ") + step["title"], {"step_id": step_id, "playbook": run["playbook_name"], "note": note}, run_id=rid)
    run = get_run(conn, rid)
    if done and run["done_count"] == len(run["steps"]):
        conn.execute("UPDATE playbook_runs SET status='completed', completed_at=? WHERE id=?", (now(), rid))
        if run["lead_id"]:
            conn.execute("UPDATE leads SET playbook_run_id=NULL WHERE id=? AND playbook_run_id=?", (run["lead_id"], rid))
        nxt = conn.execute("SELECT next_recommended FROM playbooks WHERE id=?", (run["playbook_id"],)).fetchone()
        log(conn, run["lead_id"], "playbook_completed", f"Playbook completed: {run['playbook_name']}",
            {"next_recommended": nxt["next_recommended"] if nxt else ""}, run_id=rid)
        run = get_run(conn, rid)
    _sync_task(conn, run)
    return get_run(conn, rid)


def abandon_run(conn, rid, note=None) -> dict:
    run = get_run(conn, rid)
    if run["status"] != "in_progress":
        raise ValueError("this playbook run is already " + run["status"])
    conn.execute("UPDATE playbook_runs SET status='abandoned', completed_at=?, outcome_note=? WHERE id=?", (now(), text(note, 1000), rid))
    if run["lead_id"]:
        conn.execute("UPDATE leads SET playbook_run_id=NULL WHERE id=? AND playbook_run_id=?", (run["lead_id"], rid))
    run = get_run(conn, rid)
    _sync_task(conn, run)
    log(conn, run["lead_id"], "playbook_abandoned", f"Playbook abandoned: {run['playbook_name']} ({run['done_count']}/{len(run['steps'])} steps done)",
        {"note": text(note, 500), "done": run["done_count"], "total": len(run["steps"])}, run_id=rid)
    return run
