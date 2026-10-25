"""Heuristic scam / risk indicators (spec section 6). Deterministic; the LLM can only add to these."""

import re

INDICATORS = {
    "upfront_fee": (45, re.compile(r"(registration|entry|application|processing|activation|verification|unlock)\s+fee|pay\s.{0,25}\bto\s+(apply|join|participate|unlock|claim|withdraw)|deposit\s+(is\s+)?required|send\s.{0,25}\b(eth|bnb|usdt|usdc|btc|sol)\b", re.I | re.S)),
    "wallet_or_contract_interaction": (35, re.compile(r"connect\s+(your\s+)?wallet|approve\s+(the\s+)?(contract|token|spending)|sign\s+(this|the)\s+(message|transaction)|setApprovalForAll|\bpermit\b.{0,20}signature", re.I | re.S)),
    "asks_for_secrets": (60, re.compile(r"private\s+key|seed\s+phrase|recovery\s+phrase|mnemonic|keystore\s+file", re.I)),
    "guaranteed_returns": (30, re.compile(r"guaranteed|risk[- ]free|100\s*%\s*(profit|return)|double\s+your|passive\s+income|get\s+rich", re.I)),
    "urgency_pressure": (15, re.compile(r"(act|claim|hurry|register)\s+(now|fast|immediately)|today\s+only|expires?\s+in\s+\d+\s+(minutes?|hours?)|limited\s+spots", re.I)),
    "personal_data_request": (30, re.compile(r"passport|\bssn\b|social\s+security|driver'?s?\s+licen[cs]e|bank\s+(login|password)|id\s+card\s+photo", re.I)),
    "shortened_link": (20, re.compile(r"\b(bit\.ly|tinyurl\.com|t\.co|goo\.gl|cutt\.ly|is\.gd|rb\.gy)/", re.I)),
    "excessive_permissions": (25, re.compile(r"(admin|write|full)\s+access\s+to\s+(your\s+)?(repo|repository|account|drive|email|wallet)|grant\s.{0,25}access\s+to\s+(your\s+)?(account|wallet|email)", re.I | re.S)),
}
INJECTION_RISK = 40
UNKNOWN_ORG_RISK = 10
UNCLEAR_PAYMENT_RISK = 10
UNREALISTIC_PAYMENT_USD = 10_000
UNREALISTIC_RISK = 20


def assess(text: str, *, organization: str, expected_payment, has_payment_terms: bool,
           injection: list[str], required_capital) -> tuple[int, list[str]]:
    flags, risk = [], 0
    for name, (weight, pat) in INDICATORS.items():
        if pat.search(text or ""):
            flags.append(name)
            risk += weight
    if injection:
        flags.append("prompt_injection_attempt:" + ",".join(injection))
        risk += INJECTION_RISK
    if required_capital is not None and required_capital > 0:
        flags.append("requires_capital")
        risk += 20
    if not organization:
        flags.append("unknown_organization")
        risk += UNKNOWN_ORG_RISK
    if not has_payment_terms:
        flags.append("unclear_payment_terms")
        risk += UNCLEAR_PAYMENT_RISK
    if expected_payment is not None and expected_payment >= UNREALISTIC_PAYMENT_USD:
        flags.append("unrealistic_payment")
        risk += UNREALISTIC_RISK
    return min(100, risk), flags
