import json
import unittest

from core import leads
from tests.authutil import session
from tests.dbutil import make_conn

CSV = "name,business,email,phone,notes\nJane Doe,Doe Contracting,jane@example.com,+18760000000,met at fair\nJohn Roe,Roe Builders,john@example.com,,\n"


class CsvParseTest(unittest.TestCase):
    def test_parses_valid_rows(self):
        rows = leads.parse_csv(CSV)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["email"], "jane@example.com")

    def test_rejects_missing_header_bad_email_too_large_too_many_rows(self):
        with self.assertRaises(leads.ImportError_):
            leads.parse_csv("a,b,c\n1,2,3\n")
        with self.assertRaises(leads.ImportError_) as cm:
            leads.parse_csv("name,business,email\nJane,Doe,not-an-email\n")
        self.assertIn("row 2", str(cm.exception))
        with self.assertRaises(leads.ImportError_):
            leads.parse_csv("x" * 200_001)
        huge = "name,business,email\n" + "".join(f"A{i},B,x{i}@example.com\n" for i in range(600))
        with self.assertRaises(leads.ImportError_):
            leads.parse_csv(huge)

    def test_blank_rows_skipped_and_empty_result_rejected(self):
        with self.assertRaises(leads.ImportError_):
            leads.parse_csv("name,business,email\n,,\n")


class LeadsDbTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()

    def test_import_is_deduped_by_email_and_audited(self):
        r1 = leads.import_leads(self.conn, "owner", CSV)
        self.assertEqual((r1["added"], r1["skipped_duplicates"]), (2, 0))
        r2 = leads.import_leads(self.conn, "owner", CSV)
        self.assertEqual((r2["added"], r2["skipped_duplicates"]), (0, 2))
        self.assertEqual(self.conn.execute("select count(*) from leads").fetchone()[0], 2)
        self.assertEqual(self.conn.execute("select count(*) from audit_events where action='leads.import'").fetchone()[0], 2)


class LeadsApiTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.tok, _, _ = session(self.conn)

    def call(self, method, path, body=None, auth=True):
        import dashboard.app as dash
        c, _, out = dash.handle(method, path, f"Bearer {self.tok}" if auth else None, self.conn,
                                json.dumps(body).encode() if body is not None else b"")
        return c, json.loads(out)

    def test_requires_login(self):
        for m, p in (("POST", "/api/leads/import"),):
            self.assertEqual(self.call(m, p, auth=False)[0], 401, p)

    def test_bad_csv_rejected_with_useful_error(self):
        c, r = self.call("POST", "/api/leads/import", {"csv": "garbage,only\n1,2\n"})
        self.assertEqual(c, 400)
        self.assertIn("header", r["error"])


if __name__ == "__main__":
    unittest.main()
