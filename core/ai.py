"""AI Command Center orchestration (Phase 7): the single path every Founder OS model call takes.

classify -> route (core/ai_config.py) -> business-scoped context -> budget reservation -> call -> validate -> ledgers.

Guarantees, each covered by tests/unit/test_ai.py:
* NO AI tasks never reach a model. Routing is deterministic code; a keyword can only raise caution, never lower it.
* Context is read with `WHERE business_id = <this business>` only. Global (NULL-business) rows are not included.
* The reply must be the exact JSON envelope; anything else is discarded. The model cannot trigger actions, and a
  claim labelled "verified" without a source id from the supplied context is downgraded to "unknown".
* Every attempted call reserves its worst-case cost first (core/budget.py, hard monthly cap, fails closed), then
  writes one `llm_usage` row (budget ledger) and one `ai_usage` row (per-business ledger).
* The kill switch pauses model calls. Nothing here executes an action; answers are advisory.
"""

import json
import re
import time
import uuid
from pathlib import Path

from core import ai_config as cfg
from core import budget, founder
from core.audit import audit
from core.db import now
from core.orchestrator import killswitch

SYSTEM = (Path(__file__).resolve().parents[1] / "prompts" / "ai" / f"{cfg.PROMPT_VERSION}.md").read_text().strip()
AGENT = "command_center"
LABELS = ("verified", "assumed", "unknown")
GUARANTEE = re.compile(r"guarantee[sd]?\s+(?:\w+\s+){0,3}(?:profit|returns?|income|revenue)|risk[- ]free|can'?t lose|cannot lose", re.I)


class AiError(ValueError):
    pass


# --- classification (NO AI: deterministic) ---------------------------------------------------------------------------

def classify(text: str, task_type: str | None = None, min_level: str | None = None) -> dict:
    """Choose task type and routing level. Explicit task_type wins over keywords; stakes words raise the level one step."""
    low = (text or "").lower()
    reasons = []
    if task_type:
        if task_type not in cfg.TASKS:
            raise AiError("unknown task type")
        reasons.append("task type given by caller")
    else:
        task_type = next((t for t, words in cfg.RULES if any(w in low for w in words)), None)
        reasons.append("matched a keyword rule" if task_type else "no rule matched; default task type")
        task_type = task_type or cfg.DEFAULT_TASK
    spec = cfg.TASKS[task_type]
    level = spec["level"]
    stakes = bool(spec["stakes"]) or any(w in low for w in cfg.STAKES_WORDS)
    if stakes and level != cfg.NO_AI:
        if not spec["stakes"] and level != cfg.HIGH:
            level = cfg.ORDER[cfg.ORDER.index(level) + 1]
            reasons.append("high-stakes wording: level raised one step")
        reasons.append("high-stakes: result is flagged for founder approval")
    if min_level:
        if min_level not in cfg.ORDER:
            raise AiError("unknown level")
        if cfg.ORDER.index(min_level) > cfg.ORDER.index(level):
            level = min_level
            reasons.append("escalated by caller")
    return {"task_type": task_type, "level": level, "stakes": stakes, "reasons": reasons,
            "model": cfg.model_for(level) if level != cfg.NO_AI else None}


# --- business-scoped context -----------------------------------------------------------------------------------------

def _t(v, n=cfg.MAX_ROW_CHARS):
    return " ".join(str(v if v is not None else "").split())[:n]


