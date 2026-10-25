"""Vercel entry point. Fails closed: Vercel's filesystem is ephemeral, so it must
never run against SQLite (the kill switch would silently reset). Until the
Postgres port lands (see docs/runbooks/VERCEL_AND_APK.md) this serves only the
static app shell and answers every /api route with 503."""

import json
import os
from http.server import BaseHTTPRequestHandler

from dashboard import app as dash

HAS_PERSISTENT_DB = os.environ.get("DATABASE_URL", "").startswith(("postgres://", "postgresql://"))


class handler(BaseHTTPRequestHandler):
    def _go(self, method):
        path = self.path.split("?")[0]
        if path.startswith("/api/"):
            code, ctype, body = 503, "application/json", json.dumps(
                {"error": "persistent database not configured"
                         if not HAS_PERSISTENT_DB else "postgres backend not implemented yet"}).encode()
        else:
            code, ctype, body = dash.handle(method, path, None, None, None)
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        for k, v in dash.HEADERS.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._go("GET")

    def do_POST(self):
        self._go("POST")
