"""HTTP layer for the sales execution system (/api/sales/*). The caller (dashboard.app.handle) has already
authenticated the owner. Returns (status, content_type, bytes). Errors we raise on purpose carry safe messages;
anything unexpected propagates and the server answers with a generic 503, never driver text."""

import json
import re

from core.sales import insights, pipeline, playbooks
from core.sales.events import ALL_STAGES, ACTIVE, CHANNELS, CLOSED, PARKED, SENTIMENTS, STAGE_LABEL, STAGES, TASK_KINDS, NotFound, tz_name

SALES_MAX_BODY = 65_536
ID = r"([A-Za-z0-9_]{1,40})"


def _out(code, obj):
    return code, "application/json", json.dumps(obj, default=str).encode()


def _data(body: bytes) -> dict:
    if len(body) > SALES_MAX_BODY:
        raise ValueError("request too large")
    try:
        d = json.loads(body or b"{}")
    except ValueError:
        raise ValueError("bad request") from None
    if not isinstance(d, dict):
        raise ValueError("bad request")
    return d


def _meta(conn):
    return {"stages": [{"id": s, "label": l} for s, l in STAGES], "closed": [{"id": s, "label": STAGE_LABEL[s]} for s in CLOSED],
            "parked": [{"id": s, "label": STAGE_LABEL[s]} for s in PARKED], "channels": list(CHANNELS), "sentiments": list(SENTIMENTS),
            "task_kinds": list(TASK_KINDS), "timezone": tz_name(conn), "targets": insights.get_targets(conn)}


def _prospect_action(conn, lid, action, d):
    g = d.get
    when = g("occurred_at") or None
    if action == "update":
        pipeline.update_prospect(conn, lid, d)
    elif action == "research":
        pipeline.record_research(conn, lid, g("notes"), when)
    elif action == "qualify":
        pipeline.qualify(conn, lid, g("decision"), g("reasons"), when)
    elif action == "stage":
        pipeline.move_stage(conn, lid, g("to"), g("note"), when)
    elif action == "prepare":
        pipeline.prepare_message(conn, lid, g("channel"), g("angle"), g("text"), when)
    elif action == "outreach":
        pipeline.record_outreach(conn, lid, g("channel"), g("angle"), g("text"), when, g("followup_in_days"))
    elif action == "response":
        pipeline.record_response(conn, lid, g("text"), g("sentiment") or "neutral", g("channel") or None, when)
    elif action == "followup":
        pipeline.schedule_followup(conn, lid, g("due_date"), g("note"), g("priority") or "normal")
    elif action == "meeting":
        pipeline.record_meeting(conn, lid, g("when"), g("notes"), bool(g("held")), when)
    elif action == "proposal":
        pipeline.record_proposal(conn, lid, g("value"), g("notes"), when)
    elif action == "close":
        pipeline.close_prospect(conn, lid, g("outcome"), g("reason"), g("revenue"), g("resume_date"), when)
    elif action == "note":
        pipeline.add_note(conn, lid, g("text"))
    elif action == "playbook":
        playbooks.start_run(conn, g("playbook_id"), lid)
    elif action == "delete":
        pipeline.delete_prospect(conn, lid)
        return {"deleted": True}
    else:
        raise NotFound("unknown action")
    return pipeline.prospect_view(conn, lid)


def handle(method, path, conn, body: bytes):
    p = path[len("/api/sales/"):].strip("/")
    try:
        if method == "GET":
            if p == "meta":
                return _out(200, _meta(conn))
            if p == "today":
                return _out(200, insights.today_view(conn))
            if p == "insights/performance":
                return _out(200, insights.performance(conn))
            if p == "insights/learning":
                return _out(200, insights.learning(conn))
            if p == "targets":
                return _out(200, {"targets": insights.get_targets(conn), "timezone": tz_name(conn)})
            if p == "prospects":
                return _out(200, {"prospects": pipeline.list_prospects(conn)})
            if p == "tasks":
                return _out(200, {"tasks": pipeline.list_tasks(conn, "open")})
            if p == "activity":
                return _out(200, {"events": pipeline.business_activity(conn, 100)})
            if m := re.fullmatch(r"activity/before/(\d{1,12})", p):
                return _out(200, {"events": pipeline.business_activity(conn, 100, m.group(1))})
            if p == "playbooks":
                return _out(200, {"playbooks": playbooks.list_all(conn, include_archived=True)})
            if m := re.fullmatch(rf"playbooks/{ID}", p):
                return _out(200, {"playbook": playbooks.get(conn, m.group(1))})
            if m := re.fullmatch(rf"playbooks/{ID}/runs", p):
                return _out(200, {"runs": playbooks.list_runs(conn, m.group(1))})
            if p == "runs":
                return _out(200, {"runs": playbooks.list_runs(conn)})
            if m := re.fullmatch(rf"runs/{ID}", p):
                return _out(200, {"run": playbooks.get_run(conn, m.group(1))})
            if m := re.fullmatch(rf"prospects/{ID}", p):
                return _out(200, pipeline.prospect_view(conn, m.group(1)))
            return _out(404, {"error": "not found"})
        if method != "POST":
            return _out(404, {"error": "not found"})
        d = _data(body)
        if p == "prospects":
            lead = pipeline.create_prospect(conn, d, d.get("occurred_at") or None)
            if d.get("playbook_id"):
                playbooks.start_run(conn, d["playbook_id"], lead["id"])
            return _out(200, pipeline.prospect_view(conn, lead["id"]))
        if m := re.fullmatch(rf"prospects/{ID}/(\w+)", p):
            return _out(200, _prospect_action(conn, m.group(1), m.group(2), d))
        if p == "tasks":
            return _out(200, {"task": pipeline.create_task(conn, d)})
        if m := re.fullmatch(rf"tasks/{ID}/(complete|skip)", p):
            fn = pipeline.complete_task if m.group(2) == "complete" else pipeline.skip_task
            return _out(200, {"task": fn(conn, m.group(1), d.get("outcome"))})
        if p == "targets":
            return _out(200, {"targets": insights.set_targets(conn, d), "timezone": tz_name(conn)})
        if p == "review":
            return _out(200, insights.record_review(conn, d.get("note")))
        if p == "playbooks":
            return _out(200, {"playbook": playbooks.create(conn, d)})
        if m := re.fullmatch(rf"playbooks/{ID}/(update|duplicate|archive|unarchive|start)", p):
            pid, verb = m.groups()
            if verb == "update":
                return _out(200, {"playbook": playbooks.update(conn, pid, d)})
            if verb == "duplicate":
                return _out(200, {"playbook": playbooks.duplicate(conn, pid, d.get("name"))})
            if verb in ("archive", "unarchive"):
                return _out(200, {"playbook": playbooks.set_archived(conn, pid, verb == "archive")})
            return _out(200, {"run": playbooks.start_run(conn, pid, d.get("lead_id") or None)})
        if m := re.fullmatch(rf"runs/{ID}/step", p):
            if not isinstance(d.get("done"), bool) or not isinstance(d.get("step_id"), str):
                raise ValueError("bad request")
            return _out(200, {"run": playbooks.set_step(conn, m.group(1), d["step_id"], d["done"], d.get("note"))})
        if m := re.fullmatch(rf"runs/{ID}/abandon", p):
            return _out(200, {"run": playbooks.abandon_run(conn, m.group(1), d.get("note"))})
        return _out(404, {"error": "not found"})
    except NotFound as e:
        return _out(404, {"error": str(e)})
    except (ValueError, TypeError) as e:
        return _out(400, {"error": str(e) if isinstance(e, ValueError) else "bad request"})
