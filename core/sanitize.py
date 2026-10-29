"""Everything read from outside (pasted text, screenshots, imports) is UNTRUSTED DATA."""

import re

MAX_FIELD = 4000
_HIDDEN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f​-‏‪-‮⁠-⁤﻿]")

INJECTION_PATTERNS = {
    "ignore_instructions": re.compile(r"(ignore|disregard|forget|override)\s+(all\s+|any\s+|your\s+|the\s+)?(previous|prior|above|earlier|system|these)?\s*(instructions?|prompts?|rules?|polic(y|ies)|guidelines?)", re.I),
    "role_override": re.compile(r"\byou\s+are\s+now\b|\bact\s+as\s+(an?\s+)?(admin|system|developer|root)\b|\bnew\s+(system\s+)?instructions?\b", re.I),
    "prompt_probe": re.compile(r"(reveal|show|print|repeat)\s+(your\s+|the\s+)?(system\s+)?(prompt|instructions)", re.I),
    "secret_exfiltration": re.compile(r"(send|share|paste|provide|reveal|enter|submit)\b.{0,50}(private\s+key|seed\s+phrase|recovery\s+phrase|mnemonic|password|2fa|one[- ]time\s+code)", re.I | re.S),
    "concealment": re.compile(r"do\s+not\s+(tell|inform|alert|notify)\s+(the\s+)?(user|owner|human)", re.I),
    "fake_markup": re.compile(r"<\s*/?\s*(system|assistant|instructions?|tool_call|function_call)\b", re.I),
    "agent_addressing": re.compile(r"\b(as\s+an?\s+ai\s+(agent|assistant)|dear\s+(ai|agent|assistant|llm))\b", re.I),
}


def clean(value, limit: int = MAX_FIELD) -> str:
    """Strip control/invisible/bidi characters, normalise whitespace, truncate."""
    if value is None:
        return ""
    text = _HIDDEN.sub("", str(value))
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:limit]


def injection_findings(*texts: str) -> list[str]:
    found = []
    for name, pat in INJECTION_PATTERNS.items():
        if any(pat.search(t or "") for t in texts):
            found.append(name)
    return found
