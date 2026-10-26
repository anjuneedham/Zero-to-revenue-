"""Gmail API client for actually sending an outreach email, once the owner has approved it.
Scope is deliberately narrow: send only. No reading, searching, or deleting mail, and nothing here
ever runs without an explicit owner approval checked by the caller (core.policy.policy's
SEND_OUTREACH is in APPROVAL_REQUIRED_ACTIONS). Auth is a Google OAuth refresh token the owner
generates once (see docs/runbooks or ask the assistant) - the same mechanism Gmail's own API
quickstart uses, no password ever touches this system."""

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from email.mime.text import MIMEText

TIMEOUT = 15
MAX_BYTES = 500_000
TOKEN_URL = "https://oauth2.googleapis.com/token"
SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


class GmailError(RuntimeError):
    pass


def _credentials() -> tuple[str, str, str, str]:
    cid = os.environ.get("GMAIL_CLIENT_ID", "").strip()
    secret = os.environ.get("GMAIL_CLIENT_SECRET", "").strip()
    refresh = os.environ.get("GMAIL_REFRESH_TOKEN", "").strip()
    sender = os.environ.get("GMAIL_SENDER_EMAIL", "").strip()
    if not (cid and secret and refresh and sender):
        raise GmailError("GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET / GMAIL_REFRESH_TOKEN / GMAIL_SENDER_EMAIL are not all configured")
    return cid, secret, refresh, sender


def _request(method: str, url: str, *, token: str | None = None, data: bytes | None = None,
             form: bool = False) -> dict:
    headers = {"Accept": "application/json",
               "Content-Type": "application/x-www-form-urlencoded" if form else "application/json",
               "User-Agent": "zero-to-revenue-operator/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # nosec - https only, fixed Google hosts
            raw = r.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as e:
        raise GmailError(f"Gmail {method} failed: HTTP {e.code} {e.read(500).decode(errors='replace')}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise GmailError(f"Gmail {method} failed: {type(e).__name__}") from e
    if len(raw) > MAX_BYTES:
        raise GmailError("Gmail response too large")
    try:
        return json.loads(raw) if raw else {}
    except ValueError as e:
        raise GmailError("Gmail response was not JSON") from e


def get_access_token(request=_request) -> str:
    cid, secret, refresh, _ = _credentials()
    body = urllib.parse.urlencode({"client_id": cid, "client_secret": secret,
                                   "refresh_token": refresh, "grant_type": "refresh_token"}).encode()
    data = request("POST", TOKEN_URL, data=body, form=True)
    token = data.get("access_token")
    if not token:
        raise GmailError("Google did not return an access token - the refresh token may be revoked")
    return token


def send_email(to: str, subject: str, body: str, request=_request) -> dict:
    """Sends one plain-text email from GMAIL_SENDER_EMAIL. Returns {message_id, thread_id}."""
    _, _, _, sender = _credentials()
    token = get_access_token(request)
    msg = MIMEText(body, "plain", "utf-8")
    msg["To"], msg["From"], msg["Subject"] = to, sender, subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode().rstrip("=")
    data = request("POST", SEND_URL, token=token, data=json.dumps({"raw": raw}).encode())
    if not data.get("id"):
        raise GmailError(f"Gmail did not confirm the send: {str(data)[:200]}")
    return {"message_id": data["id"], "thread_id": data.get("threadId")}
