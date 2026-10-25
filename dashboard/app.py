"""Owner-only dashboard + API. Every /api route except the few login/setup routes needs
a session bearer token in the Authorization header (no cookies, so no CSRF surface).
Mode: MOCK."""

import hmac
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from agents.operator import run as operator
from agents.scout.run import run_scout
from agents.treasury import run as treasury
from core import actions, scheduler
from dashboard.mcp import handle_mcp
from core import db
from core.audit import audit
from core.auth import owner_login as ol
from core.orchestrator import killswitch
from core.reports import status_snapshot

PAGE = (Path(__file__).parent / "pages" / "index.html").read_text()
STATIC = Path(__file__).parent / "static"
STATIC_TYPES = {"/manifest.webmanifest": "application/manifest+json", "/sw.js": "text/javascript",
                "/app.js": "text/javascript", "/icon-192.png": "image/png", "/icon-512.png": "image/png"}
MAX_BODY = 4096
SCOUT_SOURCES = None  # None = defaults (public GitHub bounty issues); tests inject fixtures
SCOUT_CLIENT = None
TREASURY_RPC = None  # None = live read-only RPC; tests inject a fake
ACTION_RE = re.compile(r"^/api/actions/([A-Za-z0-9_]{1,80})/(approve|reject|submitted|draft)$")
PAY_RE = re.compile(r"^/api/payments/([A-Za-z0-9_]{1,80})/verify$")
HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    # No inline scripts and no third-party origins: a tight XSS barrier.
    "Content-Security-Policy": ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                                "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; "
                                "base-uri 'none'; form-action 'self'"),
}


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


def handle(method, path, authz, conn, body: bytes = b""):
    """Returns (status, content_type, body_bytes)."""
    if method == "GET" and path == "/":
        return 200, "text/html; charset=utf-8", PAGE.encode()
    if method == "GET" and path in STATIC_TYPES:
        return 200, STATIC_TYPES[path], (STATIC / path[1:]).read_bytes()
    if path == "/mcp" or path.startswith("/mcp/"):
        return handle_mcp(method, path, authz, conn, body)
    if not path.startswith("/api/"):
        return _json(404, {"error": "not found"})

    # --- unauthenticated: login and one-time setup (rate limited, audited) -------
    try:
        if method == "GET" and path == "/api/auth/state":
            return _json(200, {"setup_complete": ol.setup_complete(conn), "setup_enabled": ol.setup_enabled()})
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
        return _json(200, scheduler.tick(conn, SCOUT_SOURCES, TREASURY_RPC))

    # --- authenticated -------------------------------------------------------------
    token = authz[7:] if authz and authz.startswith("Bearer ") else ""
    try:
        owner = ol.verify_session(conn, token)
    except ol.AuthError:
        return _json(401, {"error": "unauthorized"})
    if method == "GET" and path == "/api/status":
        return _json(200, status_snapshot(conn))
    if method == "POST" and path == "/api/pause":
        killswitch.pause_all(conn, owner)
        return _json(200, {"paused": True})
    if method == "POST" and path == "/api/resume":
        killswitch.resume(conn, owner)
        return _json(200, {"paused": False})
    if method == "GET" and path == "/api/opportunities":
        rows = conn.execute(
            "SELECT id,title,organization,source_url,status,opportunity_score,risk_score,confidence,expected_payment,"
            "required_capital,deadline,scam_indicators,missing_information,recommended_action "
            "FROM opportunities ORDER BY (status='QUALIFIED') DESC, opportunity_score DESC, discovered_at DESC LIMIT 25").fetchall()
        return _json(200, {"opportunities": [{k: (float(v) if hasattr(v, "as_tuple") else v) for k, v in dict(r).items()} for r in rows]})
    if method == "POST" and path == "/api/scout/run":
        return _json(200, run_scout(conn, SCOUT_SOURCES, SCOUT_CLIENT))
    if method == "POST" and path == "/api/operator/run":
        return _json(200, {"steps": operator.run(conn)})
    if method == "POST" and path == "/api/treasury/run":
        return _json(200, treasury.check_balances(conn, TREASURY_RPC))
    if method == "GET" and path == "/api/payments":
        rows = conn.execute("SELECT p.id, p.status, p.expected_amount, p.asset, p.chain_id, p.tx_hash, p.verified_at, o.title "
                            "FROM payments p LEFT JOIN opportunities o ON o.id=p.opportunity_id ORDER BY p.created_at DESC LIMIT 50")
        return _json(200, {"payments": [{k: (float(v) if hasattr(v, "as_tuple") else v) for k, v in dict(r).items()} for r in rows]})
    if method == "GET" and path == "/api/notifications":
        rows = conn.execute("SELECT priority, channel, title, body, status, created_at FROM notifications ORDER BY created_at DESC LIMIT 30")
        return _json(200, {"notifications": [dict(r) for r in rows]})
    m = ACTION_RE.match(path)
    if m:
        aid, verb = m.groups()
        try:
            if verb == "draft" and method == "GET":
                row = conn.execute("SELECT d.content FROM user_actions a JOIN deliverables d ON d.task_id=a.task_id WHERE a.action_id=?", (aid,)).fetchone()
                return _json(200, {"draft": row["content"] if row else ""})
            if method != "POST":
                return _json(404, {"error": "not found"})
            if verb == "approve":
                actions.approve(conn, aid, owner)
            elif verb == "reject":
                actions.reject(conn, aid, owner)
            else:
                (proof,) = _fields(body, "proof_url")
                actions.mark_submitted(conn, aid, owner, proof)
            return _json(200, {"ok": True})
        except actions.ActionError as e:
            return _json(409, {"error": str(e)})
        except (ValueError, json.JSONDecodeError):
            return _json(400, {"error": "bad request"})
    m = PAY_RE.match(path)
    if m and method == "POST":
        try:
            chain, tx = _fields(body, "chain_id", "tx_hash")
            return _json(200, treasury.verify_payment(conn, m.group(1), int(chain), tx, TREASURY_RPC))
        except treasury.VerifyError as e:
            return _json(422, {"error": str(e)})
        except ValueError:
            return _json(400, {"error": "chain_id must be a number"})
    if method == "POST" and path == "/api/auth/logout":
        ol.logout(conn, token)
        return _json(200, {"ok": True})
    if method == "POST" and path == "/api/auth/logout-all":
        ol.logout_everywhere(conn)
        return _json(200, {"ok": True})
    return _json(404, {"error": "not found"})


def serve(host="127.0.0.1", port=8080):
    conn = db.connect()  # DATABASE_URL
    db.migrate(conn)

    class H(BaseHTTPRequestHandler):
        def _go(self, method):
            n = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(min(n, MAX_BODY + 1)) if n else b""
            code, ctype, out = handle(method, self.path.split("?")[0], self.headers.get("Authorization"), conn, body)
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
