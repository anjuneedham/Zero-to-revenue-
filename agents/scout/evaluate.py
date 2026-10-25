"""Deterministic scoring of one opportunity (spec sections 6-8). No network, no LLM."""

import hashlib
import os
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlsplit

from agents.scout import sanitize, scam
from core.policy.policy import OpportunityStatus, classify_opportunity, opportunity_score

TRUSTED_DOMAINS = {"github.com", "gitcoin.co", "immunefi.com", "code4rena.com", "sherlock.xyz",
                   "hackerone.com", "bugcrowd.com", "superteam.fun", "dework.xyz", "layer3.xyz"}
AUTOMATABLE = ("code", "development", "research", "writing", "data", "documentation", "bug", "test", "script", "bounty")
EASY_WORDS = ("fix", "small", "simple", "quick", "minor", "one page", "single", "bug", "typo", "config", "update", "convert")
HARD_WORDS = ("full", "platform", "build from scratch", "end to end", "end-to-end", "architecture", "migrate", "integration", "complex")


def min_payment_usd() -> float:
    try:
        v = Decimal(os.environ.get("MIN_EXPECTED_PAYMENT_USD", "500").strip() or "500")
    except InvalidOperation:
        v = Decimal(500)
    return float(v) if v >= 0 else 500.0


@dataclass
class RawItem:
    title: str
    source: str
    source_url: str
    body: str = ""
    organization: str = ""
    category: str = "bounty"
    deadline: str | None = None            # ISO 8601
    required_skills: list[str] = field(default_factory=list)
    required_capital: float | None = None  # None = unknown (never assumed zero)
    expected_payment: float | None = None  # CLAIMED, unverified
    payment_asset: str = ""
    payment_method: str = ""
    effort_estimate: str = ""
    labels: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)   # shown to the owner under "missing information"
    sponsor_verified: bool | None = None               # None = unknown
    human_only: bool = False                           # listing says AI-produced work is not allowed


@dataclass
class Evaluation:
    id: str
    row: dict
    score: int
    risk: int
    status: OpportunityStatus
    flags: list[str]


def opportunity_id(source_url: str) -> str:
    return "opp_" + hashlib.sha256(source_url.strip().lower().encode()).hexdigest()[:12]


def owner_skills() -> set[str]:
    return {s.strip().lower() for s in os.environ.get("OWNER_SKILLS", "").split(",") if s.strip()}