# kind -> (SQL with one `business_id = ?` placeholder, row -> text)
_CONTEXT = {
    "goals": ("SELECT id,title,target_metric,target_value,current_value,due_date FROM goals WHERE business_id=? AND status='open' ORDER BY created_at DESC LIMIT ?",
              lambda r: f"goal: {_t(r['title'])} (metric {_t(r['target_metric'])}: {r['current_value']} of {r['target_value']}, due {r['due_date']})"),
    "tasks": ("SELECT id,title,status,priority,due_date FROM work_tasks WHERE business_id=? AND status NOT IN ('done','cancelled') ORDER BY priority ASC, created_at DESC LIMIT ?",
              lambda r: f"task: {_t(r['title'])} [{r['status']}, priority {r['priority']}, due {r['due_date']}]"),
    "kpis": ("SELECT id,name,unit,current_value,target_value FROM kpis WHERE business_id=? ORDER BY is_primary DESC, created_at LIMIT ?",
             lambda r: f"kpi: {_t(r['name'])} = {r['current_value']} {_t(r['unit'], 20)} (target {r['target_value']})"),
    "blockers": ("SELECT id,description FROM blockers WHERE business_id=? AND status='open' ORDER BY created_at DESC LIMIT ?",
                 lambda r: f"open blocker: {_t(r['description'])}"),
    "decisions": ("SELECT id,title,decision,status FROM decisions WHERE business_id=? ORDER BY created_at DESC LIMIT ?",
                  lambda r: f"decision [{r['status']}]: {_t(r['title'])} -> {_t(r['decision'])}"),
    "knowledge": ("SELECT id,title,body FROM knowledge WHERE business_id=? ORDER BY created_at DESC LIMIT ?",
                  lambda r: f"note: {_t(r['title'])}: {_t(r['body'])}"),
    "research": ("SELECT id,title,summary FROM research WHERE business_id=? ORDER BY created_at DESC LIMIT ?",
                 lambda r: f"research: {_t(r['title'])}: {_t(r['summary'])}"),
    "strategies": ("SELECT id,name,hypothesis,status,failure_conditions,max_drawdown_limit_pct FROM trading_strategies WHERE business_id=? ORDER BY created_at DESC LIMIT ?",
                   lambda r: f"strategy {_t(r['name'])} [{r['status']}]: {_t(r['hypothesis'])}; failure conditions: {_t(r['failure_conditions'])}; drawdown limit {r['max_drawdown_limit_pct']}%"),
    "runs": ("SELECT id,strategy_id,mode,trades,net_return_pct,max_drawdown_pct,costs_included,slippage_bps FROM trading_runs WHERE business_id=? ORDER BY created_at DESC LIMIT ?",
             lambda r: f"run of {r['strategy_id']} [{r['mode']}]: {r['trades']} trades, net {r['net_return_pct']}%, max drawdown {r['max_drawdown_pct']}%, costs included {r['costs_included']}, slippage {r['slippage_bps']} bps"),
}
_TABLE = {"goals": "goals", "tasks": "work_tasks", "kpis": "kpis", "blockers": "blockers", "decisions": "decisions", "knowledge": "knowledge",
          "research": "research", "strategies": "trading_strategies", "runs": "trading_runs"}


def select_context(conn, slug: str, task_type: str, max_chars: int) -> dict:
    """Rows for the task type's context kinds, from ONE business. Each item carries a source id the model may cite."""
    biz = founder.get_business(conn, slug)  # NotFound for an unknown slug
    items, used = [], 0
    for kind in cfg.TASKS[task_type]["context"]:
        sql, fmt = _CONTEXT[kind]
        for r in conn.execute(sql, (biz["id"], cfg.MAX_CONTEXT_ROWS)).fetchall():
            line = f"[{_TABLE[kind]}:{r['id']}] {fmt(r)}"
            if used + len(line) > max_chars:
                break
            items.append({"source": f"{_TABLE[kind]}:{r['id']}", "text": line})
            used += len(line)
    return {"business": {"slug": biz["slug"], "name": biz["name"], "stage": biz["stage"], "description": _t(biz["description"], 400)}, "items": items}


def build_prompt(ctx: dict, request: str) -> str:
    b = ctx["business"]
    data = "\n".join(i["text"] for i in ctx["items"]) or "(no records selected)"
    return (f"BUSINESS: {b['name']} ({b['slug']}), stage {b['stage']}. {b['description']}\n"
            f"<data>\n{data}\n</data>\n<untrusted>\nTASK: {_t(request, cfg.MAX_INPUT_CHARS)}\n</untrusted>")


