import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

import dashboard.app as dash
from core import payments, scheduler
from core.orchestrator import killswitch
from core.notifications.notify import SecretInNotification
from core.notifications.service import alert
from tests.authutil import session
from tests.dbutil import make_conn

ENV: dict = {}


class Base(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.env = mock.patch.dict(os.environ, ENV, clear=True)
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def one(self, sql, *a):
        return self.conn.execute(sql, a).fetchone()

    def submitted_payment(self):
        from dashboard import api_data
        return api_data.create_manual_payment(self.conn, "owner", "Client work", "600")["payment_id"]


class ManualPaymentTest(Base):
    def test_creates_an_anchor_opportunity_and_an_awaiting_payment_row(self):
        from dashboard import api_data
        r = api_data.create_manual_payment(self.conn, "owner", "BuildFlow subscription - Acme Co", "49.99", "USD", "Acme Co")
        self.assertTrue(r["payment_id"].startswith("pay_"))
        opp = self.one("select title, status, approval_required, organization from opportunities where id=?", r["opportunity_id"])
        self.assertEqual((opp["title"], opp["status"], opp["approval_required"], opp["organization"]),
                         ("BuildFlow subscription - Acme Co", "APPROVED", 0, "Acme Co"))
        pay = self.one("select opportunity_id, expected_amount, asset, status from payments where id=?", r["payment_id"])
        self.assertEqual((pay["opportunity_id"], float(pay["expected_amount"]), pay["asset"], pay["status"]),
                         (r["opportunity_id"], 49.99, "USD", "AWAITING_PAYMENT"))

    def test_then_works_with_the_existing_paypal_flow(self):
        from dashboard import api_data
        r = api_data.create_manual_payment(self.conn, "owner", "Direct client work", "600")
        with mock.patch("core.payments.paypal.create_payment_request",
                        return_value={"order_id": "ORDERX", "approval_link": "https://x", "status": "CREATED"}):
            payments.request_paypal_payment(self.conn, r["payment_id"])
        completed = {"status": "COMPLETED", "purchase_units": [{"payments": {"captures": [{"amount": {"value": "600", "currency_code": "USD"}}]}}]}
        with mock.patch("core.payments.paypal.get_order", return_value=completed):
            v = payments.verify_paypal_payment(self.conn, r["payment_id"])
        self.assertEqual(v["amount"], "600")

    def test_rejects_bad_input(self):
        from dashboard import api_data
        for title, amount in [("", "10"), ("ok", "0"), ("ok", "-5"), ("ok", "not-a-number")]:
            with self.assertRaises(ValueError):
                api_data.create_manual_payment(self.conn, "owner", title, amount)

    def test_api_route(self):
        tok, _, _ = session(self.conn)
        c, _, out = dash.handle("POST", "/api/payments/manual", f"Bearer {tok}", self.conn,
                                json.dumps({"title": "Test", "amount": "25"}).encode())
        self.assertEqual(c, 200)
        self.assertEqual(dash.handle("POST", "/api/payments/manual", None, self.conn, b"{}")[0], 401)
        c, _, out = dash.handle("POST", "/api/payments/manual", f"Bearer {tok}", self.conn, json.dumps({"title": "", "amount": "5"}).encode())
        self.assertEqual(c, 400)


class PayPalPaymentsTest(Base):
    def test_request_then_verify_end_to_end(self):
        pid = self.submitted_payment()
        self.conn.execute("update payments set expected_amount=600 where id=?", (pid,))
        with mock.patch("core.payments.paypal.create_payment_request",
                        return_value={"order_id": "ORDER1", "approval_link": "https://x/approve", "status": "CREATED"}) as created:
            req = payments.request_paypal_payment(self.conn, pid)
        self.assertEqual(req["order_id"], "ORDER1")
        created.assert_called_once_with("600.00", "USD", f"Payment for {self.one('select opportunity_id from payments')[0]}", pid)
        row = self.one("select tx_hash, chain_id, asset from payments")
        self.assertEqual((row["tx_hash"], row["chain_id"], row["asset"]), ("ORDER1", None, "USD"))
        completed = {"status": "COMPLETED", "purchase_units": [{"payments": {"captures": [{"amount": {"value": "600", "currency_code": "USD"}}]}}]}
        with mock.patch("core.payments.paypal.get_order", return_value=completed):
            r = payments.verify_paypal_payment(self.conn, pid)
        self.assertEqual((r["amount"], r["asset"], r["usd"]), ("600", "USD", 600.0))
        self.assertEqual(self.one("select status from payments")["status"], "PAYMENT_VERIFIED")
        led = self.one("select chain_id, transaction_hash, usd_value from ledger_entries")
        self.assertEqual((led["chain_id"], led["transaction_hash"], led["usd_value"]), (None, "ORDER1", 600.0))

    def test_approved_but_not_captured_gets_captured_automatically(self):
        pid = self.submitted_payment()
        self.conn.execute("update payments set expected_amount=100, tx_hash='ORDER2' where id=?", (pid,))
        with mock.patch("core.payments.paypal.get_order", return_value={"status": "APPROVED"}), \
             mock.patch("core.payments.paypal.capture_order", return_value={
                 "status": "COMPLETED", "purchase_units": [{"payments": {"captures": [{"amount": {"value": "100", "currency_code": "USD"}}]}}]}) as cap:
            r = payments.verify_paypal_payment(self.conn, pid)
        cap.assert_called_once_with("ORDER2")
        self.assertEqual(r["amount"], "100")

    def test_not_yet_paid_is_rejected_and_nothing_recorded(self):
        pid = self.submitted_payment()
        self.conn.execute("update payments set tx_hash='ORDER3' where id=?", (pid,))
        with mock.patch("core.payments.paypal.get_order", return_value={"status": "CREATED"}):
            with self.assertRaises(payments.VerifyError) as cm:
                payments.verify_paypal_payment(self.conn, pid)
        self.assertIn("not yet paid", str(cm.exception))
        self.assertEqual(self.one("select count(*) c from ledger_entries")["c"], 0)

    def test_duplicate_order_cannot_be_counted_twice(self):
        pid = self.submitted_payment()
        self.conn.execute("update payments set expected_amount=50, tx_hash='ORDER4' where id=?", (pid,))
        completed = {"status": "COMPLETED", "purchase_units": [{"payments": {"captures": [{"amount": {"value": "50", "currency_code": "USD"}}]}}]}
        with mock.patch("core.payments.paypal.get_order", return_value=completed):
            payments.verify_paypal_payment(self.conn, pid)
        self.conn.execute("insert into payments(id, opportunity_id, status, tx_hash, created_at) values "
                          "('pay_dup', (select id from opportunities), 'AWAITING_PAYMENT', 'ORDER4', 'now')")
        with mock.patch("core.payments.paypal.get_order", return_value=completed):
            with self.assertRaises(payments.VerifyError) as cm:
                payments.verify_paypal_payment(self.conn, "pay_dup")
        self.assertIn("already recorded", str(cm.exception))

    def test_request_rejects_without_amount_or_when_already_verified(self):
        pid = self.submitted_payment()
        self.conn.execute("update payments set expected_amount=NULL where id=?", (pid,))
        with self.assertRaises(payments.VerifyError):
            payments.request_paypal_payment(self.conn, pid)
        self.conn.execute("update payments set status='PAYMENT_VERIFIED' where id=?", (pid,))
        with self.assertRaises(payments.VerifyError):
            payments.request_paypal_payment(self.conn, pid)

    def test_get_approval_link_round_trips_through_the_api(self):
        pid = self.submitted_payment()
        self.conn.execute("update payments set expected_amount=600, tx_hash='ORDER9' where id=?", (pid,))
        with mock.patch("core.payments.paypal.get_order",
                        return_value={"status": "CREATED", "links": [{"rel": "self", "href": "https://x/self"},
                                                                      {"rel": "approve", "href": "https://x/approve/ORDER9"}]}):
            r = payments.get_paypal_approval_link(self.conn, pid)
            self.assertEqual(r["approval_link"], "https://x/approve/ORDER9")
            tok, _, _ = session(self.conn)
            c, _, out = dash.handle("GET", f"/api/payments/{pid}/paypal/link", f"Bearer {tok}", self.conn, b"")
        self.assertEqual((c, json.loads(out)["approval_link"]), (200, "https://x/approve/ORDER9"))

    def test_get_approval_link_errors_once_no_longer_available(self):
        pid = self.submitted_payment()
        self.conn.execute("update payments set tx_hash='ORDER10' where id=?", (pid,))
        with mock.patch("core.payments.paypal.get_order", return_value={"status": "COMPLETED", "links": []}):
            with self.assertRaises(payments.VerifyError) as cm:
                payments.get_paypal_approval_link(self.conn, pid)
        self.assertIn("no approval link available", str(cm.exception))

    def test_get_approval_link_requires_an_order_id(self):
        pid = self.submitted_payment()
        with self.assertRaises(payments.VerifyError) as cm:
            payments.get_paypal_approval_link(self.conn, pid)
        self.assertIn("request a payment first", str(cm.exception))

    def test_verify_requires_an_order_id(self):
        pid = self.submitted_payment()
        with self.assertRaises(payments.VerifyError) as cm:
            payments.verify_paypal_payment(self.conn, pid)
        self.assertIn("request a payment first", str(cm.exception))

    def test_respects_kill_switch(self):
        pid = self.submitted_payment()
        killswitch.pause_all(self.conn, "owner")
        with self.assertRaises(payments.VerifyError):
            payments.request_paypal_payment(self.conn, pid)
        with self.assertRaises(payments.VerifyError):
            payments.verify_paypal_payment(self.conn, pid, "ORDER5")


class NotificationsTest(Base):
    def test_low_is_stored_only_dedupe_and_no_secrets(self):
        class Spy:
            channel, sent = "whatsapp", []

            def send(self, *a):
                self.sent.append(a)
        spy = Spy()
        self.assertTrue(alert(self.conn, "HIGH", "k1", "Action required", "x", backend_override=spy))
        self.assertFalse(alert(self.conn, "HIGH", "k1", "Action required", "x", backend_override=spy))
        self.assertEqual(len(spy.sent), 1)
        alert(self.conn, "LOW", "k2", "routine", "x")
        self.assertEqual(self.one("select channel from notifications where dedupe_key='k2'")["channel"], "dashboard")
        with self.assertRaises(SecretInNotification):
            alert(self.conn, "HIGH", "k3", "x", "seed phrase: abc def")

    def test_twilio_selected_only_when_fully_configured(self):
        from core.notifications import service
        self.assertEqual(service.backend().channel, "dashboard")
        with mock.patch.dict(os.environ, {"TWILIO_ACCOUNT_SID": "AC1", "TWILIO_AUTH_TOKEN": "t", "TWILIO_WHATSAPP_FROM": "+1", "WHATSAPP_TO": "+2"}):
            self.assertEqual(service.backend().channel, "whatsapp")


class SchedulerTest(Base):
    def test_tick_reports_once_a_day_and_honours_kill_switch(self):
        r = scheduler.tick(self.conn)
        self.assertTrue(r["daily_report"])
        r2 = scheduler.tick(self.conn)
        self.assertNotIn("daily_report", r2)
        self.assertEqual(self.one("select count(*) c from notifications where title like 'Founder OS daily%'")["c"], 1)
        killswitch.pause_all(self.conn, "owner")
        self.assertFalse(scheduler.tick(self.conn)["ran"])

    def test_job_failure_is_alerted_not_swallowed(self):
        def boom(*a):
            raise RuntimeError("report down")
        from datetime import date
        with mock.patch.object(scheduler.weekly, "report", boom), \
             mock.patch.object(scheduler, "datetime", wraps=datetime) as dt:
            dt.now.return_value = datetime(2026, 11, 1, 9, tzinfo=timezone.utc)  # a Sunday
            r = scheduler.tick(self.conn)
        self.assertIn("report down", r["weekly_report"]["error"])
        self.assertEqual(self.one("select count(*) c from notifications where title='Scheduled job failed: weekly_report'")["c"], 1)


class ApiTest(Base):
    def call(self, method, path, token=None, body=None, raw_auth=None):
        auth = raw_auth if raw_auth is not None else (f"Bearer {token}" if token else None)
        c, _, out = dash.handle(method, path, auth, self.conn, json.dumps(body).encode() if body is not None else b"")
        return c, json.loads(out)

    def test_cron_requires_secret(self):
        self.assertEqual(self.call("GET", "/api/cron")[0], 401)
        with mock.patch.dict(os.environ, {"CRON_SECRET": "short"}):
            self.assertEqual(self.call("GET", "/api/cron", raw_auth="Bearer short")[0], 401)
        with mock.patch.dict(os.environ, {"CRON_SECRET": "s" * 32}):
            self.assertEqual(self.call("GET", "/api/cron", raw_auth="Bearer wrong")[0], 401)
            c, r = self.call("GET", "/api/cron", raw_auth="Bearer " + "s" * 32)
            self.assertEqual((c, r["ran"]), (200, True))

    def test_removed_agent_routes_are_gone(self):
        t, _, _ = session(self.conn)
        for m, p in (("POST", "/api/scout/run"), ("POST", "/api/operator/run"), ("POST", "/api/treasury/run"), ("GET", "/api/opportunities"),
                     ("POST", "/api/actions/x/approve"), ("POST", "/api/payments/x/verify"), ("GET", "/api/ventures")):
            self.assertEqual(self.call(m, p, t)[0], 404, p)

    def test_payment_loop_over_http(self):
        t, _, _ = session(self.conn)
        for p in ("/api/payments/manual", "/api/payments/x/paypal/request", "/api/payments/x/paypal/verify"):
            self.assertEqual(self.call("POST", p)[0], 401)
        pid = self.call("POST", "/api/payments/manual", t, {"title": "Annual plan", "amount": "500"})[1]["payment_id"]
        with mock.patch("core.payments.paypal.create_payment_request",
                        return_value={"order_id": "ORD9", "approval_link": "https://x/a", "status": "CREATED"}):
            self.assertEqual(self.call("POST", f"/api/payments/{pid}/paypal/request", t, {})[1]["order_id"], "ORD9")
        completed = {"status": "COMPLETED", "purchase_units": [{"payments": {"captures": [{"amount": {"value": "500", "currency_code": "USD"}}]}}]}
        with mock.patch("core.payments.paypal.get_order", return_value=completed):
            c, r = self.call("POST", f"/api/payments/{pid}/paypal/verify", t, {})
        self.assertEqual((c, r["verified"]), (200, True))
        self.assertEqual(self.call("GET", "/api/payments", t)[1]["payments"][0]["status"], "PAYMENT_VERIFIED")
        self.assertEqual(self.call("GET", "/api/payments/overview", t)[1]["revenue_usd"], 500.0)
        self.assertTrue(self.call("GET", "/api/notifications", t)[1]["notifications"])


if __name__ == "__main__":
    unittest.main()
