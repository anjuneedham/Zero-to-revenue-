import json
import os
import unittest
from datetime import date
from unittest import mock

import dashboard.app as dash
from core import challenge, pitches
from core.db import now
from tests.authutil import session
from tests.dbutil import make_conn
from tests.unit.test_payments import ENV


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
        """Stand-in for payment verification (PayPal verification is covered in test_paypal and test_payments)."""
        eid = "led_" + payment_id
        self.conn.execute("INSERT INTO ledger_entries(entry_id,date,type,asset,amount,usd_value,status) VALUES (?,?,'receipt','USD',?,?,'VERIFIED')",
                          (eid, when, str(usd), usd))
        self.conn.execute("UPDATE payments SET status='PAYMENT_VERIFIED', verified_at=?, ledger_entry_id=? WHERE id=?", (when, eid, payment_id))


class ConfigTest(ChallengeBase):
    def test_defaults_match_the_challenge(self):
        c = challenge.get_config(self.conn)
        self.assertEqual((c["start"], c["end"], c["target_usd"]), ("2026-11-01", "2026-12-31", 10000))
        self.assertEqual(c["offers"]["buildflow"]["free_months"], 2)
        by = {p["key"]: p["annual_usd"] for v in challenge.VENTURES for p in challenge.plans(c, v)}
        # 12 months for the price of 10: $50 -> $500, Buyer Basic $10 -> $100, Farmer Premium $20 -> $200
        self.assertEqual(by, {"standard": 500, "buyer_basic": 100, "farmer_premium": 200})

    def test_save_and_validate(self):
        c = self.call("POST", "/api/challenge/config", {"target_usd": 12000, "offers": {"agriloop": {"free_months": 2, "tiers": {"farmer_premium": "25"}}}})[1]
        self.assertEqual((c["target_usd"], c["offers"]["agriloop"]["tiers"]["farmer_premium"]["monthly_usd"]), (12000, 25))
        self.assertEqual(challenge.get_config(self.conn)["target_usd"], 12000)
        for bad in ({"target_usd": -1}, {"start": "nope"}, {"start": "2027-01-01", "end": "2026-12-31"},
                    {"offers": {"buildflow": {"tiers": {"standard": "x"}}}}, {"offers": {"buildflow": {"free_months": 99}}},
                    {"offers": {"agriloop": {"tiers": {"nope": "5"}}}}):
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

    def test_decline_stops_drafting(self):
        lid = self.lead(email="x@y.co")
        self.assertEqual(self.call("POST", "/api/challenge/draft", {"lead_id": lid, "channel": "email"})[0], 200)
        self.call("POST", "/api/challenge/touch", {"lead_id": lid, "channel": "email", "outcome": "declined"})
        row = self.conn.execute("SELECT stage, status FROM leads WHERE id=?", (lid,)).fetchone()
        self.assertEqual((row["stage"], row["status"]), ("lost", "SKIPPED"))
        c, r = self.call("POST", "/api/challenge/draft", {"lead_id": lid, "channel": "email"})
        self.assertEqual(c, 400)
        self.assertIn("declined", r["error"])

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
            self.assertIn("$500", d)
            self.assertIn("12 months for the price of 10", d)
            self.assertIn("one-on-one", d)
            self.assertIn("[OWNER TO FILL]", d)
        email = self.call("POST", "/api/challenge/draft", {"lead_id": lid, "channel": "email"})[1]["draft"]
        self.assertTrue(email.startswith("Subject:"))
        for banned in ("testimonial", "customers love", "trusted by", "guarantee"):
            self.assertNotIn(banned, email.lower())

    def test_agriloop_drafts_show_the_right_plan_for_the_segment(self):
        farmer = self.lead(venture="agriloop", business="Green Farm", segment="Farmer")
        buyer = self.lead(venture="agriloop", business="Hotel X", segment="buyer - hotel")
        other = self.lead(venture="agriloop", business="Who", segment="")
        d = lambda lid: self.call("POST", "/api/challenge/draft", {"lead_id": lid, "channel": "whatsapp"})[1]["draft"]
        self.assertIn("Farmer Premium $200/year", d(farmer))
        self.assertNotIn("Buyer Basic", d(farmer))
        self.assertIn("Buyer Basic $100/year", d(buyer))
        self.assertNotIn("Farmer Premium", d(buyer))
        self.assertTrue("Buyer Basic $100/year" in d(other) and "Farmer Premium $200/year" in d(other))

    def test_follow_up_and_bad_inputs(self):
        lid = self.lead()
        self.assertIn("following up", self.call("POST", "/api/challenge/draft", {"lead_id": lid, "channel": "whatsapp", "follow_up": True})[1]["draft"])
        self.assertEqual(self.call("POST", "/api/challenge/draft", {"lead_id": "nope"})[0], 400)
        self.assertEqual(self.call("POST", "/api/challenge/draft", {"lead_id": lid, "channel": "pigeon"})[0], 400)


