"""Per-business knowledge, research evidence and retrieval (Phase 8).

* Retrieval is keyword scoring in SQL/Python: no embeddings, no model, no network. Every query is `WHERE business_id = <this
  business>`; global notes (business_id NULL) appear only when the caller opts in, and are then labelled `global`.
* A claim is `verified` (needs a source), `assumed` or `unknown`. A knowledge note or research item is only as trustworthy as
  its evidence: `trust` is derived from the labels of the evidence attached to it, never stored, never promoted.
* Source ids look like `knowledge:kn_x`, `research:res_x`, `evidence:ev_x`: the Command Center cites these, and the answer's
  claims are stored in ai_citations.
"""

import re

from core import founder

STOP = frozenset("the and for with that this from have has are was were not you your what when how why who which about into over under than then them they their there will would could should can its our out all any but too very more most some such".split())
MAX_TERMS = 8
EXCERPT = 240


def terms(query: str) -> list[str]:
    seen = []
    for w in re.findall(r"[a-z0-9]{3,}", (query or "").lower()):
        if w not in STOP and w not in seen:
            seen.append(w)
    return seen[:MAX_TERMS]


def _like(term: str) -> str:
    return "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _excerpt(text, ts):
    t = " ".join((text or "").split())
    low = t.lower()
    at = next((low.find(x) for x in ts if low.find(x) >= 0), 0)
    start = max(0, at - 60)
    return ("…" if start else "") + t[start:start + EXCERPT] + ("…" if start + EXCERPT < len(t) else "")


def _score(ts, title, body):
    tl, bl = (title or "").lower(), (body or "").lower()
    return sum(3 * (t in tl) + bl.count(t) for t in ts)


def trust_of(counts: dict) -> str:
    """unsourced (no evidence) | verified | assumed | unknown | mixed. Derived from labels only."""
    present = [k for k in ("verified", "assumed", "unknown") if counts.get(k)]
    if not present:
        return "unsourced"
    return present[0] if len(present) == 1 else "mixed"


def _evidence_counts(conn, column, ids):
    out = {i: {"verified": 0, "assumed": 0, "unknown": 0} for i in ids}
    if ids:
        for r in conn.execute(f"SELECT {column} AS pid, label, count(*) AS n FROM evidence WHERE {column} = ANY(?) GROUP BY {column}, label", (list(ids),)):
            out[r["pid"]][r["label"]] = r["n"]
    return out


def _find(conn, table, cols, biz_id, ts, limit, include_global=False):
    """Rows of one table for ONE business (plus global rows only on opt-in), ranked by term matches; recency when no terms."""
    scope = "(business_id = ? OR business_id IS NULL)" if include_global else "business_id = ?"
    params = [biz_id]
    cond = ""
    if ts:
        cond = " AND (" + " OR ".join(f"{c} ILIKE ? ESCAPE '\\'" for t in ts for c in cols) + ")"
        params += [_like(t) for t in ts for _ in cols]
    rows = [dict(r) for r in conn.execute(f"SELECT * FROM {table} WHERE {scope}{cond} ORDER BY created_at DESC LIMIT 200", tuple(params))]
    if ts:
        rows.sort(key=lambda r: -_score(ts, r.get(cols[0]), " ".join(str(r.get(c) or "") for c in cols[1:])))
    return rows[:limit]


def relevant(conn, biz_id, kind, request, limit):
    """Rows for the Command Center context: best matches for the request, else most recent. Always this business only."""
    table, cols = {"knowledge": ("knowledge", ["title", "body", "tags"]), "research": ("research", ["title", "question", "summary"]),
                   "evidence": ("evidence", ["claim", "quote", "note"])}[kind]
    rows = _find(conn, table, cols, biz_id, terms(request), limit)
    return rows or _find(conn, table, cols, biz_id, [], limit)


