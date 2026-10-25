"""The local launcher really starts the same app, against the database, on loopback only."""

import json
import os
import subprocess
import sys
import time
import unittest
import urllib.request
import uuid
from pathlib import Path

from core import db
from tests import dbutil

ROOT = Path(__file__).resolve().parents[2]
PORT = 8093


class LocalAppTest(unittest.TestCase):
    def test_launcher_starts_serves_and_reports_local(self):
        dbutil.require_db()
        schema = "t_" + uuid.uuid4().hex[:10]
        admin = db.connect(dbutil.URL)
        admin.execute(f'CREATE SCHEMA "{schema}"')
        dbutil._schemas.append(schema)
        sep = "&" if "?" in dbutil.URL else "?"
        env = {**os.environ, "DATABASE_URL": f"{dbutil.URL}{sep}options=-csearch_path%3D{schema}"}
        env.pop("VERCEL", None)
        proc = subprocess.Popen([sys.executable, str(ROOT / "scripts" / "run_local.py"), "--port", str(PORT), "--no-browser",
                                 "--env-file", "/nonexistent/.env.local"], env=env, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        try:
            for _ in range(50):
                try:
                    state = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/auth/state", timeout=2))
                    break
                except Exception:
                    time.sleep(0.2)
            else:
                self.fail("local app did not start: " + (proc.poll() and proc.stdout.read().decode()[:300] or "still starting"))
            self.assertEqual(state["mode"], "LOCAL")
            self.assertEqual(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=2).status, 200)
            self.assertEqual(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/fonts/inter.woff2", timeout=2).status, 200)
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_launcher_refuses_without_database_or_on_live_host(self):
        base = {k: v for k, v in os.environ.items() if k not in ("DATABASE_URL", "VERCEL")}
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "run_local.py"), "--no-browser", "--env-file", "/nonexistent"],
                           env=base, cwd=ROOT, capture_output=True, text=True, timeout=20)
        self.assertEqual(r.returncode, 1)
        self.assertIn("DATABASE_URL is missing", r.stdout)
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "run_local.py"), "--no-browser", "--env-file", "/nonexistent"],
                           env={**base, "VERCEL": "1"}, cwd=ROOT, capture_output=True, text=True, timeout=20)
        self.assertEqual(r.returncode, 2)

    def test_secret_values_never_printed(self):
        base = {k: v for k, v in os.environ.items() if k != "VERCEL"}
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "run_local.py"), "--no-browser", "--port", "8092", "--env-file", "/nonexistent"],
                           env={**base, "DATABASE_URL": "postgresql://user:SECRETPASS@127.0.0.1:1/none"}, cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("SECRETPASS", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
