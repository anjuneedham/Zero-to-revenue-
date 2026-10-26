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
    # Spam/farming patterns seen in live GitHub "bounty" issues (gift cards, tokens, repeated titles).
    "non_cash_reward": (35, re.compile(r"gift\s*card|voucher|\bsteam\b.{0,20}(card|key|wallet)|v-?bucks|robux|itunes|coupon", re.I | re.S)),
    "token_exchange_scheme": (40, re.compile(r"exchange\s+[\d,\.]+\s*[kKmMbB]?\s+\S+(\s+\(\$?\w+\))?\s+for\b|(?-i:\$w[A-Z0-9]{2,}\b)|airdrop|free\s+tokens?|claim\s+your\s+(reward|tokens?)", re.I)),
    "token_promotion": (25, re.compile(r"fair\s+launch|trading\s+competition|\bshill|(write|create|post)\b.{0,25}(thread|tweet|post).{0,40}(?-i:\$[A-Za-z]{3,10}\b)", re.I | re.S)),
    # Not a one-off paid job at all: an ongoing commission-only/equity-only sales or "partner" role
    # with no guaranteed pay for the work itself - ask-your-skills jobs boards are full of these
    # disguised as freelance projects. High enough to force REVIEW_REQUIRED and block auto-send.
    "commission_only_role": (40, re.compile(r"commission[\s-]only|100\s*%\s*commission|uncapped\s+commission|"
                              r"no\s+base\s+(pay|salary)|equity\s+only|unpaid\s+(trial|probation)|"
                              r"(percentage|%)\s+of\s+(sales|revenue)\s+only|revenue\s+share\s+only", re.I)),
}
UNVERIFIED_SPONSOR_RISK = 15
INJECTION_RISK = 40
DUPLICATE_TITLE_RISK = 30
EMOJI_RISK = 10
UNKNOWN_ORG_RISK = 10
UNCLEAR_PAYMENT_RISK = 10
UNREALISTIC_PAYMENT_USD = 10_000
UNREALISTIC_RISK = 20


def duplicated_title(title: str) -> bool:
    """True when a run of 3+ words appears twice, a typical farmed-issue signature."""
    words = re.sub(r"\W+", " ", (title or "").lower()).split()
    for n in range(3, len(words) // 2 + 1):
        for i in range(len(words) - 2 * n + 1):
            chunk = words[i:i + n]
            if any(words[j:j + n] == chunk for j in range(i + n, len(words) - n + 1)):
                return True
    return False


def emoji_count(title: str) -> int:
    return sum(1 for ch in title or "" if 0x1F300 <= ord(ch) <= 0x1FAFF or 0x2600 <= ord(ch) <= 0x27BF)


def assess(text: str, *, organization: str, expected_payment, has_payment_terms: bool,
           injection: list[str], required_capital, title: str = "",
           sponsor_verified=None) -> tuple[int, list[str]]:
    flags, risk = [], 0
    if sponsor_verified is False:
        flags.append("unverified_sponsor")
        risk += UNVERIFIED_SPONSOR_RISK
    if duplicated_title(title):
        flags.append("duplicated_title_spam")
        risk += DUPLICATE_TITLE_RISK
    if emoji_count(title) >= 2:
        flags.append("emoji_heavy_title")
        risk += EMOJI_RISK
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
