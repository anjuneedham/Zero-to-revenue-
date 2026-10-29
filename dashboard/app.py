"""Owner-only dashboard + API. Every /api route except the few login/setup routes needs
a session bearer token in the Authorization header (no cookies, so no CSRF surface).
Mode: LOCAL or LIVE (Vercel)."""

import hmac
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from core import ai, challenge, founder, founder_dashboard, ingest, leads, payments, rates, scheduler, weekly, workspace
from dashboard import api_data, founder_api, growth_api, lab_api
from dashboard.mcp import handle_mcp
from core import db
from core.audit import audit
from core.db import now
from core.auth import owner_login as ol
from core.orchestrator import killswitch
from core.reports import status_snapshot

PAGE = (Path(__file__).parent / "pages" / "index.html").read_text()
STATIC = Path(__file__).parent / "static"
STATIC_MIME = {".js": "text/javascript", ".css": "text/css", ".woff2": "font/woff2", ".png": "image/png",
               ".json": "application/json", ".webmanifest": "application/manifest+json", ".svg": "image/svg+xml"}
STATIC_ROOT = {"/manifest.webmanifest", "/sw.js", "/icon-192.png", "/icon-512.png"}
STATIC_DIRS = ("/css/", "/js/", "/fonts/", "/data/")


def auth_disabled() -> bool:
    """Owner-only convenience for LOCAL runs and Vercel PREVIEWS: needs AUTH_DISABLED=1 and is ignored
    on Vercel production (VERCEL_ENV=production). Never set it where the URL is public and holds real keys."""
    return os.environ.get("AUTH_DISABLED") == "1" and os.environ.get("VERCEL_ENV") != "production"


def static_file(path: str):
    """(content_type, bytes) for an allowed static file, else None. Path traversal safe."""
    if path not in STATIC_ROOT and not path.startswith(STATIC_DIRS):
        return None
    root = STATIC.resolve()
    f = (root / path.lstrip("/")).resolve()
    if root not in f.parents or not f.is_file() or f.suffix not in STATIC_MIME:
        return None
    return STATIC_MIME[f.suffix], f.read_bytes()
MAX_BODY = 4096
# Routes that legitimately take more than MAX_BODY. The HTTP handlers read up to body_limit(path)+1 bytes, so an
# oversized body is detected instead of silently truncated.
BODY_LIMITS = {"/api/leads/import": 200_000, "/api/challenge/ingest": 4_000_000}


def body_limit(path: str) -> int:
    return BODY_LIMITS.get(path, MAX_BODY)
READ_LIMIT = 48_000  # most bytes read from a request; each route enforces its own (smaller) limit. Prompt Lab bodies need more than 4 KiB.


def read_limit(path: str) -> int:
    """Bytes the HTTP handlers read before dispatch (one more than the limit so oversize is detected, not truncated)."""
    return max(READ_LIMIT, body_limit(path))
INGEST_CLIENT = None  # None = built from the environment when configured; tests inject a fake
WORKSPACE_RE = re.compile(r"^/api/founder/workspace/([a-z][a-z0-9_-]{1,40})(/import-launch-plan)?$")
PAYPAL_RE = re.compile(r"^/api/payments/([A-Za-z0-9_]{1,80})/paypal/(request|verify)$")
PAYPAL_LINK_RE = re.compile(r"^/api/payments/([A-Za-z0-9_]{1,80})/paypal/link$")
HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    # No inline scripts and no third-party origins: a tight XSS barrier.
    "Content-Security-Policy": ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                                "img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
                                "base-uri 'none'; form-action 'self'"),
}


def _ingest_client():
    """A Claude client only when the key, budget and prices are all configured; otherwise None (images are refused)."""
    from core import budget
    if not budget.llm_enabled():
        return None
    from core.llm import ClaudeClient
    return ClaudeClient()


def _json(code, obj):
    return code, "application/json", json.dumps(obj).encode()


def _fields(body: bytes, *names):
    if len(body) > MAX_BODY:
        raise ValueError("body too large")
    data = json.loads(body or b"{}")
    out = []
    for n in names:
        v = data.get(n, "")
        if not isinstance(v, str):
            raise ValueError("bad field")
        out.append(v)
    return out


