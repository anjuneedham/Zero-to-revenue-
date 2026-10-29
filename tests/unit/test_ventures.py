import unittest
import uuid
from pathlib import Path

import dashboard.app as dash
from core import db
from tests import dbutil
from tests.unit.test_challenge import ChallengeBase

ROLLBACK = Path(__file__).resolve().parents[2] / "database" / "rollbacks" / "008_ventures.down.sql"


class VenturesTest(ChallengeBase):
    def test_seeded_ventures_and_login_required(self):
        o = self.call("GET", "/api/ventures")[1]
        self.assertEqual([v["id"] for v in o["ventures"]], ["buildflow", "agriloop", "trading", "ecommerce"])
        self.assertEqual(dash.handle("GET", "/api/ventures", "", self.conn, b"")[0], 401)

    def test_task_lifecycle_and_validation(self):
        r = self.call("POST", "/api/ventures/task", {"venture_id": "buildflow", "title": "Provision Firebase Storage", "priority": "high", "due_date": "2026-10-31"})
        self.assertEqual(r[0], 200)
        v = self.call("GET", "/api/ventures")[1]["ventures"][0]
        self.assertEqual([(t["title"], t["priority"]) for t in v["tasks"]], [("Provision Firebase Storage", "high")])
        self.assertEqual(self.call("POST", "/api/ventures/task/status", {"id": r[1]["id"], "status": "done"})[0], 200)
        self.assertEqual(self.call("GET", "/api/ventures")[1]["ventures"][0]["tasks"], [])  # done tasks leave the open list
        self.assertIsNotNone(self.conn.execute("SELECT done_at FROM venture_tasks WHERE id=?", (r[1]["id"],)).fetchone()[0])
        for bad in ({"venture_id": "nope", "title": "x"}, {"venture_id": "buildflow", "title": ""}, {"venture_id": "buildflow", "title": "x", "priority": "urgent"},
                    {"venture_id": "buildflow", "title": "x", "due_date": "tomorrow"}):
            self.assertEqual(self.call("POST", "/api/ventures/task", bad)[0], 400, bad)
        self.assertEqual(self.call("POST", "/api/ventures/task/status", {"id": "missing", "status": "done"})[0], 400)
        self.assertEqual(self.call("POST", "/api/ventures/task/status", {"id": r[1]["id"], "status": "wat"})[0], 400)

    def test_decisions_scoped_and_shared(self):
        a = self.call("POST", "/api/ventures/decision", {"venture_id": "ecommerce", "title": "Which store is the brand?"})[1]["id"]
        b = self.call("POST", "/api/ventures/decision", {"venture_id": "", "title": "Keep Scout's gig feed?"})[1]["id"]
        o = self.call("GET", "/api/ventures")[1]
        self.assertEqual([d["id"] for d in o["shared_decisions"]], [b])
        self.assertEqual([d["id"] for v in o["ventures"] if v["id"] == "ecommerce" for d in v["decisions"]], [a])
        self.assertEqual(self.call("POST", "/api/ventures/decision/decide", {"id": a, "decision": "Kadeform"})[0], 200)
        self.assertEqual(self.call("POST", "/api/ventures/decision/decide", {"id": a, "decision": ""})[0], 400)
        o = self.call("GET", "/api/ventures")[1]
        self.assertEqual([d["decision"] for d in o["recent_decisions"]], ["Kadeform"])

    def test_experiments_close_once(self):
        e = self.call("POST", "/api/ventures/experiment", {"venture_id": "buildflow", "hypothesis": "Instagram DMs beat WhatsApp", "metric": "replies per 20 messages"})[1]["id"]
        self.assertEqual(len(self.call("GET", "/api/ventures")[1]["ventures"][0]["experiments"]), 1)
        self.assertEqual(self.call("POST", "/api/ventures/experiment/close", {"id": e, "status": "won", "result": "6 vs 2"})[0], 200)
        self.assertEqual(self.call("POST", "/api/ventures/experiment/close", {"id": e, "status": "lost"})[0], 400)  # already closed
        self.assertEqual(self.call("POST", "/api/ventures/experiment", {"venture_id": "buildflow", "hypothesis": "", "metric": "x"})[0], 400)

    def test_writes_are_audited(self):
        self.call("POST", "/api/ventures/task", {"venture_id": "trading", "title": "Paper trade for 30 days"})
        self.assertEqual(self.conn.execute("SELECT count(*) FROM audit_events WHERE action='venture.task_add'").fetchone()[0], 1)


class MigrationReversibleTest(ChallengeBase):
    def test_rollback_removes_tables_and_migration_reapplies(self):
        self.conn.raw.execute(ROLLBACK.read_text())
        self.assertIsNone(self.conn.execute("SELECT to_regclass('ventures')").fetchone()[0])
        self.assertIsNone(self.conn.execute("SELECT 1 FROM schema_migrations WHERE name='008_ventures.sql'").fetchone())
        self.assertIn("008_ventures.sql", db.migrate(self.conn))
        self.assertEqual(self.conn.execute("SELECT count(*) FROM ventures").fetchone()[0], 4)

    def test_rollback_dir_is_outside_the_migration_runner(self):
        self.assertFalse(any("down" in f.name for f in db.MIGRATIONS.glob("*.sql")))


class PreexistingTablesTest(unittest.TestCase):
    def test_migration_survives_unrelated_tables_with_common_names(self):
        """Production already had a `decisions` table that no migration in this repo creates; the first 008 used that
        name, failed with DuplicateTable and took every API route down (503). Names must not collide, and the foreign
        tables must be left alone."""
        dbutil.require_db()
        schema = "t_" + uuid.uuid4().hex[:10]
        admin = db.connect(dbutil.URL)
        admin.execute(f'CREATE SCHEMA "{schema}"')
        admin.close()
        dbutil._schemas.append(schema)
        conn = db.connect(dbutil.URL, schema=schema)
        for name in ("decisions", "experiments", "ventures_old", "tasks_old"):
            conn.execute(f"CREATE TABLE {name} (id serial PRIMARY KEY, note text)")
        conn.execute("INSERT INTO decisions(note) VALUES ('keep me')")
        self.assertIn("008_ventures.sql", db.migrate(conn))
        self.assertEqual(conn.execute("SELECT note FROM decisions").fetchone()[0], "keep me")
        self.assertEqual(conn.execute("SELECT count(*) FROM ventures").fetchone()[0], 4)


if __name__ == "__main__":
    unittest.main()
