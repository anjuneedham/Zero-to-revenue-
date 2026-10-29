"""Experiment and growth routes (owner auth is checked by the caller). Returns None when the path is not ours.

GET  /api/growth/<slug>                          experiments, overdue ones, funnels from real data, KPI trends for one business
POST /api/growth/experiments/<id>/start          proposed -> running (needs a metric and a duration)
POST /api/growth/experiments/<id>/conclude       {outcome, result, decision, decision_rationale?, learnings, result_value?, source_id?}
POST /api/growth/experiments/<id>/abandon        {reason}
Experiments themselves are created and edited through the CRUD API (entity `experiments`); status moves only here.
"""

import json
import re

from core import founder, growth

MAX_BODY = 20000
R_OV = re.compile(r"^/api/growth/([a-z][a-z0-9_-]{1,40})$")
R_ACT = re.compile(r"^/api/growth/experiments/([A-Za-z0-9_]{1,80})/(start|conclude|abandon)$")


def _json(code, obj):
    return code, "application/json", json.dumps(obj, default=str).encode()


def _body(raw):
    if len(raw) > MAX_BODY:
        raise founder.FounderError("body too large")
    try:
        data = json.loads(raw or b"{}")
    except json.JSONDecodeError:
        raise founder.FounderError("bad request") from None
    if not isinstance(data, dict):
        raise founder.FounderError("bad request")
    return data


def handle(conn, owner, method, path, body=b""):
    if not path.startswith("/api/growth/"):
        return None
    try:
        m = R_OV.match(path)
        if m and method == "GET":
            return _json(200, growth.overview(conn, m.group(1)))
        m = R_ACT.match(path)
        if m and method == "POST":
            eid, act = m.groups()
            d = _body(body)
            if act == "start":
                return _json(200, growth.start(conn, eid, owner))
            if act == "abandon":
                return _json(200, growth.abandon(conn, eid, d.get("reason"), owner))
            return _json(200, growth.conclude(conn, eid, d, owner))
    except founder.NotFound as e:
        return _json(404, {"error": str(e)})
    except founder.FounderError as e:
        return _json(400, {"error": str(e)})
    return _json(404, {"error": "not found"})
