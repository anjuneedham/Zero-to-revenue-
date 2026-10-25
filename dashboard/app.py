"""Owner-only dashboard. Every /api route needs a Firebase ID token for the owner
in the Authorization header (no cookies, so no CSRF surface). Mode: MOCK."""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from core import db
from core.audit import audit
from core.auth.firebase_auth import AuthError, OwnerAuth
from core.orchestrator import killswitch
from core.reports import status_snapshot

PAGE = (Path(__file__).parent / "pages" / "index.html").read_text()
HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": ("default-src 'self'; script-src 'self' 'unsafe-inline' https://www.gstatic.com; "
                                "connect-src 'self' https://*.googleapis.com https://*.firebaseapp.com; "
                                "frame-src https://*.firebaseapp.com https://accounts.google.com; style-src 'self' 'unsafe-inline'"),
}


STATIC = Path(__file__).parent / "static"
STATIC_TYPES = {"/manifest.webmanifest": "application/manifest+json", "/sw.js": "text/javascript",
                "/icon-192.png": "image/png", "/icon-512.png": "image/png"}


def web_config() -> dict:
    """Firebase *web* config is public by design; it is not a secret."""
    return {k: os.environ.get(v, "") for k, v in
            {"apiKey": "FIREBASE_WEB_API_KEY", "authDomain": "FIREBASE_AUTH_DOMAIN", "projectId": "FIREBASE_PROJECT_ID"}.items()}


def handle(method, path, authz, conn, auth: OwnerAuth):
    """Returns (status, content_type, body_bytes)."""
    j = lambda code, obj: (code, "application/json", json.dumps(obj).encode())
    if method == "GET" and path == "/":
        return 200, "text/html; charset=utf-8", PAGE.encode()
    if method == "GET" and path in STATIC_TYPES:
        return 200, STATIC_TYPES[path], (STATIC / path[1:]).read_bytes()
    if method == "GET" and path == "/config.json":
        return j(200, web_config())
    if not path.startswith("/api/"):
        return j(404, {"error": "not found"})
    token = authz[7:] if authz and authz.startswith("Bearer ") else ""
    try:
        owner = auth.verify(token)
    except AuthError:
        return j(401, {"error": "unauthorized"})
    if method == "GET" and path == "/api/status":
        return j(200, status_snapshot(conn))
    if method == "POST" and path == "/api/pause":
        killswitch.pause_all(conn, owner)
        return j(200, {"paused": True})
    if method == "POST" and path == "/api/resume":
        killswitch.resume(conn, owner)
        return j(200, {"paused": False})
    return j(404, {"error": "not found"})


def serve(host="127.0.0.1", port=8080):
    conn = db.connect()  # DATABASE_URL
    db.migrate(conn)
    auth = OwnerAuth()

    class H(BaseHTTPRequestHandler):
        def _go(self, method):
            code, ctype, body = handle(method, self.path.split("?")[0], self.headers.get("Authorization"), conn, auth)
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            for k, v in HEADERS.items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)
        do_GET = lambda self: self._go("GET")
        do_POST = lambda self: self._go("POST")

    ThreadingHTTPServer((host, port), H).serve_forever()


if __name__ == "__main__":
    serve()
