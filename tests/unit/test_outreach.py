import json
import os
import unittest
from unittest import mock

from agents.operator import outreach
from core.orchestrator import killswitch
from tests.authutil import session
from tests.dbutil import make_conn

CSV = "name,business,email,phone,notes\nJane Doe,Doe Contracting,jane@example.com,+18760000000,met at fair\nJohn Roe,Roe Builders,john@example.com,,\n"
GMAIL_ENV = {"GMAIL_CLIENT_ID": "cid", "GMAIL_CLIENT_SECRET": "secret",
            "GMAIL_REFRESH_TOKEN": "refresh", "GMAIL_SENDER_EMAIL": "me@yardscaledigital.com"}


class SubjectBodyTest(unittest.TestCase):
    def test_splits_subject_and_body(self):
        self.assertEqual(outreach.parse_subject_body("Subject: Hi there\n\nBody text\nmore"),
                         ("Hi there", "Body text\nmore"))

    def test_falls_back_when_no_subject_line(self):
        self.assertEqual(outreach.parse_subject_body("just a body"), ("Following up", "just a body"))


class CsvParseTest(unittest.TestCase):
    def test_parses_valid_rows(self):
        rows = outreach.parse_csv(CSV)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["email"], "jane@example.com")

    def test_rejects_missing_header_bad_email_too_large_too_many_rows(self):
        with self.assertRaises(outreach.ImportError_):
            outreach.parse_csv("a,b,c\n1,2,3\n")
        with self.assertRaises(outreach.ImportError_) as cm:
            outreach.parse_csv("name,business,email\nJane,Doe,not-an-email\n")
        self.assertIn("row 2", str(cm.exception))
        with self.assertRaises(outreach.ImportError_):
            outreach.parse_csv("x" * 200_001)
        huge = "name,business,email\n" + "".join(f"A{i},B,x{i}@example.com\n" for i in range(600))
        with self.assertRaises(outreach.ImportError_):
            outreach.parse_csv(huge)

    def test_blank_rows_skipped_and_empty_result_rejected(self):
        with self.assertRaises(outreach.ImportError_):
            outreach.parse_csv("name,business,email\n,,\n")


class DraftTest(unittest.TestCase):
    def test_draft_never_invents_a_reason_or_identity(self):
        d = outreach.draft_outreach({"name": "Jane", "business": "Doe Contracting", "email": "x@x.com"})
        self.assertIn("[OWNER TO FILL]", d)
        self.assertIn("Doe Contracting", d)
        self.assertNotIn("Jane Smith", d)  # no fabricated specifics


class LeadsDbTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()

    def test_import_is_deduped_by_email_and_audited(self):
        r1 = outreach.import_leads(self.conn, "owner", CSV)
        self.assertEqual((r1["added"], r1["skipped_duplicates"]), (2, 0))
        r2 = outreach.import_leads(self.conn, "owner", CSV)
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
        for m, p in (("GET", "/api/leads"), ("POST", "/api/leads/import"), ("POST", "/api/leads/draft")):
            self.assertEqual(self.call(m, p, auth=False)[0], 401, p)

    def test_import_then_draft_creates_approval_queued_actions_not_auto_sent(self):
        r = self.call("POST", "/api/leads/import", {"csv": CSV})[1]
        self.assertEqual(r["added"], 2)
        d = self.call("POST", "/api/leads/draft", {"count": 1})[1]
        self.assertEqual(d["drafted"], 1)
        status = self.call("GET", "/api/status")[1]
        self.assertEqual(len(status["open_user_actions"]), 1)
        a = status["open_user_actions"][0]
        self.assertEqual(a["status"], "OPEN")  # never auto-approved or auto-sent
        aid = a["action_id"]
        draft = self.call("GET", f"/api/actions/{aid}/draft")[1]["draft"]
        self.assertIn("[OWNER TO FILL]", draft)
        self.assertEqual(self.call("POST", f"/api/actions/{aid}/sent")[0], 409)  # not approved yet
        self.assertEqual(self.call("POST", f"/api/actions/{aid}/approve", {})[0], 200)
        self.assertEqual(self.call("POST", f"/api/actions/{aid}/sent")[0], 200)
        leads = self.call("GET", "/api/leads")[1]["leads"]
        sent = [x for x in leads if x["status"] == "SENT"]
        self.assertEqual(len(sent), 1)

    def test_bad_csv_rejected_with_useful_error(self):
        c, r = self.call("POST", "/api/leads/import", {"csv": "garbage,only\n1,2\n"})
        self.assertEqual(c, 400)
        self.assertIn("header", r["error"])

    def test_mark_sent_refuses_on_non_outreach_action(self):
        from agents.scout.run import run_scout
        from agents.operator import run as operator
        from tests.unit.test_scout import good
        from tests.unit.test_scout_db import Source
        import os
        from unittest import mock
        with mock.patch.dict(os.environ, {"OWNER_SKILLS": "python"}, clear=True):
            run_scout(self.conn, [Source([good()])])
            operator.step(self.conn)
        aid = self.conn.execute("select action_id from user_actions").fetchone()[0]
        self.call("POST", f"/api/actions/{aid}/approve", {})
        self.assertEqual(self.call("POST", f"/api/actions/{aid}/sent")[0], 409)


class SendOutreachTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.env = mock.patch.dict(os.environ, GMAIL_ENV, clear=True)
        self.env.start()
        r = outreach.import_leads(self.conn, "owner", CSV)
        self.assertEqual(r["added"], 2)
        self.lead = self.conn.execute("select * from leads order by created_at limit 1").fetchone()
        draft = outreach.draft_outreach(dict(self.lead))
        self.aid = "ua_lead_" + self.lead["id"]
        self.conn.execute(
            "INSERT INTO user_actions(action_id, task_id, title, why_required, exact_action, risk, status, "
            "created_at, kind, submission_id) VALUES (?, NULL, 'Send outreach', 'why', ?, 'LOW', 'OPEN', ?, 'send_outreach', NULL)",
            (self.aid, draft, "now"))
        self.conn.execute("update leads set status='DRAFTED' where id=?", (self.lead["id"],))

    def tearDown(self):
        self.env.stop()

    def test_refuses_until_approved(self):
        with self.assertRaises(outreach.SendError) as cm:
            outreach.send_outreach(self.conn, self.aid, "owner")
        self.assertIn("approve", str(cm.exception))

    def test_sends_approved_draft_marks_done_and_lead_sent(self):
        from core.actions import approve
        approve(self.conn, self.aid, "owner")
        with mock.patch("integrations.gmail.send_email", return_value={"message_id": "msg_1", "thread_id": "t1"}) as send:
            r = outreach.send_outreach(self.conn, self.aid, "owner")
        self.assertEqual(r, {"sent": True, "message_id": "msg_1"})
        send.assert_called_once()
        self.assertEqual(send.call_args[0][0], self.lead["email"])
        self.assertEqual(self.conn.execute("select status from user_actions where action_id=?", (self.aid,)).fetchone()[0], "DONE")
        self.assertEqual(self.conn.execute("select status from leads where id=?", (self.lead["id"],)).fetchone()[0], "SENT")
        self.assertEqual(self.conn.execute("select count(*) from audit_events where action='action.sent_via_gmail'").fetchone()[0], 1)

    def test_edited_body_replaces_stored_draft_and_is_what_gets_sent(self):
        from core.actions import approve
        approve(self.conn, self.aid, "owner")
        edited = "Subject: Edited subject\n\nHand-edited body."
        with mock.patch("integrations.gmail.send_email", return_value={"message_id": "msg_2"}) as send:
            outreach.send_outreach(self.conn, self.aid, "owner", edited_body=edited)
        send.assert_called_once_with(self.lead["email"], "Edited subject", "Hand-edited body.")
        self.assertEqual(self.conn.execute("select exact_action from user_actions where action_id=?", (self.aid,)).fetchone()[0], edited)

    def test_gmail_failure_leaves_action_approved_for_retry(self):
        from core.actions import approve
        approve(self.conn, self.aid, "owner")
        import integrations.gmail as gmail
        with mock.patch("integrations.gmail.send_email", side_effect=gmail.GmailError("down")):
            with self.assertRaises(outreach.SendError):
                outreach.send_outreach(self.conn, self.aid, "owner")
        self.assertEqual(self.conn.execute("select status from user_actions where action_id=?", (self.aid,)).fetchone()[0], "APPROVED")
        self.assertEqual(self.conn.execute("select status from leads where id=?", (self.lead["id"],)).fetchone()[0], "DRAFTED")

    def test_respects_kill_switch(self):
        from core.actions import approve
        approve(self.conn, self.aid, "owner")
        killswitch.pause_all(self.conn, "owner")
        with self.assertRaises(outreach.SendError):
            outreach.send_outreach(self.conn, self.aid, "owner")

    def test_batch_sends_only_approved_and_reports_failures(self):
        from core.actions import approve
        approve(self.conn, self.aid, "owner")
        with mock.patch("integrations.gmail.send_email", return_value={"message_id": "m"}):
            r = outreach.send_outreach_batch(self.conn, "owner", [self.aid, "ua_lead_does_not_exist"])
        self.assertEqual(r["sent"], 1)
        self.assertEqual(len(r["failed"]), 1)
        self.assertEqual(r["failed"][0]["action_id"], "ua_lead_does_not_exist")

    def test_api_route_requires_approval_and_sends(self):
        import dashboard.app as dash
        tok, _, _ = session(self.conn)
        c, _, out = dash.handle("POST", f"/api/actions/{self.aid}/send", f"Bearer {tok}", self.conn, b"{}")
        self.assertEqual(c, 422)  # not approved yet
        from core.actions import approve
        approve(self.conn, self.aid, "owner")
        with mock.patch("integrations.gmail.send_email", return_value={"message_id": "msg_api"}):
            c, _, out = dash.handle("POST", f"/api/actions/{self.aid}/send", f"Bearer {tok}", self.conn, b"{}")
        self.assertEqual((c, json.loads(out)["message_id"]), (200, "msg_api"))

    def test_batch_api_route(self):
        import dashboard.app as dash
        tok, _, _ = session(self.conn)
        from core.actions import approve
        approve(self.conn, self.aid, "owner")
        with mock.patch("integrations.gmail.send_email", return_value={"message_id": "m"}):
            c, _, out = dash.handle("POST", "/api/leads/send-batch", f"Bearer {tok}", self.conn,
                                    json.dumps({"action_ids": [self.aid]}).encode())
        self.assertEqual((c, json.loads(out)["sent"]), (200, 1))
        self.assertEqual(dash.handle("POST", "/api/leads/send-batch", f"Bearer {tok}", self.conn, b"{}")[0], 400)


if __name__ == "__main__":
    unittest.main()
