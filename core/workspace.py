"""Per-business workspace read model (Phase 3). Everything is scoped to ONE business; nothing from another business is returned.

Generic sections work for any business slug (later workspaces reuse them). BuildFlow-only extras: the legacy outreach `leads`
pipeline counts and the launch-plan import. Read-only except `import_launch_plan`. Deterministic: no AI.
"""

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from core import founder, founder_dashboard as fd
from core.audit import audit
from core.db import now

PLAN = Path(__file__).resolve().parents[1] / "dashboard" / "static" / "data" / "plan.json"
PLAN_PRIORITY = {"P0": 1, "P1": 2, "P2": 3}


def _by(rows, key):
    """Aggregate posted content by one attribute. Only posts that HAVE recorded views contribute to averages."""
    groups: dict[str, dict] = {}
    for r in rows:
        k = (r.get(key) or "").strip() or "(not recorded)"
        g = groups.setdefault(k, {"name": k, "posts": 0, "with_views": 0, "views": 0, "signups": 0, "with_signups": 0})
        g["posts"] += 1
        if r["views"] is not None:
            g["with_views"] += 1
            g["views"] += r["views"]
        if r["signups"] is not None:
            g["with_signups"] += 1
            g["signups"] += r["signups"]
    out = []
    for g in groups.values():
        g["avg_views"] = round(g["views"] / g["with_views"], 1) if g["with_views"] else None
        out.append(g)
    return sorted(out, key=lambda g: (-(g["avg_views"] or -1), -g["posts"], g["name"]))[:6]


def content_summary(items: list[dict], today: date) -> dict:
    posted = [i for i in items if i["status"] == "posted"]
    since = (today - timedelta(days=6)).isoformat()
    return {
        "by_status": {s: sum(1 for i in items if i["status"] == s) for s in ("idea", "scripted", "filmed", "posted", "dropped")},
        "posted_today": sum(1 for i in posted if (i["posted_at"] or "")[:10] == today.isoformat()),
        "posted_last_7_days": sum(1 for i in posted if (i["posted_at"] or "")[:10] >= since),
        "posted_missing_metrics": sum(1 for i in posted if i["views"] is None),
        "by_platform": _by(posted, "platform"), "by_format": _by(posted, "format"), "by_topic": _by(posted, "topic"),
        "caveat": "Averages use only posts with recorded views; small samples are noise, not proof.",
    }


def _norm(v):
    return " ".join((v or "").lower().split())


def suggest_matches(listings: list[dict], demands: list[dict], limit: int = 20) -> list[dict]:
    """Rule-based supply/demand pairing. These are INFERENCES for the founder to act on, not confirmed deals.
    Same product (case-insensitive) is required; a known location mismatch or a known price above the buyer's maximum
    (same currency) rules a pair out. Unknown fields never count for or against a pair, they are listed as unknowns."""
    out = []
    for l in listings:
        if l["status"] != "open":
            continue
        for d in demands:
            if d["status"] != "open" or not _norm(l["product"]) or _norm(l["product"]) != _norm(d["product"]):
                continue
            score, why, unknown = 50, ["same product: " + l["product"]], []
            if l.get("location") and d.get("location"):
                if _norm(l["location"]) != _norm(d["location"]):
                    continue
                score += 20; why.append("same location: " + l["location"])
            else:
                unknown.append("location")
            if l.get("price") is not None and d.get("max_price") is not None and _norm(l.get("currency")) and _norm(l.get("currency")) == _norm(d.get("currency")):
                if l["price"] > d["max_price"]:
                    continue
                score += 20; why.append(f"price {l['price']:g} is within the buyer's max {d['max_price']:g} {l['currency']}")
            else:
                unknown.append("price comparison (missing price or different/missing currency)")
            if l.get("quantity") and d.get("quantity") and _norm(l.get("unit")) == _norm(d.get("unit")) and _norm(l.get("unit")):
                score += 10; why.append(f"supply {l['quantity']:g} vs need {d['quantity']:g} {l['unit']}" + (" (covers it)" if l["quantity"] >= d["quantity"] else " (partial)"))
            else:
                unknown.append("quantity comparison")
            out.append({"listing_id": l["id"], "demand_id": d["id"], "product": l["product"], "farmer": l.get("party_name"), "buyer": d.get("party_name"),
                        "score": score, "why": why, "unknown": unknown, "label": "inference"})
    out.sort(key=lambda m: (-m["score"], m["listing_id"], m["demand_id"]))
    return out[:limit]


