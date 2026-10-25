"""Optional, budget-capped Claude help. Safe by construction (spec sections 32, 39):

* Untrusted text goes in as delimited DATA; the system prompt says so.
* The model can only return three soft ratings in [0,1], a short display note, and extra
  risk flags. It can never change legitimacy, capital, payment, status, or trigger any action.
* AI may only ADD caution: extra flags raise risk, they can never lower it.
* Output that is not exactly the expected JSON is discarded.
"""

import json
import os
from pathlib import Path

from agents.scout import sanitize
from agents.scout.evaluate import RawItem
from core import budget

PROMPT_VERSION = "scout-enrich-v1"
SYSTEM = (Path(__file__).resolve().parents[2] / "prompts" / "scout" / f"{PROMPT_VERSION}.md").read_text().strip()
MAX_IN, MAX_OUT = 1500, 200
MAX_EXTRA_FLAGS = 3
EXTRA_FLAG_RISK = 10


class ClaudeClient:
    """Thin wrapper over the Anthropic SDK (lazy import). Not exercised against the live API in tests."""

    def __init__(self, model: str | None = None):
        import anthropic
        self.model = model or os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
        self.client = anthropic.Anthropic()  # ANTHROPIC_API_KEY from the environment

    def complete(self, system: str, user: str, max_tokens: int):
        r = self.client.messages.create(model=self.model, max_tokens=max_tokens, system=system,
                                        messages=[{"role": "user", "content": user}])
        text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
        return text, r.usage.input_tokens, r.usage.output_tokens


def _rating(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError("bad rating")
    return max(0.0, min(1.0, float(v)))


def parse_reply(text: str) -> dict:
    data = json.loads(text)
    if not isinstance(data, dict) or set(data) - {"skill_fit", "automation", "repeatability", "risk_flags", "note"}:
        raise ValueError("unexpected keys")
    flags = data.get("risk_flags", [])
    if not isinstance(flags, list) or not all(isinstance(f, str) for f in flags):
        raise ValueError("bad flags")
    return {"skill_fit": _rating(data["skill_fit"]), "automation": _rating(data["automation"]),
            "repeatability": _rating(data["repeatability"]),
            "risk_flags": [sanitize.clean(f, 60) for f in flags[:MAX_EXTRA_FLAGS] if f.strip()],
            "note": sanitize.clean(data.get("note", ""), 200)}


def enrich(conn, client, item: RawItem, model: str = "") -> dict | None:
    """Returns a validated suggestion, or None (disabled / over budget / bad output)."""
    if not budget.llm_enabled():
        return None
    model = model or getattr(client, "model", "unknown")
    try:
        rid = budget.reserve(conn, "scout", model, "enrich", MAX_IN + 400, MAX_OUT)
    except (budget.BudgetExceeded, budget.LlmDisabled):
        return None
    body = f"<untrusted>\nTITLE: {sanitize.clean(item.title, 300)}\nORG: {sanitize.clean(item.organization, 100)}\n" \
           f"TEXT: {sanitize.clean(item.body, 3000)}\n</untrusted>"
    try:
        text, tin, tout = client.complete(SYSTEM, body, MAX_OUT)
    except Exception:
        budget.fail(conn, rid)  # unknown outcome: keep the reservation counted
        return None
    budget.settle(conn, rid, int(tin), int(tout))
    try:
        return parse_reply(text)
    except (ValueError, KeyError, TypeError):
        return None