def _parse_deadline(deadline):
    if not deadline:
        return None
    try:
        d = datetime.fromisoformat(str(deadline).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def evaluate(item: RawItem, now: datetime | None = None, skills: set[str] | None = None) -> Evaluation:
    now = now or datetime.now(timezone.utc)
    skills = owner_skills() if skills is None else skills
    title = sanitize.clean(item.title, 300)
    body = sanitize.clean(item.body)
    org = sanitize.clean(item.organization, 200)
    url = sanitize.clean(item.source_url, 500)
    text = f"{title}\n{body}\n{' '.join(item.labels)}"

    injection = sanitize.injection_findings(title, body, *item.labels)
    has_terms = bool(item.expected_payment and item.payment_asset)
    risk, flags = scam.assess(text, organization=org, expected_payment=item.expected_payment,
                              has_payment_terms=has_terms, injection=injection,
                              required_capital=item.required_capital, title=title,
                              sponsor_verified=item.sponsor_verified)

    missing = []
    if item.required_capital is None:
        missing.append("required_capital unknown (not assumed zero)")
    if not item.expected_payment:
        missing.append("payment amount not stated")
    if not item.payment_asset:
        missing.append("payment asset not stated")
    if not item.payment_method:
        missing.append("payment method not stated")
    if not item.deadline:
        missing.append("deadline not stated")
    if not skills:
        missing.append("OWNER_SKILLS not configured; skill fit is neutral")
    missing.extend(sanitize.clean(c, 200) for c in item.caveats)
    if item.human_only:
        pass

    host = (urlsplit(url).hostname or "").removeprefix("www.")
    trusted = urlsplit(url).scheme == "https" and any(host == d or host.endswith("." + d) for d in TRUSTED_DOMAINS)
    deadline = _parse_deadline(item.deadline)
    expired = deadline is not None and deadline < now

    legit = 0.25 + (0.25 if trusted else 0) + (0.2 if org else 0) + (0.15 if has_terms else 0) + (0.15 if deadline else 0)
    legit = max(0.0, min(1.0, legit - 0.8 * risk / 100))
    overlap = (len(skills & {s.lower() for s in item.required_skills}) / len(item.required_skills)
               if skills and item.required_skills else 0.5)
    factors = {
        "legitimacy": legit,
        # unknown capital is NOT zero capital: partial credit only; known capital > 0 earns nothing
        "zero_capital": 1.0 if item.required_capital == 0 else (0.5 if item.required_capital is None else 0.0),
        "payment_clarity": (0.5 if item.expected_payment else 0) + (0.25 if item.payment_asset else 0) + (0.25 if item.payment_method else 0),
        "skill_fit": overlap,
        "repeatability": 0.7 if trusted else 0.4,
        "automation": 0.7 if any(k in text.lower() for k in AUTOMATABLE) else 0.4,
        "deadline": 0.0 if expired else (1.0 if deadline else 0.5),
    }
    score = opportunity_score(factors)
    if expired:
        flags.append("deadline_passed")
    status = OpportunityStatus.REVIEW_REQUIRED if expired else classify_opportunity(score, risk)
    # Stricter than the spec's thresholds, on purpose: an opportunity cannot be auto-queued for the
    # Operator unless payment amount and asset are stated AND there is a payment method or a deadline.
    undocumented = not (item.expected_payment and item.payment_asset and (item.payment_method or item.deadline))
    if item.human_only:
        flags.append("human_only_listing")
        status = OpportunityStatus.REVIEW_REQUIRED
    if status is OpportunityStatus.QUALIFIED and undocumented:
        status = OpportunityStatus.REVIEW_REQUIRED
        flags.append("insufficient_terms")

    min_pay = min_payment_usd()
    low_text = text.lower()
    looks_hard = any(w in low_text for w in HARD_WORDS) or len(item.required_skills) > 2
    bar = min_pay * 2 if looks_hard else min_pay  # harder work needs a bigger fee, not a pass on the floor
    below_bar = item.expected_payment is not None and item.expected_payment < bar
    if status is OpportunityStatus.QUALIFIED and below_bar:
        status = OpportunityStatus.REVIEW_REQUIRED
        flags.append(f"under_${bar:.0f}_bar" + ("_harder_work_needs_more" if looks_hard else ""))

    known = [title, org, url, body, item.deadline, item.expected_payment, item.payment_asset, item.payment_method,
             item.required_skills, item.required_capital is not None]
    confidence = max(0, round(100 * sum(1 for k in known if k) / len(known)) - (25 if injection else 0))

    if status is OpportunityStatus.QUALIFIED:
        action = "Research and draft; submission needs owner approval"
    elif item.human_only:
        action = "Listing is human-only: do the work yourself; AI-produced work may break the rules"
    elif risk > 35:
        action = "Do not engage until risk flags are reviewed by the owner"
    elif "insufficient_terms" in flags:
        action = "Owner review: payment terms are not documented well enough to queue automatically"
    elif any(f.startswith("under_$") for f in flags):
        action = (f"Below the ${bar:.0f} bar for work this complex; needs a bigger fee" if looks_hard
                  else f"Below the ${min_pay:.0f} floor; only worth it if the scope is genuinely small")
    else:
        action = "Owner review: score below qualification threshold"
    oid = opportunity_id(url)
    row = {
        "id": oid, "title": title, "category": sanitize.clean(item.category, 60), "source": sanitize.clean(item.source, 80),
        "source_url": url, "organization": org, "deadline": item.deadline,
        "eligibility": None, "required_skills": ",".join(item.required_skills)[:300],
        "required_capital": item.required_capital, "expected_payment": item.expected_payment,
        "payment_method": item.payment_method or None, "payment_asset": item.payment_asset or None,
        "effort_estimate": item.effort_estimate or None, "opportunity_score": score, "risk_score": risk,
        "confidence": confidence, "scam_indicators": "; ".join(flags), "missing_information": "; ".join(missing),
        "recommended_action": action, "approval_required": 1,
        "evidence": f"{url} | claimed payment (unverified): {item.expected_payment} {item.payment_asset}".strip(),
        "status": status.value,
    }
    return Evaluation(oid, row, score, risk, status, flags)
