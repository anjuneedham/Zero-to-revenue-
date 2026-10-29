"""Founder OS data layer: one declarative spec per entity, generic list/create/update.

Every write is validated against the spec (allowed columns, types, enums, required fields),
parameterised, scoped to a business, and audited. Entities that point at a parent (project, goal)
must point at one in the same business.
"""

import uuid
from decimal import Decimal, InvalidOperation

from core.audit import audit
from core.db import now

STATUSES = {
    "projects": ("planned", "active", "blocked", "done", "cancelled"),
    "goals": ("open", "achieved", "missed", "cancelled"),
    "work_tasks": ("todo", "doing", "blocked", "done", "cancelled"),
    "experiments": ("proposed", "running", "succeeded", "failed", "abandoned"),
    "blockers": ("open", "resolved"),
    "content_items": ("idea", "scripted", "filmed", "posted", "dropped"),
    "feedback_items": ("new", "triaged", "actioned", "dismissed"),
    "market_parties": ("lead", "onboarded", "active", "churned"),
    "market_listings": ("open", "matched", "closed", "expired"),
    "market_demand": ("open", "fulfilled", "closed", "expired"),
    "market_transactions": ("proposed", "agreed", "completed", "cancelled"),
    "shop_products": ("idea", "sampling", "ready", "live", "discontinued"),
    "shop_campaigns": ("planned", "running", "done", "cancelled"),
    "trading_strategies": ("idea", "researching", "backtesting", "validating", "paper", "rejected", "retired"),
    "research": ("open", "done", "archived"),
    "decisions": ("proposed", "decided", "reversed"),
}
EVIDENCE_LABELS = ("verified", "assumed", "unknown")
T, I, N, B = "text", "int", "num", "bool"


class FounderError(ValueError):
    pass


class NotFound(FounderError):
    pass