# --- structured output -----------------------------------------------------------------------------------------------

def parse_reply(text: str, sources: set[str]) -> dict:
    """Strict envelope. Raises ValueError on anything unexpected (caller discards the output)."""
    s = text.strip()
    m = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", s, re.S)
    data = json.loads(m.group(1) if m else s)
    if not isinstance(data, dict) or set(data) - {"answer", "claims", "next_steps", "needs_approval", "fields"} or not isinstance(data.get("answer"), str):
        raise ValueError("unexpected shape")
    claims = data.get("claims", [])
    steps = data.get("next_steps", [])
    fields = data.get("fields", {})
    if not isinstance(claims, list) or not isinstance(steps, list) or not isinstance(fields, dict):
        raise ValueError("bad types")
    out_claims = []
    for c in claims[:10]:
        if not isinstance(c, dict) or set(c) - {"text", "label", "source"} or not isinstance(c.get("text"), str) or c.get("label") not in LABELS:
            raise ValueError("bad claim")
        src = c.get("source")
        if src is not None and not isinstance(src, str):
            raise ValueError("bad claim")
        label = c["label"]
        if label == "verified" and src not in sources:
            label, src = "unknown", None  # a fact must trace to supplied data, else it is not presented as verified
        out_claims.append({"text": _t(c["text"]), "label": label, "source": src if src in sources else None})
    if not all(isinstance(x, str) for x in steps) or not all(isinstance(k, str) and isinstance(v, str) for k, v in fields.items()):
        raise ValueError("bad types")
    if not isinstance(data.get("needs_approval", False), bool):
        raise ValueError("bad types")
    answer = data["answer"].strip()[:3000]
    warnings = ["Contains guarantee/risk-free language: treat as unreliable. No outcome is guaranteed."] if GUARANTEE.search(answer + " " + " ".join(c["text"] for c in out_claims)) else []
    return {"answer": answer, "claims": out_claims, "next_steps": [_t(x, 200) for x in steps[:5]],
            "needs_approval": bool(data.get("needs_approval", False)),
            "fields": {_t(k, 40): _t(v, 200) for k, v in list(fields.items())[:20]}, "warnings": warnings}


# --- model client (lazy; NOT exercised against the live API in this repo's tests) -----------------------------------

class AnthropicClient:
    """Thin wrapper over the Anthropic SDK. ANTHROPIC_API_KEY comes from the environment."""

    def complete(self, model: str, system: str, user: str, max_tokens: int):
        import anthropic
        r = anthropic.Anthropic().messages.create(model=model, max_tokens=max_tokens, system=system, messages=[{"role": "user", "content": user}])
        return "".join(b.text for b in r.content if getattr(b, "type", "") == "text"), r.usage.input_tokens, r.usage.output_tokens


# --- the orchestrator ------------------------------------------------------------------------------------------------

