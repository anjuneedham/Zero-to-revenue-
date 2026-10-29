"""Prompt Lab and Knowledge routes (owner auth is checked by the caller). Returns None when the path is not ours.

GET  /api/lab/prompts                     prompts grouped by name, newest version first (no bodies)
GET  /api/lab/prompts/<id>                one version with its body and recorded evals
POST /api/lab/prompts                     {name, body, purpose?, change_note?, business?} -> new inactive version
POST /api/lab/prompts/sync                register prompts/ai/*.md files as versions (drift reported, never overwritten)
POST /api/lab/prompts/<id>/activate       make this version the active one for its name
POST /api/lab/prompts/<id>/evals          {input, output, score 1-5, notes?} (append-only)
POST /api/lab/compare                     {a, b} two version ids of one prompt: diff + recorded score summary (no model call)
GET  /api/knowledge/<slug>                knowledge, research, evidence, sources and gaps for one business
POST /api/knowledge/<slug>/search         {q, include_global?} keyword retrieval scoped to the business
Sources and evidence are created through the CRUD API (entities `sources`, `evidence`).
"""

import json
import re

from core import founder, knowledge, prompt_lab

MAX_BODY = 40000
SLUG = r"[a-z][a-z0-9_-]{1,40}"
ID = r"[A-Za-z0-9_]{1,80}"
R_LIST = re.compile(r"^/api/lab/prompts$")
R_SYNC = re.compile(r"^/api/lab/prompts/sync$")
R_ONE = re.compile(rf"^/api/lab/prompts/({ID})$")
R_ACT = re.compile(rf"^/api/lab/prompts/({ID})/activate$")
R_EVAL = re.compile(rf"^/api/lab/prompts/({ID})/evals$")
R_CMP = re.compile(r"^/api/lab/compare$")
R_KN = re.compile(rf"^/api/knowledge/({SLUG})$")
R_SEARCH = re.compile(rf"^/api/knowledge/({SLUG})/search$")


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
    if not (path.startswith("/api/lab/") or path.startswith("/api/knowledge/")):
        return None
    try:
        if method == "GET" and R_LIST.match(path):
            return _json(200, {"prompts": prompt_lab.list_prompts(conn)})
        if method == "POST" and R_LIST.match(path):
            d = _body(body)
            return _json(201, prompt_lab.create_version(conn, d.get("name"), d.get("body"), owner, d.get("purpose"), d.get("change_note"), d.get("business") or None))
        if method == "POST" and R_SYNC.match(path):
            return _json(200, prompt_lab.sync_files(conn, owner))
        if method == "POST" and R_CMP.match(path):
            d = _body(body)
            return _json(200, prompt_lab.compare(conn, str(d.get("a", "")), str(d.get("b", ""))))
        m = R_ACT.match(path)
        if m and method == "POST":
            return _json(200, prompt_lab.activate(conn, m.group(1), owner))
        m = R_EVAL.match(path)
        if m and method == "POST":
            d = _body(body)
            return _json(201, prompt_lab.add_eval(conn, m.group(1), d.get("input"), d.get("output"), d.get("score"), d.get("notes"), owner))
        m = R_ONE.match(path)
        if m and method == "GET":
            return _json(200, prompt_lab.get_prompt(conn, m.group(1)))
        m = R_SEARCH.match(path)
        if m and method == "POST":
            d = _body(body)
            return _json(200, knowledge.search(conn, m.group(1), str(d.get("q", "")), d.get("include_global") is True))
        m = R_KN.match(path)
        if m and method == "GET":
            return _json(200, knowledge.overview(conn, m.group(1)))
    except founder.NotFound as e:
        return _json(404, {"error": str(e)})
    except founder.FounderError as e:
        return _json(400, {"error": str(e)})
    return _json(404, {"error": "not found"})
