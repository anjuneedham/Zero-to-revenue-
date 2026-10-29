"""Experiment and growth routes (owner auth is checked by the caller). Returns None when the path is not ours.

GET  /api/growth/<slug>                          funnel (from recorded data) + experiments with evaluation and counts
POST /api/growth/experiments/<id>/start          proposed -> running (needs success metric and duration)
POST /api/growth/experiments/<id>/conclude       {outcome, decision, learnings, result?, result_value?, sample_size?, decision_note?}
POST /api/growth/experiments/<id>/abandon        {reason}
Experiments are created and their plan edited (while proposed) through the CRUD API (entity `experiments`). Nothing here executes
an experiment: it only records the founder's start, result, decision and learning.
"""

import json
import re

from core import experiments, founder, growth

MAX_BODY = 8192
SLUG = r"[a-z][a-z0-9_-]{1,40}"
ID = r"[A-Za-z0-9_]{1,80}"
R_BIZ = re.compile(rf"^/api/growth/({SLUG})$")
R_ACT = re.compile(rf"^/api/growth/experiments/({ID})/(start|conclude|abandon)$")


def _json(code, obj):
    return code, "application/json", json.dumps(obj, default=str).encode()


def _body(raw):
    if len(raw) > MAX_BODY:
        raise founder.FounderError("body too large")
    try:
        d = json.loads(raw or b"{}")
    except json.JSONDecodeError:
        raise founder.FounderError("bad request") from None
    if not isinstance(d, dict):
        raise founder.FounderError("bad request")
    return d


def handle(conn, owner, method, path, body=b""):
    if not path.startswith("/api/growth/"):
        return None
    try:
        m = R_BIZ.match(path)
        if m and method == "GET":
            return _json(200, {**experiments.for_business(conn, m.group(1)), "funnel": growth.funnel(conn, m.group(1))})
        m = R_ACT.match(path)
        if m and method == "POST":
            eid, act, d = m.group(1), m.group(2), _body(body)
            if act == "start":
                return _json(200, experiments.start(conn, eid, owner))
            if act == "abandon":
                return _json(200, experiments.abandon(conn, eid, d.get("reason"), owner))
            return _json(200, experiments.conclude(conn, eid, owner, d.get("outcome"), d.get("result"), d.get("result_value"), d.get("sample_size"),
                                                   d.get("learnings"), d.get("decision"), d.get("decision_note")))
    except founder.NotFound as e:
        return _json(404, {"error": str(e)})
    except founder.FounderError as e:
        return _json(400, {"error": str(e)})
    return _json(404, {"error": "not found"})