def _challenge_route(method, path, body, conn, owner):
    """60-day challenge: summary, config, prospect pipeline, touches, drafts, deals."""
    data = json.loads(body or b"{}") if len(body) <= body_limit(path) else {}
    if not isinstance(data, dict):
        raise ValueError("bad request")
    if method == "GET" and path == "/api/challenge":
        return challenge.summary(conn)
    if method == "GET" and path == "/api/challenge/weekly":
        return weekly.report(conn)
    if method == "GET" and path == "/api/challenge/leads":
        return {"leads": challenge.list_leads(conn)}
    if method != "POST":
        raise ValueError("bad request")
    if path == "/api/challenge/config":
        return challenge.set_config(conn, owner, data)
    if path == "/api/challenge/leads":
        return challenge.add_lead(conn, owner, data)
    if path == "/api/challenge/stage":
        return challenge.set_stage(conn, owner, str(data.get("lead_id", "")), str(data.get("stage", "")),
                                   str(data.get("reason", "")), data.get("next_days"))
    if path == "/api/challenge/touch":
        return challenge.log_touch(conn, owner, str(data.get("lead_id", "")), str(data.get("channel", "")),
                                   str(data.get("outcome", "sent")), str(data.get("direction", "out")), str(data.get("body", "")))
    if path == "/api/challenge/draft":
        return challenge.draft_for(conn, str(data.get("lead_id", "")), str(data.get("channel", "email")), bool(data.get("follow_up")))
    if path == "/api/challenge/deal":
        return challenge.create_deal(conn, owner, str(data.get("lead_id", "")), data.get("amount"), str(data.get("plan", "")))
    if path == "/api/challenge/ingest":
        return ingest.extract(conn, INGEST_CLIENT or _ingest_client(), str(data.get("text", "")),
                              str(data.get("image", "")), str(data.get("mime", "")))
    if path == "/api/challenge/paypal-message":
        return challenge.paypal_message(conn, owner, str(data.get("deal_id", "")))
    if path == "/api/challenge/onboarding":
        return challenge.set_onboarding(conn, owner, str(data.get("deal_id", "")), str(data.get("status", "")))
    raise ValueError("bad request")


def _ai_route(conn, owner, method, path, body):
    """AI Command Center: GET /api/ai/status, POST /api/ai/classify (no model), POST /api/ai/run {business, request, task_type?, min_level?}."""
    try:
        if method == "GET" and path == "/api/ai/status":
            return _json(200, ai.status(conn))
        if method == "POST" and path in ("/api/ai/classify", "/api/ai/run"):
            if len(body) > MAX_BODY:
                raise ai.AiError("body too large")
            d = json.loads(body or b"{}")
            if not isinstance(d, dict):
                raise ai.AiError("bad request")
            if path == "/api/ai/classify":
                return _json(200, ai.classify(str(d.get("request", "")), d.get("task_type"), d.get("min_level")))
            return _json(200, ai.run(conn, ai.AnthropicClient(), str(d.get("business", "")), d.get("request"), owner, d.get("task_type"), d.get("min_level")))
    except founder.NotFound as e:
        return _json(404, {"error": str(e)})
    except (ai.AiError, founder.FounderError, json.JSONDecodeError):
        return _json(400, {"error": "bad request"})
    return _json(404, {"error": "not found"})