# table -> dict(prefix, business: "required"|"optional", cols: {name: (type, enum|None)}, required, parents, order)
ENTITIES = {
    "projects": dict(prefix="prj", business="required", required=("name",), order="created_at DESC",
                     cols={"name": (T, None), "description": (T, None), "status": (T, STATUSES["projects"])}),
    "goals": dict(prefix="goal", business="required", required=("title",), order="created_at DESC", parents={"project_id": "projects"},
                  cols={"title": (T, None), "description": (T, None), "target_metric": (T, None), "target_value": (N, None),
                        "current_value": (N, None), "due_date": (T, None), "project_id": (T, None), "status": (T, STATUSES["goals"])}),
    "work_tasks": dict(prefix="wt", business="required", required=("title",), order="priority ASC, created_at DESC",
                       parents={"project_id": "projects", "goal_id": "goals", "depends_on": "work_tasks"},
                       cols={"title": (T, None), "description": (T, None), "status": (T, STATUSES["work_tasks"]), "priority": (I, None),
                             "due_date": (T, None), "project_id": (T, None), "goal_id": (T, None), "impact": (I, None),
                             "effort_hours": (N, None), "depends_on": (T, None), "expected_outcome": (T, None), "next_step": (T, None)}),
    "kpis": dict(prefix="kpi", business="required", required=("name",), order="name ASC",
                 cols={"name": (T, None), "unit": (T, None), "target_value": (N, None), "current_value": (N, None),
                       "direction": (T, ("up", "down")), "baseline_value": (N, None), "is_primary": (B, None), "period": (T, None)}),
    "experiments": dict(prefix="exp", business="required", required=("hypothesis",), order="created_at DESC", parents={"goal_id": "goals", "metric_kpi_id": "kpis"},
                        # Phase 9: status/result/learnings move only through core/growth.py (start, conclude, abandon).
                        locked=("status", "result", "learnings"), force={"status": "proposed"},
                        cols={"metric_kpi_id": (T, None), "duration_days": (I, None), "hypothesis": (T, None), "method": (T, None), "success_metric": (T, None), "result": (T, None),
                              "learnings": (T, None), "goal_id": (T, None), "status": (T, STATUSES["experiments"]), "baseline_value": (N, None),
                              "target_value": (N, None), "review_date": (T, None), "next_action": (T, None)}),
    "blockers": dict(prefix="blk", business="required", required=("description",), order="created_at ASC", parents={"work_task_id": "work_tasks"},
                     cols={"description": (T, None), "impact": (T, None), "suggested_action": (T, None), "work_task_id": (T, None),
                           "status": (T, STATUSES["blockers"])}),
    "content_items": dict(prefix="cnt", business="required", required=("platform",), order="created_at DESC",
                          cols={"platform": (T, ("youtube_shorts", "tiktok", "instagram", "facebook", "other")), "topic": (T, None), "hook": (T, None),
                                "format": (T, None), "status": (T, STATUSES["content_items"]), "posted_at": (T, None), "url": (T, None),
                                "views": (I, None), "likes": (I, None), "comments": (I, None), "shares": (I, None), "signups": (I, None), "notes": (T, None)}),
    "feedback_items": dict(prefix="fb", business="required", required=("body",), order="created_at DESC", parents={"work_task_id": "work_tasks"},
                           cols={"source": (T, None), "contact": (T, None), "body": (T, None),
                                 "kind": (T, ("bug", "feature", "pricing", "onboarding", "praise", "other")), "status": (T, STATUSES["feedback_items"]),
                                 "work_task_id": (T, None)}),
    "market_parties": dict(prefix="mp", business="required", required=("name", "role"), order="created_at DESC",
                           cols={"role": (T, ("farmer", "buyer")), "name": (T, None), "location": (T, None), "contact": (T, None), "source": (T, None),
                                 "produce": (T, None), "status": (T, STATUSES["market_parties"]), "notes": (T, None)}),
    "market_listings": dict(prefix="ml", business="required", required=("party_id", "product"), order="created_at DESC", parents={"party_id": "market_parties"}, party_role="farmer",
                            cols={"party_id": (T, None), "product": (T, None), "quantity": (N, None), "unit": (T, None), "price": (N, None), "currency": (T, None),
                                  "location": (T, None), "available_from": (T, None), "status": (T, STATUSES["market_listings"])}),
    "market_demand": dict(prefix="md", business="required", required=("party_id", "product"), order="created_at DESC", parents={"party_id": "market_parties"}, party_role="buyer",
                          cols={"party_id": (T, None), "product": (T, None), "quantity": (N, None), "unit": (T, None), "max_price": (N, None), "currency": (T, None),
                                "location": (T, None), "needed_by": (T, None), "status": (T, STATUSES["market_demand"])}),
    "market_transactions": dict(prefix="mt", business="required", required=(), order="created_at DESC",
                                parents={"listing_id": "market_listings", "demand_id": "market_demand"},
                                cols={"listing_id": (T, None), "demand_id": (T, None), "quantity": (N, None), "unit": (T, None), "amount": (N, None), "currency": (T, None),
                                      "status": (T, STATUSES["market_transactions"]), "occurred_at": (T, None), "notes": (T, None)}),
    "shop_products": dict(prefix="sp", business="required", required=("name",), order="created_at DESC",
                          cols={"name": (T, None), "category": (T, None), "sku": (T, None), "status": (T, STATUSES["shop_products"]), "unit_cost": (N, None),
                                "price": (N, None), "currency": (T, None), "stock_qty": (I, None), "reorder_point": (I, None), "notes": (T, None)}),
    "shop_sales": dict(prefix="ss", business="required", required=(), order="sold_at DESC", no_updated_at=True, parents={"product_id": "shop_products"},
                       cols={"product_id": (T, None), "quantity": (I, None), "revenue": (N, None), "currency": (T, None), "channel": (T, None),
                             "customer_ref": (T, None), "sold_at": (T, None)}),
    "shop_campaigns": dict(prefix="sc", business="required", required=("name",), order="created_at DESC",
                           cols={"name": (T, None), "channel": (T, None), "status": (T, STATUSES["shop_campaigns"]), "spend": (N, None), "attributed_revenue": (N, None),
                                 "orders": (I, None), "currency": (T, None), "start_date": (T, None), "end_date": (T, None), "notes": (T, None)}),
    "trading_strategies": dict(prefix="ts", business="required", required=("name",), order="created_at DESC",
                               cols={"name": (T, None), "hypothesis": (T, None), "instrument": (T, None), "status": (T, STATUSES["trading_strategies"]),
                                     "data_notes": (T, None), "risk_notes": (T, None), "failure_conditions": (T, None),
                                     "max_drawdown_limit_pct": (N, None), "min_trades": (I, None)}),
    "trading_runs": dict(prefix="tr", business="required", required=("strategy_id", "mode"), order="created_at DESC", no_updated_at=True, immutable=True,
                         parents={"strategy_id": "trading_strategies"},
                         cols={"strategy_id": (T, None), "mode": (T, ("backtest", "out_of_sample", "walk_forward", "paper")), "period_start": (T, None),
                               "period_end": (T, None), "trades": (I, None), "net_return_pct": (N, None), "max_drawdown_pct": (N, None),
                               "costs_included": (B, None), "cost_bps": (N, None), "slippage_bps": (N, None), "data_source": (T, None),
                               "params": (T, None), "notes": (T, None)}),
    "research": dict(prefix="res", business="required", required=("title",), order="created_at DESC",
                     cols={"title": (T, None), "question": (T, None), "summary": (T, None), "source_url": (T, None),
                           "status": (T, STATUSES["research"])}),
    "knowledge": dict(prefix="kn", business="optional", required=("title", "body"), order="created_at DESC",
                      cols={"title": (T, None), "body": (T, None), "tags": (T, None), "source_url": (T, None)}),
    "decisions": dict(prefix="dec", business="optional", required=("title",), order="created_at DESC",
                      cols={"title": (T, None), "context": (T, None), "decision": (T, None), "rationale": (T, None),
                            "alternatives": (T, None), "status": (T, STATUSES["decisions"])}),
    # Phase 8: versions are immutable and activation goes through core/prompt_lab.py, so the generic path can only
    # create an inactive version or edit the purpose line.
    "prompts": dict(prefix="pr", business="optional", required=("name", "body"), order="name ASC, version DESC", force={"active": 0},
                    update_only=("purpose",),
                    cols={"name": (T, None), "purpose": (T, None), "body": (T, None), "version": (I, None), "active": (B, None)}),
    "sources": dict(prefix="src", business="required", required=("title",), order="created_at DESC",
                    cols={"title": (T, None), "url": (T, None), "kind": (T, ("web", "document", "interview", "dataset", "internal", "other")),
                          "publisher": (T, None), "retrieved_at": (T, None), "reliability": (T, ("high", "medium", "low", "unknown")), "notes": (T, None)}),
    "evidence": dict(prefix="ev", business="required", required=("claim",), order="created_at DESC",
                     parents={"research_id": "research", "knowledge_id": "knowledge", "source_id": "sources"},
                     cols={"claim": (T, None), "label": (T, EVIDENCE_LABELS), "research_id": (T, None), "knowledge_id": (T, None),
                           "source_id": (T, None), "quote": (T, None), "note": (T, None)}),
    "ai_usage": dict(prefix="use", business="optional", required=("model",), order="created_at DESC", immutable=True,
                     cols={"provider": (T, None), "model": (T, None), "purpose": (T, None), "input_tokens": (I, None),
                           "output_tokens": (I, None), "cost_usd": (N, None)}),
    "automations": dict(prefix="auto", business="optional", required=("name",), order="name ASC",
                        cols={"name": (T, None), "description": (T, None), "trigger_kind": (T, ("manual", "schedule", "event")),
                              "schedule": (T, None), "config": (T, None), "enabled": (B, None), "requires_approval": (B, None)}),
}
MAX_TEXT = 4000


