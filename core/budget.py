"""Hard monthly cap on LLM spend (spec section 39). Fails closed.

The LLM is DISABLED unless all of these are set: LLM_MONTHLY_BUDGET_USD (>0),
LLM_PRICE_IN_PER_MTOK and LLM_PRICE_OUT_PER_MTOK (USD per million tokens; take them from the
provider's pricing page, they are deliberately not hard-coded here).
Each call first RESERVES its worst-case cost under an advisory lock, so concurrent calls
cannot overshoot the cap; the reservation is trued-up to actual usage afterwards.
"""

import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from core.db import now

LOCK = 7_262_026


class BudgetExceeded(RuntimeError):
    pass


class LlmDisabled(RuntimeError):
    pass


def _dec(name: str) -> Decimal:
    try:
        v = Decimal(os.environ.get(name, "").strip() or "0")
    except InvalidOperation:
        return Decimal(0)
    return v if v > 0 else Decimal(0)


def monthly_cap() -> Decimal:
    return _dec("LLM_MONTHLY_BUDGET_USD")


def prices() -> tuple[Decimal, Decimal]:
    return _dec("LLM_PRICE_IN_PER_MTOK"), _dec("LLM_PRICE_OUT_PER_MTOK")


def llm_enabled() -> bool:
    pin, pout = prices()
    return monthly_cap() > 0 and pin > 0 and pout > 0 and bool(os.environ.get("ANTHROPIC_API_KEY"))


def _month_start() -> str:
    n = datetime.now(timezone.utc)
    return datetime(n.year, n.month, 1, tzinfo=timezone.utc).isoformat()


def spent_this_month(conn) -> Decimal:
    return Decimal(conn.execute("SELECT COALESCE(SUM(cost_usd),0) s FROM llm_usage WHERE at >= ?",
                                (_month_start(),)).fetchone()["s"])


def _cost(pin: Decimal, pout: Decimal, tin: int, tout: int) -> Decimal:
    return (pin * tin + pout * tout) / Decimal(1_000_000)


def reserve(conn, agent: str, model: str, purpose: str, max_in: int, max_out: int) -> int:
    """Reserve worst-case cost; returns the reservation id or raises."""
    pin, pout = prices()
    cap = monthly_cap()
    if cap <= 0 or pin <= 0 or pout <= 0:
        raise LlmDisabled("LLM budget/prices not configured")
    worst = _cost(pin, pout, max_in, max_out)
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(%s)" % LOCK)
        if spent_this_month(conn) + worst > cap:
            raise BudgetExceeded(f"monthly LLM budget ${cap} would be exceeded")
        return conn.execute(
            "INSERT INTO llm_usage(at,agent,model,purpose,input_tokens,output_tokens,cost_usd,status) "
            "VALUES (?,?,?,?,?,?,?, 'RESERVED') RETURNING id",
            (now(), agent, model, purpose, max_in, max_out, worst)).fetchone()["id"]


def settle(conn, reservation_id: int, in_tokens: int, out_tokens: int) -> None:
    pin, pout = prices()
    conn.execute("UPDATE llm_usage SET input_tokens=?, output_tokens=?, cost_usd=?, status='DONE' WHERE id=?",
                 (in_tokens, out_tokens, _cost(pin, pout, in_tokens, out_tokens), reservation_id))


def fail(conn, reservation_id: int) -> None:
    """Outcome unknown (call may have been billed): keep the worst-case reservation (fail safe)."""
    conn.execute("UPDATE llm_usage SET status='FAILED' WHERE id=?", (reservation_id,))