def search(conn, slug, query, include_global=False, limit=10) -> dict:
    biz = founder.get_business(conn, slug)
    ts = terms(query)
    if not ts:
        raise founder.FounderError("query: use at least one word of 3+ letters")
    limit = max(1, min(int(limit), 25))
    results = []
    kn = _find(conn, "knowledge", ["title", "body", "tags"], biz["id"], ts, limit, include_global)
    rs = _find(conn, "research", ["title", "question", "summary"], biz["id"], ts, limit)
    ev = _find(conn, "evidence", ["claim", "quote", "note"], biz["id"], ts, limit)
    kc, rc = _evidence_counts(conn, "knowledge_id", [r["id"] for r in kn]), _evidence_counts(conn, "research_id", [r["id"] for r in rs])
    srcs = {r["id"]: dict(r) for r in conn.execute("SELECT id,title,url,reliability FROM sources WHERE business_id=?", (biz["id"],))} if ev else {}
    for r in kn:
        results.append({"source": f"knowledge:{r['id']}", "kind": "knowledge", "id": r["id"], "title": r["title"], "scope": "global" if r["business_id"] is None else "business",
                        "excerpt": _excerpt(r["body"], ts), "score": _score(ts, r["title"], f"{r['body']} {r['tags'] or ''}"),
                        "evidence": kc[r["id"]], "trust": trust_of(kc[r["id"]])})
    for r in rs:
        results.append({"source": f"research:{r['id']}", "kind": "research", "id": r["id"], "title": r["title"], "scope": "business",
                        "excerpt": _excerpt(r["summary"] or r["question"], ts), "score": _score(ts, r["title"], f"{r['question'] or ''} {r['summary'] or ''}"),
                        "evidence": rc[r["id"]], "trust": trust_of(rc[r["id"]])})
    for r in ev:
        s = srcs.get(r["source_id"])
        results.append({"source": f"evidence:{r['id']}", "kind": "evidence", "id": r["id"], "title": r["claim"][:100], "scope": "business", "label": r["label"],
                        "excerpt": _excerpt(r["quote"] or r["claim"], ts), "score": _score(ts, r["claim"], f"{r['quote'] or ''} {r['note'] or ''}"),
                        "source_record": s, "parent": ("knowledge:" + r["knowledge_id"]) if r["knowledge_id"] else "research:" + r["research_id"]})
    results.sort(key=lambda x: -x["score"])
    return {"business": slug, "query_terms": ts, "scope": "business + global notes (opted in)" if include_global else "business only",
            "results": results[:limit], "note": "Keyword match only. 'assumed' and 'unknown' evidence is not fact; cross-business search is not available."}


def overview(conn, slug) -> dict:
    """Everything for one business: knowledge and research with derived trust, evidence, sources, and gaps to close."""
    biz = founder.get_business(conn, slug)
    bid = biz["id"]
    kn = [dict(r) for r in conn.execute("SELECT * FROM knowledge WHERE business_id=? ORDER BY created_at DESC LIMIT 100", (bid,))]
    rs = [dict(r) for r in conn.execute("SELECT * FROM research WHERE business_id=? ORDER BY created_at DESC LIMIT 100", (bid,))]
    ev = [dict(r) for r in conn.execute("SELECT * FROM evidence WHERE business_id=? ORDER BY created_at DESC LIMIT 500", (bid,))]
    srcs = [dict(r) for r in conn.execute("SELECT * FROM sources WHERE business_id=? ORDER BY created_at DESC LIMIT 200", (bid,))]
    by_src = {s["id"]: s for s in srcs}
    for e in ev:
        s = by_src.get(e["source_id"])
        e["source_title"] = s["title"] if s else None
        e["source_reliability"] = s["reliability"] if s else None
        e["weak_source"] = bool(e["label"] == "verified" and s and s["reliability"] in ("low", "unknown"))
    for key, rows in (("knowledge_id", kn), ("research_id", rs)):
        for r in rows:
            mine = [e for e in ev if e[key] == r["id"]]
            r["evidence_counts"] = {l: sum(1 for e in mine if e["label"] == l) for l in founder.EVIDENCE_LABELS}
            r["trust"] = trust_of(r["evidence_counts"])
    counts = {l: sum(1 for e in ev if e["label"] == l) for l in founder.EVIDENCE_LABELS}
    gaps = {"unsourced_knowledge": [r["id"] for r in kn if r["trust"] == "unsourced"],
            "unsourced_research": [r["id"] for r in rs if r["trust"] == "unsourced"],
            "verified_on_weak_source": [e["id"] for e in ev if e["weak_source"]]}
    return {"business": slug, "knowledge": kn, "research": rs, "evidence": ev, "sources": srcs, "evidence_counts": counts, "gaps": gaps}
