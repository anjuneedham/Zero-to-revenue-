"""Vercel entry point (serverless, Neon Postgres).

Fails closed: without a postgres DATABASE_URL, or if the database is unreachable,
every /api route answers 503 - never a fake or partial state. The schema is applied
(once per cold start) under an advisory lock, so concurrent cold starts are safe.
A fresh connection per request: serverless instances are short-lived.
"""

import json
import os
from http.server import BaseHTTPRequestHandler

from core import db
from dashboard import app as dash

_migrated = False


def _db_url() -> str:
    return os.environ.get("DATABASE_URL", "")


def has_persistent_db() -> bool:
    return _db_url().startswith(("postgres://", "postgresql://"))


def _api(method, path, authz, body=b""):
    global _migrated
    unavailable = (503, "application/json", json.dumps({"error": "database unavailable"}).encode())
    if not has_persistent_db():
        return unavailable
    try:
        conn = db.connect(_db_url())
    except Exception:
        return unavailable
    try:
        if not _migrated:
            db.migrate(conn)
            _migrated = True
        return dash.handle(method, path, authz, conn, body)
    except Exception:
        return unavailable  # never leak driver errors (may contain hosts/users)
    finally:
        conn.close()


class handler(BaseHTTPRequestHandler):
    def _go(self, method):
        path = self.path.split("?")[0]
        n = int(self.headers.get("Content-Length") or 0)
        req_body = self.rfile.read(min(n, dash.MAX_BODY + 1)) if n else b""
        if path.startswith("/api/"):
            code, ctype, body = _api(method, path, self.headers.get("Authorization"), req_body)
        else:
            code, ctype, body = dash.handle(method, path, None, None)
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in dash.HEADERS.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._go("GET")

    def do_POST(self):
        self._go("POST")

    def log_message(self, *args):  # no request logging: headers may carry tokens
        pass