def liquidity(listings: list[dict], demands: list[dict]) -> list[dict]:
    """Open supply vs open demand per product: counts only (units differ), flagging one-sided products."""
    prod: dict[str, dict] = {}
    for kind, rows in (("supply", listings), ("demand", demands)):
        for r in rows:
            if r["status"] != "open":
                continue
            p = prod.setdefault(_norm(r["product"]) or "(unnamed)", {"product": _norm(r["product"]) or "(unnamed)", "supply": 0, "demand": 0})
            p[kind] += 1
    out = sorted(prod.values(), key=lambda p: (-(p["supply"] + p["demand"]), p["product"]))
    for p in out:
        p["gap"] = "no buyers recorded" if p["demand"] == 0 else "no farmers recorded" if p["supply"] == 0 else "both sides present"
    return out


def transaction_summary(txns: list[dict]) -> dict:
    by_status = {s: sum(1 for t in txns if t["status"] == s) for s in ("proposed", "agreed", "completed", "cancelled")}
    money: dict[str, dict] = {}
    unvalued = 0
    for t in txns:
        if t["status"] != "completed":
            continue
        if t["amount"] is None or not (t.get("currency") or "").strip():
            unvalued += 1
            continue
        m = money.setdefault(t["currency"].strip().upper(), {"currency": t["currency"].strip().upper(), "count": 0, "amount": 0.0})
        m["count"] += 1
        m["amount"] = round(m["amount"] + t["amount"], 2)
    return {"by_status": by_status, "completed_by_currency": sorted(money.values(), key=lambda m: m["currency"]), "completed_without_value": unvalued,
            "note": "Amounts are never added across currencies; completed deals with no amount or currency are counted but not valued."}


