"""Core safety policy for the Zero-to-Revenue Agent System.

This module is the single source of truth for what agents may do. It is
deliberately code, not configuration: financial and signing capabilities are
hard-disabled and cannot be switched on through environment variables or
database settings. Agents (and the learning loop) must not modify this file.
"""

from dataclasses import dataclass
from enum import Enum


class Agent(str, Enum):
    SCOUT = "scout"
    OPERATOR = "operator"
    TREASURY = "treasury"


class SystemMode(str, Enum):
    """Release status labels the product must surface for each feature."""

    DEMO = "DEMO"
    MOCK = "MOCK"
    READ_ONLY = "READ_ONLY"
    HUMAN_APPROVED = "HUMAN_APPROVED"
    PRODUCTION = "PRODUCTION"


class OpportunityStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    QUALIFIED = "QUALIFIED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    APPROVED = "APPROVED"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    AWAITING_PAYMENT = "AWAITING_PAYMENT"
    PAYMENT_UNVERIFIED = "PAYMENT_UNVERIFIED"
    PAYMENT_VERIFIED = "PAYMENT_VERIFIED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class TaskStatus(str, Enum):
    NEW = "NEW"
    QUEUED = "QUEUED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_FOR_USER = "WAITING_FOR_USER"
    WAITING_FOR_EXTERNAL = "WAITING_FOR_EXTERNAL"
    SUBMITTED = "SUBMITTED"
    AWAITING_PAYMENT = "AWAITING_PAYMENT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SECURITY_HOLD = "SECURITY_HOLD"


class Action(str, Enum):
    # Internal / sandboxed work
    RESEARCH = "research"
    READ_EXTERNAL = "read_external"
    WRITE_DATABASE = "write_database"
    CREATE_DELIVERABLE = "create_deliverable"
    RUN_TESTS = "run_tests"
    NOTIFY_OWNER = "notify_owner"
    READ_WALLET = "read_wallet"
    RECONCILE = "reconcile"
    # External writes: allowed only with owner approval
    SUBMIT_WORK = "submit_work"
    SEND_OUTREACH = "send_outreach"
    SUBMIT_APPLICATION = "submit_application"
    ENABLE_PAID_SERVICE = "enable_paid_service"
    # Permanently forbidden in this release
    SEND_FUNDS = "send_funds"
    SIGN_TRANSACTION = "sign_transaction"
    SWAP = "swap"
    BRIDGE = "bridge"
    STAKE = "stake"
    TRADE = "trade"
    APPROVE_CONTRACT = "approve_contract"
    ACCEPT_BINDING_CONTRACT = "accept_binding_contract"
    REQUEST_SECRET = "request_secret"
    BYPASS_ACCESS_CONTROL = "bypass_access_control"


FORBIDDEN_ACTIONS = frozenset({
    Action.SEND_FUNDS,
    Action.SIGN_TRANSACTION,
    Action.SWAP,
    Action.BRIDGE,
    Action.STAKE,
    Action.TRADE,
    Action.APPROVE_CONTRACT,
    Action.ACCEPT_BINDING_CONTRACT,
    Action.REQUEST_SECRET,
    Action.BYPASS_ACCESS_CONTROL,
})

APPROVAL_REQUIRED_ACTIONS = frozenset({
    Action.SUBMIT_WORK,
    Action.SEND_OUTREACH,
    Action.SUBMIT_APPLICATION,
    Action.ENABLE_PAID_SERVICE,
})

# Least-privilege grants per agent. Anything not listed is denied.
AGENT_PERMISSIONS = {
    Agent.SCOUT: frozenset({
        Action.RESEARCH, Action.READ_EXTERNAL, Action.WRITE_DATABASE,
        Action.NOTIFY_OWNER,
    }),
    Agent.OPERATOR: frozenset({
        Action.RESEARCH, Action.READ_EXTERNAL, Action.WRITE_DATABASE,
        Action.CREATE_DELIVERABLE, Action.RUN_TESTS, Action.NOTIFY_OWNER,
        Action.SUBMIT_WORK, Action.SEND_OUTREACH, Action.SUBMIT_APPLICATION,
    }),
    Agent.TREASURY: frozenset({
        Action.READ_WALLET, Action.RECONCILE, Action.WRITE_DATABASE,
        Action.NOTIFY_OWNER,
    }),
}

