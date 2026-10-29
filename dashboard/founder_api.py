"""Founder OS HTTP routes (all authenticated by the caller). Returns None when the path is not ours.

GET  /api/founder/businesses                         the four businesses
GET  /api/founder/businesses/<slug>                  one business + record counts
GET  /api/founder/businesses/<slug>/<entity>         list that business's records
POST /api/founder/businesses/<slug>/<entity>         create (business taken from the path)
GET  /api/founder/<entity>                           list across businesses
POST /api/founder/<entity>                           create (global entities; business optional in body)
POST /api/founder/<entity>/<id>                      update
POST /api/founder/kpis/<id>/readings                 record a KPI value {value, note}
<entity> = projects goals work-tasks kpis experiments research knowledge decisions prompts ai-usage automations
"""

import json
import re

from core import founder

MAX_BODY = 8192
SLUG = r"[a-z][a-z0-9_-]{1,40}"
ID = r"[A-Za-z0-9_]{1,80}"
URL_ENTITY = {e.replace("_", "-"): e for e in founder.ENTITIES}
ENT = "(" + "|".join(URL_ENTITY) + ")"
R_BIZ_LIST = re.compile(r"^/api/founder/businesses$")
R_BIZ = re.compile(rf"^/api/founder/businesses/({SLUG})$")
R_BIZ_ENT = re.compile(rf"^/api/founder/businesses/({SLUG})/{ENT}$")
R_ENT = re.compile(rf"^/api/founder/{ENT}$")
R_ENT_ID = re.compile(rf"^/api/founder/{ENT}/({ID})$")
R_READING = re.compile(rf"^/api/founder/kpis/({ID})/readings$")


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
    if not path.startswith("/api/founder/"):
        return None
    try:
        if method == "GET" and R_BIZ_LIST.match(path):
            return _json(200, {"businesses": founder.list_businesses(conn)})
        m = R_BIZ.match(path)
        if m and method == "GET":
            return _json(200, founder.business_summary(conn, m.group(1)))
        m = R_BIZ_ENT.match(path)
        if m:
            slug, ent = m.group(1), URL_ENTITY[m.group(2)]
            if method == "GET":
                return _json(200, {ent: founder.list_rows(conn, ent, slug)})
            if method == "POST":
                return _json(201, founder.create(conn, ent, {**_body(body), "business": slug}, owner))
        m = R_READING.match(path)
        if m and method == "POST":
            data = _body(body)
            return _json(200, founder.record_kpi_reading(conn, m.group(1), data.get("value"), data.get("note"), owner))
        m = R_ENT.match(path)
        if m:
            ent = URL_ENTITY[m.group(1)]
            if method == "GET":
                return _json(200, {ent: founder.list_rows(conn, ent)})
            if method == "POST":
                if founder.ENTITIES[ent]["business"] == "required":
                    raise founder.FounderError("create via /api/founder/businesses/<slug>/" + m.group(1))
                return _json(201, founder.create(conn, ent, _body(body), owner))
        m = R_ENT_ID.match(path)
        if m and method == "POST":
            return _json(200, founder.update(conn, URL_ENTITY[m.group(1)], m.group(2), _body(body), owner))
    except founder.NotFound as e:
        return _json(404, {"error": str(e)})
    except founder.FounderError as e:
        return _json(400, {"error": str(e)})
    return _json(404, {"error": "not found"})