def workspace(conn, slug: str, today: date | None = None) -> dict:
    today = today or datetime.now(timezone.utc).date()
    b = founder.get_business(conn, slug)  # NotFound for an unknown slug
    bid = b["id"]
    out: dict = {"business": {k: b[k] for k in ("id", "slug", "name", "description", "stage", "status", "priority")}, "today": today.isoformat()}

    def rows(sql, params=()):
        return fd._rows(conn, sql, params)

    def sec(name, fn):
        out[name] = fd._section(fn)

    def tasks():
        ts = rows("SELECT t.*, g.title AS goal_title, (SELECT count(*) FROM blockers k WHERE k.work_task_id=t.id AND k.status='open') AS open_blockers "
                  "FROM work_tasks t LEFT JOIN goals g ON g.id=t.goal_id WHERE t.business_id=? AND t.status NOT IN ('done','cancelled')", (bid,))
        for t in ts:
            t["business_name"] = b["name"]
        ranked = fd.rank_tasks(ts, {bid: {"priority": b["priority"] or 1}}, today)
        return ranked

    sec("tasks", tasks)
    sec("goals", lambda: rows("SELECT id,title,target_metric,target_value,current_value,due_date FROM goals WHERE business_id=? AND status='open' ORDER BY created_at", (bid,)))

    def kpis():
        ks = rows("SELECT * FROM kpis WHERE business_id=? ORDER BY is_primary DESC, created_at", (bid,))
        rd: dict = {}
        for r in rows("SELECT r.kpi_id, r.value, r.recorded_at FROM kpi_readings r JOIN kpis k ON k.id=r.kpi_id WHERE k.business_id=? ORDER BY r.recorded_at, r.id", (bid,)):
            rd.setdefault(r["kpi_id"], []).append(r)
        return [fd.kpi_view(k, rd.get(k["id"], [])) for k in ks]

    sec("kpis", kpis)
    sec("blockers", lambda: rows("SELECT k.*, t.title AS task_title FROM blockers k LEFT JOIN work_tasks t ON t.id=k.work_task_id WHERE k.business_id=? AND k.status='open' ORDER BY k.created_at", (bid,)))
    sec("experiments", lambda: rows("SELECT * FROM experiments WHERE business_id=? ORDER BY (status IN ('proposed','running')) DESC, COALESCE(review_date,'9999'), created_at DESC LIMIT 30", (bid,)))
    sec("decisions", lambda: rows("SELECT * FROM decisions WHERE business_id=? ORDER BY COALESCE(decided_at, created_at) DESC LIMIT 20", (bid,)))
    sec("knowledge", lambda: rows("SELECT id,title,body,tags,source_url,created_at FROM knowledge WHERE business_id=? ORDER BY created_at DESC LIMIT 30", (bid,)))
    sec("research", lambda: rows("SELECT id,title,question,summary,source_url,status FROM research WHERE business_id=? ORDER BY created_at DESC LIMIT 20", (bid,)))
    sec("feedback", lambda: rows("SELECT * FROM feedback_items WHERE business_id=? ORDER BY (status IN ('new','triaged')) DESC, created_at DESC LIMIT 50", (bid,)))

    def content():
        items = rows("SELECT * FROM content_items WHERE business_id=? ORDER BY COALESCE(posted_at, created_at) DESC LIMIT 200", (bid,))
        return {"items": items[:40], "summary": content_summary(items, today)}

    sec("content", content)

    if slug == "agriloop":
        def marketplace():
            parties = rows("SELECT * FROM market_parties WHERE business_id=? ORDER BY created_at DESC LIMIT 300", (bid,))
            names = {p["id"]: p["name"] for p in parties}
            listings = rows("SELECT * FROM market_listings WHERE business_id=? ORDER BY created_at DESC LIMIT 300", (bid,))
            demands = rows("SELECT * FROM market_demand WHERE business_id=? ORDER BY created_at DESC LIMIT 300", (bid,))
            txns = rows("SELECT * FROM market_transactions WHERE business_id=? ORDER BY COALESCE(occurred_at, created_at) DESC LIMIT 300", (bid,))
            for r in listings + demands:
                r["party_name"] = names.get(r["party_id"])
            funnel = {role: {st: sum(1 for p in parties if p["role"] == role and p["status"] == st) for st in ("lead", "onboarded", "active", "churned")} for role in ("farmer", "buyer")}
            buyer_of = {d["id"]: d["party_id"] for d in demands}
            done = {}
            for t in txns:
                if t["status"] == "completed" and t.get("demand_id") in buyer_of:
                    done[buyer_of[t["demand_id"]]] = done.get(buyer_of[t["demand_id"]], 0) + 1
            return {"parties": parties[:50], "funnel": funnel, "listings": listings[:50], "demand": demands[:50], "liquidity": liquidity(listings, demands),
                    "matches": suggest_matches(listings, demands), "transactions": txns[:30], "transaction_summary": transaction_summary(txns),
                    "repeat_buyers": sum(1 for n in done.values() if n >= 2), "buyers_with_completed": len(done)}

        sec("marketplace", marketplace)

    if slug == "buildflow":
        def pipeline():
            counts = {r["status"]: r["n"] for r in conn.execute("SELECT status, count(*) AS n FROM leads GROUP BY status")}
            recent = rows("SELECT id,name,business,status,source,created_at FROM leads ORDER BY created_at DESC LIMIT 10")
            return {"source": "legacy outreach leads table (owner-imported); not yet a customer/contractor CRM", "counts": counts,
                    "total": sum(counts.values()), "recent": recent}

        sec("pipeline", pipeline)
    return out


def import_launch_plan(conn, slug: str, actor: str) -> dict:
    """Create work tasks from the owner's own BuildFlow launch plan (docs/strategy/BUILDFLOW_LAUNCH_PLAN.md). Idempotent by plan id."""
    if slug != "buildflow":
        raise founder.FounderError("launch plan import is only for buildflow")
    b = founder.get_business(conn, slug)
    items = json.loads(PLAN.read_text())["buildflow"]
    from dashboard import api_data
    ticks = api_data.plan_get(conn)["ticks"]
    created = skipped = 0
    for it in items:
        marker = f"[plan:{it['id']}]"
        if conn.execute("SELECT 1 FROM work_tasks WHERE business_id=? AND description LIKE ?", (b["id"], "%" + marker + "%")).fetchone():
            skipped += 1
            continue
        done = it["id"] in ticks
        ts = now()
        conn.execute("INSERT INTO work_tasks(id,business_id,title,description,status,priority,completed_at,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT (id) DO NOTHING",
                     (f"wt_plan_{it['id'].replace('-', '_')}"[:80], b["id"], it["title"][:200], f"{it['detail']}\nOwner: {it['who']}. Source: {it['src']}. {marker}",
                      "done" if done else "todo", PLAN_PRIORITY.get(it["p"], 3), ts if done else None, ts, ts))
        created += 1
    audit(conn, actor, "founder.buildflow.import_plan", b["id"], f"created={created} skipped={skipped}")
    return {"created": created, "skipped": skipped}
