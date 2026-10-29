import json
import os
import unittest
from datetime import date
from unittest import mock

import dashboard.app as dash
from agents.operator import outreach, pitches
from core import challenge
from core.db import now
from tests.authutil import session
from tests.dbutil import make_conn
from tests.unit.test_phases_3_6 import ENV


class ChallengeBase(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.env = mock.patch.dict(os.environ, ENV, clear=True)
        self.env.start()
        self.tok, _, _ = session(self.conn)

    def tearDown(self):
        self.env.stop()

    def call(self, method, path, body=None):
        c, _, out = dash.handle(method, path, f"Bearer {self.tok}", self.conn, json.dumps(body).encode() if body is not None else b"")
        return c, json.loads(out)

    def lead(self, **kw):
        d = {"venture": "buildflow", "name": "Tia", "business": "Tia Tiling", "phone": "876-555-0100", "channel": "whatsapp"}
        d.update(kw)
        return self.call("POST", "/api/challenge/leads", d)[1]["id"]

    def verify(self, payment_id, usd, when="2026-11-10T12:00:00+00:00"):
        """Stand-in for Treasury's verification (PayPal/on-chain verification is covered in test_paypal/test_phases_3_6)."""
        eid = "led_" + payment_id
        self.conn.execute("INSERT INTO ledger_entries(entry_id,date,type,asset,amount,usd_value,status) VALUES (?,?,'receipt','USD',?,?,'VERIFIED')",
                          (eid, when, str(usd), usd))
        self.conn.execute("UPDATE payments SET status='PAYMENT_VERIFIED', verified_at=?, ledger_entry_id=? WHERE id=?", (when, eid, payment_id))


class ConfigTest(ChallengeBase):
    def test_defaults_match_the_challenge(self):
        c = challenge.get_config(self.conn)
        self.assertEqual((c["start"], c["end"], c["target_usd"]), ("2026-11-01", "2026-12-31", 10000))
        self.assertEqual(c["offers"]["buildflow"]["annual_usd"], 600)
        self.assertEqual(c["offers"]["buildflow"]["free_months"], 2)
        self.assertIsNone(c["offers"]["agriloop"]["annual_usd"])  # no invented Agriloop price

    def test_save_and_validate(self):
        c = self.call("POST", "/api/challenge/config", {"target_usd": 12000, "offers": {"agriloop": {"annual_usd": "300", "monthly_usd": "", "free_months": 2}}})[1]
        self.assertEqual((c["target_usd"], c["offers"]["agriloop"]["annual_usd"]), (12000, 300))
        self.assertEqual(challenge.get_config(self.conn)["target_usd"], 12000)
        for bad in ({"target_usd": -1}, {"start": "nope"}, {"start": "2027-01-01", "end": "2026-12-31"},
                    {"offers": {"buildflow": {"annual_usd": "x", "free_months": 2}}}, {"offers": {"buildflow": {"annual_usd": "5", "free_months": 99}}}):
            self.assertEqual(self.call("POST", "/api/challenge/config", bad)[0], 400, bad)

    def test_requires_login(self):
        self.assertEqual(dash.handle("GET", "/api/challenge", None, self.conn)[0], 401)


class PipelineTest(ChallengeBase):
    def test_add_lead_validation_and_duplicate_email(self):
        self.assertEqual(self.call("POST", "/api/challenge/leads", {"venture": "x", "name": "a", "phone": "1"})[0], 400)
        self.assertEqual(self.call("POST", "/api/challenge/leads", {"venture": "buildflow"})[0], 400)
        self.assertEqual(self.call("POST", "/api/challenge/leads", {"venture": "buildflow", "name": "a"})[0], 400)  # no way to reach them
        self.assertEqual(self.call("POST", "/api/challenge/leads", {"venture": "buildflow", "name": "a", "email": "nope"})[0], 400)
        self.lead(email="a@b.co")
        self.assertEqual(self.call("POST", "/api/challenge/leads", {"venture": "agriloop", "name": "b", "email": "A@B.co"})[0], 400)

    def test_touches_move_stage_forward_only_and_schedule_follow_up(self):
        lid = self.lead()
        stage = lambda: self.conn.execute("SELECT stage, next_action_at FROM leads WHERE id=?", (lid,)).fetchone()
        self.call("POST", "/api/challenge/touch", {"lead_id": lid, "channel": "whatsapp", "outcome": "sent", "body": "hi"})
        self.assertEqual(stage()["stage"], "contacted")
        self.assertIsNotNone(stage()["next_action_at"])
        self.call("POST", "/api/challenge/touch", {"lead_id": lid, "channel": "whatsapp", "direction": "in", "outcome": "replied"})
        self.assertEqual(stage()["stage"], "replied")
        self.call("POST", "/api/challenge/touch", {"lead_id": lid, "channel": "whatsapp", "outcome": "sent"})
        self.assertEqual(stage()["stage"], "replied")  # a later 'sent' never moves a lead backwards
        self.call("POST", "/api/challenge/touch", {"lead_id": lid, "channel": "call", "outcome": "booked"})
        self.assertEqual(stage()["stage"], "onboarding_booked")
        self.assertEqual(self.call("POST", "/api/challenge/touch", {"lead_id": lid, "channel": "fax"})[0], 400)

    def test_decline_and_opt_out_stop_all_drafting_and_sending(self):
        lid = self.lead(email="x@y.co")
        self.call("POST", "/api/challenge/touch", {"lead_id": lid, "channel": "email", "outcome": "declined"})
        row = self.conn.execute("SELECT stage, status FROM leads WHERE id=?", (lid,)).fetchone()
        self.assertEqual((row["stage"], row["status"]), ("lost", "SKIPPED"))
        self.assertEqual(self.call("POST", "/api/leads/draft", {"count": 10})[1]["drafted"], 0)
        self.conn.execute("INSERT INTO user_actions(action_id,title,why_required,exact_action,risk,status,created_at,kind) "
                          "VALUES (?,?,?,?,'LOW','APPROVED',?,'send_outreach')", ("ua_lead_" + lid, "t", "w", "Subject: hi\n\nbody", now()))
        with self.assertRaises(outreach.SendError) as cm:
            outreach.send_outreach(self.conn, "ua_lead_" + lid, "owner")
        self.assertIn("opted out", str(cm.exception))

    def test_sending_email_logs_a_touch_and_advances_the_lead(self):
        lid = self.lead(email="x@y.co")
        self.assertEqual(self.call("POST", "/api/leads/draft", {"count": 5})[1]["drafted"], 1)
        aid = "ua_lead_" + lid
        self.assertIn("BuildFlow", self.call("GET", f"/api/actions/{aid}/draft")[1]["draft"])
        self.call("POST", f"/api/actions/{aid}/approve")
        with mock.patch("agents.operator.outreach.gmail.send_email", return_value={"message_id": "m1"}):
            self.assertTrue(self.call("POST", f"/api/actions/{aid}/send", {})[1]["sent"])
        self.assertEqual(self.conn.execute("SELECT stage FROM leads WHERE id=?", (lid,)).fetchone()[0], "contacted")
        self.assertEqual(self.conn.execute("SELECT count(*) FROM lead_touches WHERE lead_id=? AND channel='email'", (lid,)).fetchone()[0], 1)

    def test_csv_import_sets_venture(self):
        r = self.call("POST", "/api/leads/import", {"csv": "name,business,email\nA,Farm A,a@farm.co\n", "venture": "agriloop"})
        self.assertEqual(r[1]["added"], 1)
        self.assertEqual(self.conn.execute("SELECT venture FROM leads WHERE email='a@farm.co'").fetchone()[0], "agriloop")
        self.assertEqual(self.call("POST", "/api/leads/import", {"csv": "name,business,email\nA,B,c@d.co\n", "venture": "nope"})[0], 400)


class DraftTest(ChallengeBase):
    def test_drafts_state_the_offer_and_never_invent_claims(self):
        lid = self.lead()
        for ch in pitches.channels():
            d = self.call("POST", "/api/challenge/draft", {"lead_id": lid, "channel": ch})[1]["draft"]
            self.assertIn("$600", d)
            self.assertIn("2 months", d)
            self.assertIn("one-on-one", d)
            self.assertIn("[OWNER TO FILL]", d)
        email = self.call("POST", "/api/challenge/draft", {"lead_id": lid, "channel": "email"})[1]["draft"]
        self.assertTrue(email.startswith("Subject:"))
        for banned in ("testimonial", "customers love", "trusted by", "guarantee"):
            self.assertNotIn(banned, email.lower())

    def test_agriloop_without_price_asks_owner_to_fill_it(self):
        lid = self.lead(venture="agriloop", business="Green Farm")
        d = self.call("POST", "/api/challenge/draft", {"lead_id": lid, "channel": "whatsapp"})[1]["draft"]
        self.assertIn("AgriLoop", d)
        self.assertIn("(annual price)", d)

    def test_follow_up_and_bad_inputs(self):
        lid = self.lead()
        self.assertIn("following up", self.call("POST", "/api/challenge/draft", {"lead_id": lid, "channel": "whatsapp", "follow_up": True})[1]["draft"])
        self.assertEqual(self.call("POST", "/api/challenge/draft", {"lead_id": "nope"})[0], 400)
        self.assertEqual(self.call("POST", "/api/challenge/draft", {"lead_id": lid, "channel": "pigeon"})[0], 400)


class DealTest(ChallengeBase):
    def test_deal_is_pipeline_until_verified_then_counts_as_cash(self):
        lid = self.lead()
        d = self.call("POST", "/api/challenge/deal", {"lead_id": lid})[1]
        self.assertEqual(d["amount_usd"], 600)
        s = self.call("GET", "/api/challenge")[1]
        self.assertEqual((s["cash_usd"], s["deals_open"], s["pipeline_usd"], s["deals_paid"]), (0, 1, 600, 0))
        self.assertEqual(self.conn.execute("SELECT status FROM payments WHERE id=?", (d["payment_id"],)).fetchone()[0], "AWAITING_PAYMENT")
        self.assertEqual(self.call("POST", "/api/challenge/deal", {"lead_id": lid})[0], 400)  # no double deal
        self.verify(d["payment_id"], 600)
        s = self.call("GET", "/api/challenge")[1]
        self.assertEqual((s["cash_usd"], s["deals_paid"], s["deals_open"]), (600, 1, 0))
        self.assertEqual(self.conn.execute("SELECT stage FROM leads WHERE id=?", (lid,)).fetchone()[0], "paying")
        self.assertEqual(s["funnel"]["buildflow"]["paying"], 1)

    def test_agriloop_needs_an_amount_until_a_price_is_set(self):
        lid = self.lead(venture="agriloop")
        self.assertEqual(self.call("POST", "/api/challenge/deal", {"lead_id": lid})[0], 400)
        self.assertEqual(self.call("POST", "/api/challenge/deal", {"lead_id": lid, "amount": "250"})[1]["amount_usd"], 250)

    def test_cash_outside_the_window_is_not_challenge_cash(self):
        lid = self.lead()
        d = self.call("POST", "/api/challenge/deal", {"lead_id": lid})[1]
        self.verify(d["payment_id"], 600, when="2026-10-20T12:00:00+00:00")
        self.assertEqual(self.call("GET", "/api/challenge")[1]["cash_usd"], 0)

    def test_onboarding_status(self):
        d = self.call("POST", "/api/challenge/deal", {"lead_id": self.lead()})[1]
        did = self.conn.execute("SELECT id FROM deals").fetchone()[0]
        self.assertEqual(self.call("POST", "/api/challenge/onboarding", {"deal_id": did, "status": "done"})[0], 200)
        self.assertEqual(self.call("POST", "/api/challenge/onboarding", {"deal_id": did, "status": "x"})[0], 400)
        self.assertEqual(self.call("POST", "/api/challenge/onboarding", {"deal_id": "nope", "status": "done"})[0], 400)


class SummaryTest(ChallengeBase):
    def test_pace_math_and_phase(self):
        s = challenge.summary(self.conn, today=date(2026, 10, 30))
        self.assertEqual((s["state"], s["starts_in_days"], s["day"], s["total_days"]), ("before", 2, 0, 61))
        s = challenge.summary(self.conn, today=date(2026, 12, 1))  # day 31 of 61
        self.assertEqual((s["state"], s["day"], s["days_left"]), ("running", 31, 31))
        self.assertAlmostEqual(s["pace_target_usd"], 10000 * 31 / 61, places=1)
        self.assertLess(s["ahead_by_usd"], 0)
        self.assertEqual(s["deals_needed"], 17)  # 10,000 / 600 rounded up
        self.assertEqual(challenge.summary(self.conn, today=date(2027, 1, 2))["state"], "after")

    def test_due_list_orders_replies_first_and_skips_lost(self):
        a, b, c = self.lead(name="A", business="A"), self.lead(name="B", business="B"), self.lead(name="C", business="C")
        self.call("POST", "/api/challenge/touch", {"lead_id": b, "channel": "call", "direction": "in", "outcome": "replied"})
        self.call("POST", "/api/challenge/stage", {"lead_id": b, "stage": "replied", "next_days": 0})
        self.call("POST", "/api/challenge/stage", {"lead_id": c, "stage": "lost"})
        due = self.call("GET", "/api/challenge")[1]["due"]
        self.assertEqual([x["id"] for x in due], [b, a])

    def test_channel_learning_loop(self):
        a, b = self.lead(name="A"), self.lead(name="B")
        self.call("POST", "/api/challenge/touch", {"lead_id": a, "channel": "whatsapp", "outcome": "sent"})
        self.call("POST", "/api/challenge/touch", {"lead_id": b, "channel": "whatsapp", "outcome": "sent"})
        self.call("POST", "/api/challenge/touch", {"lead_id": a, "channel": "whatsapp", "direction": "in", "outcome": "replied"})
        w = [r for r in self.call("GET", "/api/challenge")[1]["by_channel"] if r["channel"] == "whatsapp"][0]
        self.assertEqual((w["sent"], w["replies"], w["paying"]), (2, 1, 0))

    def test_status_mode_no_longer_hardcoded_mock(self):
        self.assertEqual(self.call("GET", "/api/status")[1]["mode"], "LOCAL")


if __name__ == "__main__":
    unittest.main()
