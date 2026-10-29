"""Owner-only dashboard + API. Every /api route except the few login/setup routes needs
a session bearer token in the Authorization header (no cookies, so no CSRF surface).
Mode: MOCK."""

import hmac
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from agents.operator import outreach, run as operator
from agents.scout.run import run_scout
from agents.treasury import run as treasury
from core import actions, founder_dashboard, rates, scheduler
from dashboard import api_data, founder_api
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
SCOUT_SOURCES = None  # None = defaults (public GitHub bounty issues); tests inject fixtures
SCOUT_CLIENT = None
TREASURY_RPC = None  # None = live read-only RPC; tests inject a fake
ACTION_RE = re.compile(r"^/api/actions/([A-Za-z0-9_]{1,80})/(approve|reject|submitted|sent|draft|send|submit-email)$")
PAY_RE = re.compile(r"^/api/payments/([A-Za-z0-9_]{1,80})/verify$")
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
        return _json(200, scheduler.tick(conn, SCOUT_SOURCES, TREASURY_RPC))

    # --- authenticated -------------------------------------------------------------
    token = authz[7:] if authz and authz.startswith("Bearer ") else ""
    try:
        owner = ol.IDENTITY if auth_disabled() else ol.verify_session(conn, token)
    except ol.AuthError:
        return _json(401, {"error": "unauthorized"})
    if path == "/api/founder/dashboard" and method == "GET":
        return _json(200, founder_dashboard.dashboard(conn))
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
    if method == "GET" and path == "/api/opportunities":
        rows = conn.execute(
            "SELECT id,title,organization,source_url,status,opportunity_score,risk_score,confidence,expected_payment,"
            "required_capital,deadline,scam_indicators,missing_information,recommended_action,discovered_at "
            "FROM opportunities ORDER BY (status='QUALIFIED') DESC, opportunity_score DESC, discovered_at DESC LIMIT 100").fetchall()
        return _json(200, {"opportunities": [{k: (float(v) if hasattr(v, "as_tuple") else v) for k, v in dict(r).items()} for r in rows]})
    if method == "POST" and path == "/api/opportunities/approve":
        try:
            data = json.loads(body or b"{}") if len(body) <= MAX_BODY else {}
            ids = data.get("ids")
            if not isinstance(ids, list) or not ids:
                raise ValueError("bad request")
            return _json(200, api_data.approve_for_drafting(conn, owner, ids))
        except (ValueError, json.JSONDecodeError):
            return _json(400, {"error": "bad request"})
    if method == "POST" and path == "/api/opportunities/dismiss":
        try:
            data = json.loads(body or b"{}") if len(body) <= MAX_BODY else {}
            ids = data.get("ids")
            force = data.get("force", False)
            if not isinstance(ids, list) or not ids or not isinstance(force, bool):
                raise ValueError("bad request")
            return _json(200, api_data.dismiss_opportunities(conn, owner, ids, force=force))
        except (ValueError, json.JSONDecodeError):
            return _json(400, {"error": "bad request"})
    if method == "POST" and path == "/api/scout/run":
        return _json(200, run_scout(conn, SCOUT_SOURCES, SCOUT_CLIENT))
    if method == "GET" and path == "/api/scout/overview":
        return _json(200, api_data.scout_overview(conn))
    if method == "GET" and path == "/api/operator/board":
        return _json(200, api_data.operator_board(conn))
    if method == "GET" and path == "/api/treasury/overview":
        return _json(200, api_data.treasury_overview(conn))
    if method == "GET" and path == "/api/rates":
        return _json(200, rates.get_rates())
    if method == "GET" and path == "/api/leads":
        rows = conn.execute("SELECT id,name,business,email,phone,status,created_at FROM leads ORDER BY created_at DESC LIMIT 200")
        return _json(200, {"leads": [dict(r) for r in rows]})
    if method == "POST" and path == "/api/leads/import":
        try:
            data = json.loads(body or b"{}") if len(body) <= 200_000 else {}
            csv_text = data.get("csv", "")
            if not isinstance(csv_text, str):
                raise ValueError("bad request")
            return _json(200, outreach.import_leads(conn, owner, csv_text))
        except outreach.ImportError_ as e:
            return _json(400, {"error": str(e)})
        except (ValueError, json.JSONDecodeError):
            return _json(400, {"error": "bad request"})
    if method == "POST" and path == "/api/leads/draft":
        try:
            data = json.loads(body or b"{}") if len(body) <= MAX_BODY else {}
            n = max(1, min(int(data.get("count", 15)), 50))
        except (ValueError, json.JSONDecodeError):
            return _json(400, {"error": "bad request"})
        rows = conn.execute("SELECT * FROM leads WHERE status='NEW' ORDER BY created_at LIMIT ?", (n,)).fetchall()
        made = []
        for r in rows:
            lead = dict(r)
            draft = outreach.draft_outreach(lead)
            action_id = "ua_lead_" + lead["id"]
            conn.execute(
                "INSERT INTO user_actions(action_id, task_id, title, why_required, exact_action, risk, status, "
                "created_at, kind, submission_id) VALUES (?, NULL, ?, ?, ?, 'LOW', 'OPEN', ?, 'send_outreach', NULL) "
                "ON CONFLICT (action_id) DO NOTHING",
                (action_id, f"Send outreach to {lead['business'] or lead['name'] or lead['email']}"[:200],
                 "Needs your review and approval before it goes out - edit it if you want, then send "
                 "it yourself through Gmail here, or confirm you sent it another way.",
                 draft, now()))
            conn.execute("UPDATE leads SET status='DRAFTED' WHERE id=?", (lead["id"],))
            made.append(action_id)
        return _json(200, {"drafted": len(made)})
    if method == "POST" and path == "/api/leads/send-batch":
        try:
            data = json.loads(body or b"{}") if len(body) <= MAX_BODY else {}
            ids = data.get("action_ids")
            if not isinstance(ids, list) or not ids:
                raise ValueError("bad request")
            return _json(200, outreach.send_outreach_batch(conn, owner, ids))
        except (ValueError, json.JSONDecodeError):
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
    if method == "POST" and path == "/api/operator/run":
        return _json(200, {"steps": operator.run(conn)})
    if method == "POST" and path == "/api/treasury/run":
        return _json(200, treasury.check_balances(conn, TREASURY_RPC))
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
    m = ACTION_RE.match(path)
    if m:
        aid, verb = m.groups()
        try:
            if verb == "draft" and method == "GET":
                a_row = conn.execute("SELECT kind, exact_action FROM user_actions WHERE action_id=?", (aid,)).fetchone()
                if a_row and a_row["kind"] == "send_outreach":
                    return _json(200, {"draft": a_row["exact_action"] or ""})
                row = conn.execute("SELECT d.content FROM user_actions a JOIN deliverables d ON d.task_id=a.task_id WHERE a.action_id=?", (aid,)).fetchone()
                return _json(200, {"draft": row["content"] if row else ""})
            if method != "POST":
                return _json(404, {"error": "not found"})
            if verb == "approve":
                actions.approve(conn, aid, owner)
            elif verb == "reject":
                actions.reject(conn, aid, owner)
            elif verb == "sent":
                actions.mark_sent(conn, aid, owner)
            elif verb == "send":
                data = json.loads(body or b"{}") if len(body) <= MAX_BODY else {}
                return _json(200, outreach.send_outreach(conn, aid, owner, data.get("edited_body") or None))
            elif verb == "submit-email":
                data = json.loads(body or b"{}") if len(body) <= MAX_BODY else {}
                return _json(200, outreach.send_submission_email(conn, aid, owner, data.get("to_email", ""), data.get("edited_body") or None))
            else:
                (proof,) = _fields(body, "proof_url")
                actions.mark_submitted(conn, aid, owner, proof)
            return _json(200, {"ok": True})
        except actions.ActionError as e:
            return _json(409, {"error": str(e)})
        except outreach.SendError as e:
            return _json(422, {"error": str(e)})
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
    m = PAYPAL_LINK_RE.match(path)
    if m and method == "GET":
        try:
            return _json(200, treasury.get_paypal_approval_link(conn, m.group(1)))
        except treasury.VerifyError as e:
            return _json(422, {"error": str(e)})
    m = PAYPAL_RE.match(path)
    if m and method == "POST":
        pid, verb = m.groups()
        try:
            data = json.loads(body or b"{}") if len(body) <= MAX_BODY else {}
            if verb == "request":
                return _json(200, treasury.request_paypal_payment(conn, pid, data.get("currency", "USD") or "USD", data.get("description", "")))
            return _json(200, treasury.verify_paypal_payment(conn, pid, data.get("order_id", "")))
        except treasury.VerifyError as e:
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
            body = self.rfile.read(min(n, MAX_BODY + 1)) if n else b""
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