def _log(conn, biz_id, route, model, tin, tout, cost, ms, outcome, llm_id):
    conn.execute("INSERT INTO ai_usage(id,business_id,provider,model,purpose,input_tokens,output_tokens,cost_usd,created_at,routing_level,task_type,latency_ms,outcome,llm_usage_id) "
                 "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                 (f"use_{uuid.uuid4().hex[:12]}", biz_id, "anthropic", model, route["task_type"], tin, tout, cost, now(), route["level"], route["task_type"], ms, outcome, llm_id))


def run(conn, client, slug: str, request: str, actor: str, task_type: str | None = None, min_level: str | None = None) -> dict:
    """Route and (if a model is warranted and allowed) execute one request for one business. Never raises for budget/disabled/bad output."""
    if not isinstance(request, str) or not request.strip():
        raise AiError("request is required")
    if len(request) > cfg.MAX_INPUT_CHARS:
        raise AiError("request too long")
    biz = founder.get_business(conn, slug)
    route = classify(request, task_type, min_level)
    base = {"business": slug, "route": route, "model_called": False}
    if route["level"] == cfg.NO_AI:
        return {**base, "status": "no_ai", "message": "This is a deterministic task: use the dashboard/workspace figures or code, not a model."}
    level = route["level"]
    if killswitch.is_paused(conn):
        return {**base, "status": "paused", "message": "The kill switch is on: model calls are paused."}
    if not budget.llm_enabled(level):
        return {**base, "status": "disabled", "message": "AI is off: set ANTHROPIC_API_KEY, LLM_MONTHLY_BUDGET_USD and the LLM_PRICE_* variables."}
    max_prompt, max_out = cfg.limits(level)
    ctx_chars = max(0, max_prompt * cfg.CHARS_PER_TOKEN - len(SYSTEM) - len(request) - 600)
    ctx = select_context(conn, slug, route["task_type"], ctx_chars)
    prompt = build_prompt(ctx, request)
    max_in = (len(SYSTEM) + len(prompt)) // cfg.CHARS_PER_TOKEN + 1
    model = route["model"]
    try:
        rid = budget.reserve(conn, AGENT, model, route["task_type"], max_in, max_out, level)
    except budget.BudgetExceeded as e:
        return {**base, "status": "budget_exceeded", "message": str(e)}
    except budget.LlmDisabled:
        return {**base, "status": "disabled", "message": "LLM budget/prices not configured."}
    t0 = time.monotonic()
    try:
        text, tin, tout = client.complete(model, SYSTEM, prompt, max_out)
    except Exception:
        held = budget.fail(conn, rid)  # outcome unknown: the worst-case hold stays counted
        _log(conn, biz["id"], route, model, 0, 0, held, int((time.monotonic() - t0) * 1000), "error", rid)
        audit(conn, actor, "ai.run.error", slug, route["task_type"])
        return {**base, "status": "error", "model_called": True, "message": "The model call failed; its worst-case cost stays counted against the budget."}
    ms = int((time.monotonic() - t0) * 1000)
    cost = budget.settle(conn, rid, int(tin), int(tout), level)
    try:
        out = parse_reply(text, {i["source"] for i in ctx["items"]})
        outcome = "ok"
    except (ValueError, KeyError, TypeError):
        out, outcome = None, "bad_output"
    _log(conn, biz["id"], route, model, int(tin), int(tout), cost, ms, outcome, rid)
    audit(conn, actor, f"ai.run.{outcome}", slug, f"{route['task_type']}/{level}")
    usage = {"input_tokens": int(tin), "output_tokens": int(tout), "cost_usd": str(cost), "latency_ms": ms, "model": model}
    if out is None:
        return {**base, "status": "bad_output", "model_called": True, "usage": usage, "message": "The reply was not the expected structure and was discarded."}
    out["needs_approval"] = out["needs_approval"] or route["stakes"]
    return {**base, "status": "ok", "model_called": True, "usage": usage, "output": out, "context_sources": [i["source"] for i in ctx["items"]],
            "advisory": "Advisory only. Nothing was executed. 'assumed' and 'unknown' claims are not facts."}


def status(conn) -> dict:
    """Routing table and whether AI is currently enabled, per level. Reads env/config only."""
    levels = {lv: {"model": cfg.model_for(lv), "max_prompt_tokens": cfg.limits(lv)[0], "max_output_tokens": cfg.limits(lv)[1],
                   "enabled": budget.llm_enabled(lv)} for lv in cfg.LEVELS}
    return {"levels": levels, "tasks": {k: {"level": v["level"], "about": v["about"], "stakes": v["stakes"]} for k, v in cfg.TASKS.items()},
            "monthly_cap_usd": float(budget.monthly_cap()) or None, "spent_this_month_usd": float(budget.spent_this_month(conn)),
            "paused": killswitch.is_paused(conn), "prompt_version": cfg.PROMPT_VERSION}
