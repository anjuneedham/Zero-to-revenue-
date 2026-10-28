"""Routes for the venture workspace. Returns (status, content_type, bytes) or None if the path is not ours."""

import json
import re

from core import ventures as v

MAX_BODY = 4096
VENTURE_RE = re.compile(r"^/api/ventures/([a-z0-9_-]{1,40})(?:/(stage|tasks|experiments|metrics|effort))?$")
ITEM_RE = re.compile(r"^/api/(tasks|decisions|experiments)/([a-z]{1,4}_[a-f0-9]{12})$")


def _out(code, obj):
    return code, "application/json", json.dumps(obj).encode()


def _data(body):
    if len(body) > MAX_BODY:
        raise ValueError("body too large")
    d = json.loads(body or b"{}")
    if not isinstance(d, dict):
        raise ValueError("bad request")
    return d


def handle(method, path, body, conn, owner):
    if not (path in ("/api/ventures", "/api/decisions") or VENTURE_RE.match(path) or ITEM_RE.match(path)):
        return None
    try:
        if path == "/api/ventures" and method == "GET":
            return _out(200, v.overview(conn))
        if path == "/api/decisions" and method == "POST":
            d = _data(body)
            return _out(200, v.add_decision(conn, owner, d.get("question"), d.get("venture_id") or None, d.get("decision"), d.get("rationale")))
        m = VENTURE_RE.match(path)
        if m:
            vid, sub = m.groups()
            if sub is None and method == "GET":
                return _out(200, v.venture_detail(conn, vid))
            if method == "POST" and sub:
                d = _data(body)
                if sub == "stage":
                    return _out(200, v.set_stage(conn, owner, vid, d.get("stage"), d.get("reason")))
                if sub == "tasks":
                    return _out(200, v.add_task(conn, owner, vid, d.get("title"), d.get("owner", "founder"), d.get("due_at"), d.get("note")))
                if sub == "experiments":
                    return _out(200, v.add_experiment(conn, owner, vid, d.get("hypothesis"), d.get("metric"), d.get("success_threshold")))
                if sub == "metrics":
                    return _out(200, v.record_metric(conn, owner, vid, d.get("name"), d.get("value"), d.get("source", "owner")))
                if sub == "effort":
                    return _out(200, v.log_effort(conn, owner, vid, d.get("hours", 0), d.get("claude_sessions", 0), d.get("note"), d.get("day")))
        m = ITEM_RE.match(path)
        if m and method == "POST":
            kind, iid = m.groups()
            d = _data(body)
            if kind == "tasks":
                return _out(200, v.update_task(conn, owner, iid, d.get("status"), d.get("note")))
            if kind == "decisions":
                return _out(200, v.resolve_decision(conn, owner, iid, d.get("decision"), d.get("rationale")))
            return _out(200, v.update_experiment(conn, owner, iid, d.get("status"), d.get("result")))
    except v.VentureError as e:
        return _out(400, {"error": str(e)})
    except (ValueError, json.JSONDecodeError):
        return _out(400, {"error": "bad request"})
    return _out(404, {"error": "not found"})