# Hard-coded financial safety flags (spec sections 2, 15, 33).
STARTING_CAPITAL = 0
WALLET_MODE = "READ_ONLY"
TRADING_ENABLED = False
AUTO_SPENDING_ENABLED = False
TRANSACTION_SIGNING_ENABLED = False
CONTRACT_INTERACTION_ENABLED = False
BRIDGE_ENABLED = False
SWAPS_ENABLED = False
STAKING_ENABLED = False


@dataclass(frozen=True)
class Decision:
    allowed: bool
    requires_approval: bool
    reason: str


def authorize(agent: Agent, action: Action, *, paused: bool,
              owner_approved: bool = False) -> Decision:
    """Decide whether `agent` may perform `action` right now.

    Order matters: forbidden actions are refused even when the owner has
    approved them, and the kill switch blocks everything except notifying
    the owner.
    """
    if action in FORBIDDEN_ACTIONS:
        return Decision(False, False, f"{action.value} is forbidden in this release")
    if paused and action is not Action.NOTIFY_OWNER:
        return Decision(False, False, "system is paused by kill switch")
    if action not in AGENT_PERMISSIONS[agent]:
        return Decision(False, False, f"{agent.value} is not permitted to {action.value}")
    if action in APPROVAL_REQUIRED_ACTIONS and not owner_approved:
        return Decision(False, True, f"{action.value} requires owner approval")
    return Decision(True, False, "allowed")


# --- Scout scoring (spec sections 6 and 7) -----------------------------------

SCORE_WEIGHTS = {
    "legitimacy": 25,
    "zero_capital": 20,
    "payment_clarity": 15,
    "skill_fit": 15,
    "repeatability": 10,
    "automation": 10,
    "deadline": 5,
}
assert sum(SCORE_WEIGHTS.values()) == 100

QUALIFY_MIN_SCORE = 65
QUALIFY_MAX_RISK = 35


def opportunity_score(factors: dict) -> int:
    """Weighted score from per-factor ratings in [0.0, 1.0]."""
    missing = set(SCORE_WEIGHTS) - set(factors)
    if missing:
        raise ValueError(f"missing score factors: {sorted(missing)}")
    total = 0.0
    for name, weight in SCORE_WEIGHTS.items():
        rating = float(factors[name])
        if not 0.0 <= rating <= 1.0:
            raise ValueError(f"{name} rating must be within [0, 1]")
        total += weight * rating
    return round(total)


def classify_opportunity(score: int, risk: int) -> OpportunityStatus:
    if score >= QUALIFY_MIN_SCORE and risk <= QUALIFY_MAX_RISK:
        return OpportunityStatus.QUALIFIED
    return OpportunityStatus.REVIEW_REQUIRED


def is_zero_capital(required_capital: float) -> bool:
    return required_capital <= 0


# --- Revenue verification (spec sections 16 and 18) --------------------------

NON_REVENUE_TYPES = frozenset({
    "self_transfer", "loan", "unrealized_gain", "promised_payment",
    "pending_bounty", "estimated_earnings",
})

REQUIRED_PAYMENT_EVIDENCE = (
    "occurred", "chain_confirmed", "final", "transaction_hash",
    "asset_amount_verified", "source_associated", "ledger_recorded",
)


def counts_as_verified_revenue(entry_type: str, evidence: dict) -> bool:
    """Only a receipt with every verification check satisfied counts."""
    if entry_type in NON_REVENUE_TYPES or entry_type != "receipt":
        return False
    return all(evidence.get(check) is True for check in REQUIRED_PAYMENT_EVIDENCE)
