"""Owner-supplied screenshots and pasted text -> prospect candidates for REVIEW (never created, never sent).

* Nothing is stored: the image is passed to the model and discarded; only what the owner confirms becomes a lead,
  through the normal add-lead path.
* Everything extracted is untrusted data: delimited for the model, a fixed JSON schema, unknown keys and bad values
  dropped, injection-looking text flagged for the owner. Output can never change a stage or trigger a send.
* Pasted text works without AI (deterministic: emails, phone numbers, @handles). Images need ANTHROPIC_API_KEY and
  the monthly cap in core/budget.py; without them the API says so instead of guessing.
"""

import base64
import binascii
import json
import re
from pathlib import Path

from agents.scout import sanitize
from core import budget

PROMPT_VERSION = "lead-extract-v1"
SYSTEM = (Path(__file__).resolve().parents[1] / "prompts" / "challenge" / f"{PROMPT_VERSION}.md").read_text().strip()
MAX_IMAGE_BYTES = 3_000_000
MAX_TEXT = 8000
MAX_CANDIDATES = 10
MAX_OUT = 900
FIELDS = {"name": 120, "business": 160, "phone": 40, "email": 160, "instagram": 60, "segment": 80, "location": 80, "notes": 200}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
PHONE_RE = re.compile(r"(?<![\w.])(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\d)")
HANDLE_RE = re.compile(r"(?<![\w@])@([A-Za-z0-9._]{3,30})\b")
MAGIC = {"image/png": b"\x89PNG\r\n\x1a\n", "image/jpeg": b"\xff\xd8\xff", "image/webp": b"RIFF"}


class IngestError(ValueError):
    pass


def status() -> dict:
    return {"images": budget.llm_enabled(), "text": True}


def _candidate(d: dict) -> dict | None:
    out = {k: sanitize.clean(d.get(k, ""), n) if isinstance(d.get(k, ""), str) else "" for k, n in FIELDS.items()}
    if out["email"] and not (EMAIL_RE.fullmatch(out["email"])):
        out["email"] = ""
    out["instagram"] = out["instagram"].lstrip("@")
    if not any(out[k] for k in ("name", "business", "phone", "email", "instagram")):
        return None
    out["flags"] = sanitize.injection_findings(*out.values())
    return out


def parse_reply(text: str) -> list[dict]:
    data = json.loads(text)
    if not isinstance(data, dict) or set(data) - {"prospects"} or not isinstance(data.get("prospects"), list):
        raise ValueError("unexpected shape")
    rows = [c for c in (_candidate(p) for p in data["prospects"][:MAX_CANDIDATES] if isinstance(p, dict)) if c]
    return rows


def from_text_rules(text: str) -> list[dict]:
    """No-AI fallback: one candidate per email / phone / handle found in pasted text, first match per kind kept together
    only when the text holds a single contact; otherwise one row each so the owner can merge by hand."""
    text = sanitize.clean(text, MAX_TEXT)
    emails = list(dict.fromkeys(EMAIL_RE.findall(text)))
    phones = list(dict.fromkeys(m.strip() for m in PHONE_RE.findall(text)))
    handles = list(dict.fromkeys(HANDLE_RE.findall(text)))
    if len(emails) + len(phones) + len(handles) == 0:
        return []
    if max(len(emails), len(phones), len(handles)) <= 1:
        return [c for c in [_candidate({"email": emails[0] if emails else "", "phone": phones[0] if phones else "",
                                         "instagram": handles[0] if handles else "", "notes": text[:200]})] if c]
    rows = [{"email": e} for e in emails] + [{"phone": p} for p in phones] + [{"instagram": h} for h in handles]
    return [c for c in (_candidate(r) for r in rows[:MAX_CANDIDATES]) if c]


def _check_image(image_b64: str, mime: str) -> None:
    if mime not in MAGIC:
        raise IngestError("image must be PNG, JPEG or WebP")
    try:
        raw = base64.b64decode(image_b64, validate=True)
    except (binascii.Error, ValueError):
        raise IngestError("image is not valid base64") from None
    if not raw or len(raw) > MAX_IMAGE_BYTES:
        raise IngestError("image is empty or over 3 MB: crop or downscale it")
    if not raw.startswith(MAGIC[mime]):
        raise IngestError("image content does not match its type")


def extract(conn, client, text: str = "", image_b64: str = "", mime: str = "") -> dict:
    """Returns {"candidates": [...], "method": "ai"|"rules", "notes": str}. Raises IngestError for bad input or when an
    image is supplied but AI extraction cannot run."""
    text = text if isinstance(text, str) else ""
    if not text.strip() and not image_b64:
        raise IngestError("paste some text or add a screenshot")
    if not image_b64:
        if budget.llm_enabled() and client is not None and len(text.strip()) > 40:
            r = _ask(conn, client, text, "", "")
            if r is not None:
                return {"candidates": r, "method": "ai", "notes": ""}
        rows = from_text_rules(text)
        return {"candidates": rows, "method": "rules",
                "notes": "" if rows else "No email, phone number or @handle found in that text."}
    _check_image(image_b64, mime)
    if not budget.llm_enabled() or client is None:
        raise IngestError("Reading screenshots needs ANTHROPIC_API_KEY plus the LLM budget and price settings. "
                          "Paste the text instead, or add the lead by hand.")
    r = _ask(conn, client, text, image_b64, mime)
    if r is None:
        raise IngestError("Could not read that screenshot (over budget, API error or unusable answer). Add the lead by hand.")
    return {"candidates": r, "method": "ai", "notes": "" if r else "Nothing usable was visible in that image."}


def _ask(conn, client, text: str, image_b64: str, mime: str):
    model = getattr(client, "model", "unknown")
    try:
        rid = budget.reserve(conn, "scout", model, "lead_extract", 2500 if image_b64 else 2000, MAX_OUT)
    except (budget.BudgetExceeded, budget.LlmDisabled):
        return None
    user = "<untrusted>\n" + sanitize.clean(text, MAX_TEXT) + "\n</untrusted>"
    try:
        reply, tin, tout = client.complete(SYSTEM, user, MAX_OUT, image=(mime, image_b64) if image_b64 else None)
    except Exception:
        budget.fail(conn, rid)
        return None
    budget.settle(conn, rid, int(tin), int(tout))
    try:
        return parse_reply(reply)
    except (ValueError, KeyError, TypeError):
        return None
