import unittest
import uuid

from core import db
from tests import dbutil


class ForeignTablesTest(unittest.TestCase):
    def test_migrations_leave_unrelated_existing_tables_alone(self):
        """On 29 Oct a migration failed with DuplicateTable against a table nobody in this repo owned, every route answered 503
        and login was down. Foreign tables with unrelated names must never stop the migrations or be modified."""
        dbutil.require_db()
        schema = "t_" + uuid.uuid4().hex[:10]
        admin = db.connect(dbutil.URL)
        admin.execute(f'CREATE SCHEMA "{schema}"')
        admin.close()
        dbutil._schemas.append(schema)
        conn = db.connect(dbutil.URL, schema=schema)
        for name in ("ventures_old", "tasks_old", "notes_old"):
            conn.execute(f"CREATE TABLE {name} (id serial PRIMARY KEY, note text)")
        conn.execute("INSERT INTO notes_old(note) VALUES ('keep me')")
        self.assertTrue(db.migrate(conn))
        self.assertEqual(conn.execute("SELECT note FROM notes_old").fetchone()[0], "keep me")
        self.assertEqual(db.migrate(conn), [])


if __name__ == "__main__":
    unittest.main()
