"""Hardened read-only HTTP GET for Scout: https only, host allowlist, no redirects,
size cap, timeout. Everything fetched is UNTRUSTED DATA."""

import json
import urllib.error
import urllib.request
from urllib.parse import urlsplit

MAX_BYTES = 1_000_000
TIMEOUT = 10


class FetchError(RuntimeError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        raise FetchError("redirects are not followed")


def fetch_json(url: str, allowed_hosts: set[str], headers: dict | None = None):
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in allowed_hosts:
        raise FetchError(f"blocked url: {parts.scheme}://{parts.hostname}")
    req = urllib.request.Request(url, headers={"User-Agent": "zero-to-revenue-scout/1.0", **(headers or {})})
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=TIMEOUT) as r:
            raw = r.read(MAX_BYTES + 1)
    except FetchError:
        raise
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise FetchError(f"fetch failed: {type(e).__name__}") from e
    if len(raw) > MAX_BYTES:
        raise FetchError("response too large")
    try:
        return json.loads(raw)
    except ValueError as e:
        raise FetchError("response was not JSON") from e