def _coerce(entity, col, kind, enum, value):
    if value is None:
        return None
    if kind == T:
        if not isinstance(value, str) or len(value) > MAX_TEXT:
            raise FounderError(f"{col}: must be text up to {MAX_TEXT} characters")
        value = value.strip()
        if enum is not None and value not in enum:
            raise FounderError(f"{col}: must be one of {', '.join(enum)}")
        return value
    if isinstance(value, bool) and kind != B:
        raise FounderError(f"{col}: invalid number")
    if kind == B:
        if value in (0, 1, True, False):
            return int(value)
        raise FounderError(f"{col}: must be true or false")
    if kind == I:
        if not isinstance(value, int):
            raise FounderError(f"{col}: must be an integer")
        return value
    try:
        d = Decimal(str(value))
    except InvalidOperation:
        raise FounderError(f"{col}: must be a number") from None
    if not d.is_finite():
        raise FounderError(f"{col}: must be a finite number")
    return d


def _clean(entity, data, partial):
    spec = ENTITIES[entity]
    unknown = set(data) - set(spec["cols"]) - {"business"}
    if unknown:
        raise FounderError("unknown field(s): " + ", ".join(sorted(unknown)))
    out = {c: _coerce(entity, c, k, e, data[c]) for c, (k, e) in spec["cols"].items() if c in data}
    for r in spec["required"]:
        if (not partial or r in out) and not out.get(r):
            raise FounderError(f"{r} is required")
    return out


def get_business(conn, slug):
    row = conn.execute("SELECT * FROM businesses WHERE slug=?", (slug,)).fetchone()
    if not row:
        raise NotFound("unknown business")
    return dict(row)


def list_businesses(conn):
    return [dict(r) for r in conn.execute("SELECT * FROM businesses ORDER BY name")]