class DealTest(ChallengeBase):
    def test_deal_is_pipeline_until_verified_then_counts_as_cash(self):
        lid = self.lead()
        d = self.call("POST", "/api/challenge/deal", {"lead_id": lid})[1]
        self.assertEqual(d["amount_usd"], 500)
        s = self.call("GET", "/api/challenge")[1]
        self.assertEqual((s["cash_usd"], s["deals_open"], s["pipeline_usd"], s["deals_paid"]), (0, 1, 500, 0))
        self.assertEqual(self.conn.execute("SELECT status FROM payments WHERE id=?", (d["payment_id"],)).fetchone()[0], "AWAITING_PAYMENT")
        self.assertEqual(self.call("POST", "/api/challenge/deal", {"lead_id": lid})[0], 400)  # no double deal
        self.verify(d["payment_id"], 500)
        s = self.call("GET", "/api/challenge")[1]
        self.assertEqual((s["cash_usd"], s["deals_paid"], s["deals_open"]), (500, 1, 0))
        self.assertEqual(self.conn.execute("SELECT stage FROM leads WHERE id=?", (lid,)).fetchone()[0], "paying")
        self.assertEqual(s["funnel"]["buildflow"]["paying"], 1)

    def test_paypal_message_is_one_tap_and_idempotent(self):
        lid = self.lead(name="Tia Brown")
        d = self.call("POST", "/api/challenge/deal", {"lead_id": lid})[1]
        link = "https://paypal.example/approve/ORD1"
        with mock.patch("integrations.paypal.create_payment_request",
                        return_value={"order_id": "ORD1", "approval_link": link, "status": "CREATED"}) as create, \
                mock.patch("integrations.paypal.get_order", return_value={"status": "CREATED", "links": [{"rel": "approve", "href": link}]}):
            c, r = self.call("POST", "/api/challenge/paypal-message", {"deal_id": d["deal_id"]})
            self.assertEqual(c, 200)
            self.assertIn(link, r["message"])
            self.assertIn("$500.00", r["message"])
            self.assertTrue(r["message"].startswith("Hi Tia,"))
            self.assertEqual(r["warning"], "")
            c, r2 = self.call("POST", "/api/challenge/paypal-message", {"deal_id": d["deal_id"]})  # second tap reuses the order
            self.assertEqual((c, r2["approval_link"]), (200, link))
            self.assertEqual(create.call_count, 1)
        self.assertEqual(self.conn.execute("SELECT tx_hash FROM payments WHERE id=?", (d["payment_id"],)).fetchone()[0], "ORD1")
        # still pipeline: a link is not cash
        self.assertEqual(self.call("GET", "/api/challenge")[1]["cash_usd"], 0)

    def test_paypal_message_refuses_paid_unknown_and_flags_agriloop(self):
        self.assertEqual(self.call("POST", "/api/challenge/paypal-message", {"deal_id": "nope"})[0], 400)
        lid = self.lead()
        d = self.call("POST", "/api/challenge/deal", {"lead_id": lid})[1]
        self.verify(d["payment_id"], 500)
        self.assertEqual(self.call("POST", "/api/challenge/paypal-message", {"deal_id": d["deal_id"]})[0], 400)
        ag = self.lead(venture="agriloop", segment="farmer", name="Ann", phone="876-555-0111")
        d2 = self.call("POST", "/api/challenge/deal", {"lead_id": ag})[1]
        link = "https://paypal.example/approve/ORD2"
        with mock.patch("integrations.paypal.create_payment_request", return_value={"order_id": "ORD2", "approval_link": link, "status": "CREATED"}):
            r = self.call("POST", "/api/challenge/paypal-message", {"deal_id": d2["deal_id"]})[1]
        self.assertIn("not confirmed live", r["warning"])
        self.assertIn("Farmer Premium", r["message"])

    def test_paypal_message_requires_login(self):
        c, _, _ = dash.handle("POST", "/api/challenge/paypal-message", "", self.conn, b"{}")
        self.assertEqual(c, 401)

    def test_agriloop_plans_and_prices(self):
        none = self.lead(venture="agriloop", segment="")
        r = self.call("POST", "/api/challenge/deal", {"lead_id": none})
        self.assertEqual(r[0], 400)
        self.assertIn("Farmer Premium", r[1]["error"])
        self.assertEqual(self.call("POST", "/api/challenge/deal", {"lead_id": none, "plan": "bogus"})[0], 400)
        self.assertEqual(self.call("POST", "/api/challenge/deal", {"lead_id": none, "plan": "buyer_basic"})[1]["amount_usd"], 100)
        farm = self.lead(venture="agriloop", segment="farmer")  # segment implies the plan
        d = self.call("POST", "/api/challenge/deal", {"lead_id": farm})[1]
        self.assertEqual((d["amount_usd"], d["plan"]), (200, "Farmer Premium"))
        self.assertEqual(self.conn.execute("SELECT plan, free_months FROM deals WHERE id=?", (d["deal_id"],)).fetchone().values().__iter__().__next__(), "farmer_premium")

    def test_cash_outside_the_window_is_not_challenge_cash(self):
        lid = self.lead()
        d = self.call("POST", "/api/challenge/deal", {"lead_id": lid})[1]
        self.verify(d["payment_id"], 500, when="2026-10-20T12:00:00+00:00")
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
        self.assertEqual(s["deals_needed"], 20)  # 10,000 / $500 BuildFlow annual
        need = {p["key"]: p["deals_needed"] for p in s["plans"]}
        self.assertEqual(need, {"standard": 20, "buyer_basic": 100, "farmer_premium": 50})
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