def handle(method, path, authz, conn, body: bytes = b""):
    """Returns (status, content_type, body_bytes)."""
    if method == "GET" and path == "/":
        return 200, "text/html; charset=utf-8", PAGE.encode()
    if method == "GET":
        f = static_file(path)
        if f:
            return 200, f[0], f[1]
    if path == "/mcp" or path.startswith("/mcp/"):
        return handle_mcp(method, path, authz, conn, body)
    if not path.startswith("/api/"):
        return _json(404, {"error": "not found"})

    # --- unauthenticated: login and one-time setup (rate limited, audited) -------
    try:
        if method == "GET" and path == "/api/auth/state":
            return _json(200, {"setup_complete": ol.setup_complete(conn), "setup_enabled": ol.setup_enabled(),
                               "mode": "LIVE" if api_data.is_live() else "LOCAL", **({"auth_disabled": True} if auth_disabled() else {})})
        if method == "POST" and path == "/api/auth/login":
            password, code = _fields(body, "password", "code")
            return _json(200, ol.login(conn, password, code))
        if method == "POST" and path == "/api/auth/setup/begin":
            token, password = _fields(body, "setup_token", "password")
            return _json(200, ol.begin_setup(conn, token, password))
        if method == "POST" and path == "/api/auth/setup/confirm":
            token, code = _fields(body, "setup_token", "code")
            return _json(200, {"recovery_codes": ol.confirm_setup(conn, token, code)})
    except ol.LockedOut:
        return _json(429, {"error": "too many attempts; try again later"})
    except ol.SetupDisabled:
        return _json(403, {"error": "setup is not enabled"})
    except ol.SetupClosed:
        return _json(403, {"error": "setup is already complete"})
    except ol.AuthError:
        return _json(401, {"error": "invalid credentials"})
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        return _json(400, {"error": str(e) if isinstance(e, ValueError) and "password" in str(e) else "bad request"})

    # --- scheduler: Vercel Cron sends "Authorization: Bearer <CRON_SECRET>" ------------
    if path == "/api/cron":
        secret = os.environ.get("CRON_SECRET", "")
        if len(secret) < 16 or not hmac.compare_digest((authz or "").encode(), f"Bearer {secret}".encode()):
            return _json(401, {"error": "unauthorized"})
        return _json(200, scheduler.tick(conn))

    # --- authenticated -------------------------------------------------------------
    token = authz[7:] if authz and authz.startswith("Bearer ") else ""
    try:
        owner = ol.IDENTITY if auth_disabled() else ol.verify_session(conn, token)
    except ol.AuthError:
        return _json(401, {"error": "unauthorized"})
    if path == "/api/founder/dashboard" and method == "GET":
        return _json(200, founder_dashboard.dashboard(conn))
    wm = WORKSPACE_RE.match(path)
    if wm:
        try:
            if method == "GET" and not wm.group(2):
                return _json(200, workspace.workspace(conn, wm.group(1)))
            if method == "POST" and wm.group(2):
                return _json(200, workspace.import_launch_plan(conn, wm.group(1), owner))
        except founder.NotFound as e:
            return _json(404, {"error": str(e)})
        except founder.FounderError as e:
            return _json(400, {"error": str(e)})
        return _json(404, {"error": "not found"})
    if path.startswith("/api/ai/"):
        return _ai_route(conn, owner, method, path, body)
    lab = lab_api.handle(conn, owner, method, path, body)
    if lab:
        return lab
    gr = growth_api.handle(conn, owner, method, path, body)
    if gr:
        return gr
    fo = founder_api.handle(conn, owner, method, path, body)
    if fo:
        return fo
    if method == "GET" and path == "/api/status":
        return _json(200, status_snapshot(conn))
    if method == "POST" and path == "/api/pause":
        killswitch.pause_all(conn, owner)
        return _json(200, {"paused": True})
    if method == "POST" and path == "/api/resume":
        killswitch.resume(conn, owner)
        return _json(200, {"paused": False})
    if method == "GET" and path == "/api/payments/overview":
        return _json(200, api_data.payments_overview(conn))
    if method == "GET" and path == "/api/rates":
        return _json(200, rates.get_rates())
    if method == "POST" and path == "/api/leads/import":
        try:
            data = json.loads(body or b"{}") if len(body) <= 200_000 else {}
            csv_text = data.get("csv", "")
            if not isinstance(csv_text, str):
                raise ValueError("bad request")
            return _json(200, leads.import_leads(conn, owner, csv_text, data.get("venture", "buildflow")))
        except leads.ImportError_ as e:
            return _json(400, {"error": str(e)})
        except (ValueError, json.JSONDecodeError):
            return _json(400, {"error": "bad request"})
    if path.startswith("/api/challenge"):
        try:
            return _json(200, _challenge_route(method, path, body, conn, owner))
        except (challenge.ChallengeError, ingest.IngestError) as e:
            return _json(400, {"error": str(e)})
        except (ValueError, json.JSONDecodeError, AttributeError, TypeError):
            return _json(400, {"error": "bad request"})
    if method == "GET" and path == "/api/plan":
        return _json(200, api_data.plan_get(conn))
    if method == "POST" and path == "/api/plan":
        try:
            data = json.loads(body or b"{}") if len(body) <= MAX_BODY else {}
            if not isinstance(data.get("done"), bool):
                raise ValueError("bad request")
            return _json(200, api_data.plan_set(conn, str(data.get("id", "")), data["done"]))
        except (ValueError, json.JSONDecodeError):
            return _json(400, {"error": "bad request"})
    if method == "GET" and path == "/api/payments":
        rows = conn.execute("SELECT p.id, p.status, p.expected_amount, p.asset, p.chain_id, p.tx_hash, p.verified_at, o.title, "
                            "l.amount AS received_amount, l.asset AS received_asset FROM payments p "
                            "LEFT JOIN opportunities o ON o.id=p.opportunity_id LEFT JOIN ledger_entries l ON l.entry_id=p.ledger_entry_id "
                            "ORDER BY p.created_at DESC LIMIT 50")
        return _json(200, {"payments": [{k: (float(v) if hasattr(v, "as_tuple") else v) for k, v in dict(r).items()} for r in rows]})
    if method == "POST" and path == "/api/payments/manual":
        try:
            data = json.loads(body or b"{}") if len(body) <= MAX_BODY else {}
            return _json(200, api_data.create_manual_payment(conn, owner, data.get("title", ""), data.get("amount", ""),
                                                             data.get("currency", "USD") or "USD", data.get("organization", "")))
        except ValueError as e:
            return _json(400, {"error": str(e)})
        except json.JSONDecodeError:
            return _json(400, {"error": "bad request"})
    if method == "GET" and path == "/api/notifications":
        rows = conn.execute("SELECT priority, channel, title, body, status, created_at FROM notifications ORDER BY created_at DESC LIMIT 30")
        return _json(200, {"notifications": [dict(r) for r in rows]})
    m = PAYPAL_LINK_RE.match(path)
    if m and method == "GET":
        try:
            return _json(200, payments.get_paypal_approval_link(conn, m.group(1)))
        except payments.VerifyError as e:
            return _json(422, {"error": str(e)})
    m = PAYPAL_RE.match(path)
    if m and method == "POST":
        pid, verb = m.groups()
        try:
            data = json.loads(body or b"{}") if len(body) <= MAX_BODY else {}
            if verb == "request":
                return _json(200, payments.request_paypal_payment(conn, pid, data.get("currency", "USD") or "USD", data.get("description", "")))
            return _json(200, payments.verify_paypal_payment(conn, pid, data.get("order_id", "")))
        except payments.VerifyError as e:
            return _json(422, {"error": str(e)})
        except json.JSONDecodeError:
            return _json(400, {"error": "bad request"})
    if method == "POST" and path == "/api/auth/logout":
        ol.logout(conn, token)
        return _json(200, {"ok": True})
    if method == "POST" and path == "/api/auth/logout-all":
        ol.logout_everywhere(conn)
        return _json(200, {"ok": True})
    return _json(404, {"error": "not found"})


def serve(host="127.0.0.1", port=8080):
    """Local server. Same code as the live site: a fresh database connection per request, so a dropped
    or suspended connection (Neon scales idle databases to zero) can never wedge the app."""
    first = db.connect()  # DATABASE_URL; fails fast and loudly if it is missing or wrong
    db.migrate(first)
    first.close()

    class H(BaseHTTPRequestHandler):
        def _go(self, method):
            n = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(min(n, read_limit(self.path.split("?")[0]) + 1)) if n else b""
            path = self.path.split("?")[0]
            conn = None
            try:
                conn = db.connect() if (path.startswith("/api/") or path.startswith("/mcp")) else None
                code, ctype, out = handle(method, path, self.headers.get("Authorization"), conn, body)
            except Exception:
                code, ctype, out = 503, "application/json", json.dumps({"error": "database unavailable"}).encode()
            finally:
                if conn is not None:
                    conn.close()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(out)))
            for k, v in HEADERS.items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(out)

        do_GET = lambda self: self._go("GET")
        do_POST = lambda self: self._go("POST")

        def log_message(self, *a):
            pass

    ThreadingHTTPServer((host, port), H).serve_forever()


if __name__ == "__main__":
    serve()