def business_summary(conn, slug):
    b = get_business(conn, slug)
    counts = {}
    for t in ("projects", "goals", "work_tasks", "kpis", "experiments", "research", "knowledge", "decisions", "automations"):
        counts[t] = conn.execute(f"SELECT count(*) AS n FROM {t} WHERE business_id=?", (b["id"],)).fetchone()["n"]
    counts["open_work_tasks"] = conn.execute(
        "SELECT count(*) AS n FROM work_tasks WHERE business_id=? AND status IN ('todo','doing','blocked')", (b["id"],)).fetchone()["n"]
    b["counts"] = counts
    return b


def _bid(conn, entity, slug, required_for_write):
    if slug:
        return get_business(conn, slug)["id"]
    if required_for_write and ENTITIES[entity]["business"] == "required":
        raise FounderError("business is required")
    return None


def list_rows(conn, entity, slug=None, status=None, limit=200):
    spec = ENTITIES[entity]
    where, params = [], []
    if slug:
        where.append("business_id=?")
        params.append(get_business(conn, slug)["id"])
    if status:
        if "status" not in spec["cols"]:
            raise FounderError("status filter not supported")
        where.append("status=?")
        params.append(status)
    sql = f"SELECT * FROM {entity}" + (" WHERE " + " AND ".join(where) if where else "") + f" ORDER BY {spec['order']} LIMIT {int(min(max(limit, 1), 500))}"
    return [dict(r) for r in conn.execute(sql, tuple(params))]


def _check_parents(conn, spec, business_id, values):
    for col, table in spec.get("parents", {}).items():
        if values.get(col):
            row = conn.execute(f"SELECT business_id FROM {table} WHERE id=?", (values[col],)).fetchone()
            if not row or row["business_id"] != business_id:
                raise FounderError(f"{col}: not found in this business")


def _check_party_role(conn, spec, values):
    """A listing must belong to a farmer and a demand row to a buyer (supply and demand never get crossed)."""
    role = spec.get("party_role")
    if role and values.get("party_id"):
        row = conn.execute("SELECT role FROM market_parties WHERE id=?", (values["party_id"],)).fetchone()
        if row and row["role"] != role:
            raise FounderError(f"party_id: must be a {role}")


def _check_evidence(values):
    """A claim hangs off a research item or knowledge note, and is 'verified' only with a source (assumptions never pass as facts)."""
    if not (values.get("research_id") or values.get("knowledge_id")):
        raise FounderError("evidence must belong to a research item or a knowledge note")
    if values.get("label") == "verified" and not values.get("source_id"):
        raise FounderError("verified evidence needs a source; otherwise label it assumed or unknown")


def _check_locked(spec, values):
    bad = [c for c in spec.get("locked", ()) if c in values]
    if bad:
        raise FounderError(", ".join(bad) + ": cannot be set directly (use the experiment start / conclude / abandon actions)")


def create(conn, entity, data, actor):
    spec = ENTITIES[entity]
    values = _clean(entity, data, partial=False)
    _check_locked(spec, values)
    values.update(spec.get("force", {}))
    if entity == "evidence":
        _check_evidence(values)
    business_id = _bid(conn, entity, data.get("business"), True)
    _check_parents(conn, spec, business_id, values)
    _check_party_role(conn, spec, values)
    if entity == "market_transactions" and values.get("status") == "completed" and not values.get("occurred_at"):
        values["occurred_at"] = now()
    if entity == "shop_sales" and not values.get("sold_at"):
        values["sold_at"] = now()
    if entity == "work_tasks" and values.get("status") == "done":
        values["completed_at"] = now()
    if entity == "decisions" and values.get("status") == "decided":
        values["decided_at"] = now()
    if entity == "content_items" and values.get("status") == "posted" and not values.get("posted_at"):
        values["posted_at"] = now()
    rid = f"{spec['prefix']}_{uuid.uuid4().hex[:12]}"
    ts = now()
    cols = {"id": rid, "business_id": business_id, **values, "created_at": ts}
    if not spec.get("immutable") and not spec.get("no_updated_at"):
        cols["updated_at"] = ts
    names = list(cols)
    try:
        conn.execute(f"INSERT INTO {entity}({','.join(names)}) VALUES ({','.join('?' * len(names))})", tuple(cols.values()))
    except Exception as e:  # unique / check violations surface as a clean 4xx, never a driver message
        if e.__class__.__module__.startswith("psycopg") and getattr(e, "sqlstate", "")[:2] == "23":
            raise FounderError("conflicts with an existing record or violates a constraint") from None
        raise
    audit(conn, actor, f"founder.{entity}.create", rid)
    return dict(conn.execute(f"SELECT * FROM {entity} WHERE id=?", (rid,)).fetchone())


def update(conn, entity, rid, data, actor):
    spec = ENTITIES[entity]
    if spec.get("immutable"):
        raise FounderError(f"{entity} records are append-only")
    if "business" in data:
        raise FounderError("business cannot be changed")
    values = _clean(entity, data, partial=True)
    if not values:
        raise FounderError("nothing to update")
    _check_locked(spec, values)
    if spec.get("update_only") and set(values) - set(spec["update_only"]):
        raise FounderError("only these fields can be edited: " + ", ".join(spec["update_only"]) + " (create a new version instead)")
    row = conn.execute(f"SELECT * FROM {entity} WHERE id=?", (rid,)).fetchone()
    if not row:
        raise NotFound("not found")
    if entity == "evidence":
        _check_evidence({**dict(row), **values})
    _check_parents(conn, spec, row["business_id"], values)
    _check_party_role(conn, spec, values)
    ts = now()
    if entity == "market_transactions" and values.get("status") == "completed" and not row["occurred_at"] and not values.get("occurred_at"):
        values["occurred_at"] = ts
    if entity == "work_tasks" and "status" in values:
        values["completed_at"] = ts if values["status"] == "done" else None
    if entity == "decisions" and values.get("status") == "decided" and not row["decided_at"]:
        values["decided_at"] = ts
    if entity == "content_items" and values.get("status") == "posted" and not row["posted_at"] and not values.get("posted_at"):
        values["posted_at"] = ts
    if entity == "blockers" and "status" in values:
        values["resolved_at"] = ts if values["status"] == "resolved" else None
    if not spec.get("no_updated_at"):
        values["updated_at"] = ts
    try:
        conn.execute(f"UPDATE {entity} SET {','.join(c + '=?' for c in values)} WHERE id=?", (*values.values(), rid))
    except Exception as e:
        if e.__class__.__module__.startswith("psycopg") and getattr(e, "sqlstate", "")[:2] == "23":
            raise FounderError("conflicts with an existing record or violates a constraint") from None
        raise
    audit(conn, actor, f"founder.{entity}.update", rid, f"label {row['label']} -> {values['label']}" if entity == "evidence" and "label" in values else None)
    return dict(conn.execute(f"SELECT * FROM {entity} WHERE id=?", (rid,)).fetchone())


def record_kpi_reading(conn, kpi_id, value, note, actor):
    v = _coerce("kpis", "value", N, None, value)
    if v is None:
        raise FounderError("value is required")
    if not conn.execute("SELECT 1 FROM kpis WHERE id=?", (kpi_id,)).fetchone():
        raise NotFound("not found")
    ts = now()
    with conn.transaction():
        conn.execute("INSERT INTO kpi_readings(kpi_id,value,note,recorded_at) VALUES (?,?,?,?)", (kpi_id, v, (note or "")[:500] or None, ts))
        conn.execute("UPDATE kpis SET current_value=?, updated_at=? WHERE id=?", (v, ts, kpi_id))
    audit(conn, actor, "founder.kpis.reading", kpi_id)
    return dict(conn.execute("SELECT * FROM kpis WHERE id=?", (kpi_id,)).fetchone())


def feedback_to_task(conn, feedback_id, actor):
    """Turn one feedback item into a work task in the same business. Idempotent: a second call returns the first task."""
    fb = conn.execute("SELECT * FROM feedback_items WHERE id=?", (feedback_id,)).fetchone()
    if not fb:
        raise NotFound("not found")
    if fb["work_task_id"]:
        return {"task_id": fb["work_task_id"], "created": False}
    ts = now()
    tid = f"wt_{uuid.uuid4().hex[:12]}"
    title = ("Feedback (" + fb["kind"] + "): " + " ".join(fb["body"].split()))[:200]
    with conn.transaction():
        conn.execute("INSERT INTO work_tasks(id,business_id,title,description,status,priority,created_at,updated_at) VALUES (?,?,?,?, 'todo', 3, ?, ?)",
                     (tid, fb["business_id"], title, fb["body"] + "\n[from feedback " + feedback_id + "]", ts, ts))
        conn.execute("UPDATE feedback_items SET work_task_id=?, status='actioned', updated_at=? WHERE id=?", (tid, ts, feedback_id))
    audit(conn, actor, "founder.feedback.to_task", feedback_id, tid)
    return {"task_id": tid, "created": True}
