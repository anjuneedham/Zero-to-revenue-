import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

import dashboard.app as dash
from agents.operator import run as operator
from agents.scout.run import run_scout
from agents.treasury import run as treasury
from core import actions, scheduler
from core.orchestrator import killswitch
from core.notifications.notify import SecretInNotification
from core.notifications.service import alert
from tests.authutil import session
from tests.dbutil import make_conn
from tests.unit.test_scout import good
from tests.unit.test_scout_db import Source

OWNER = "0x99024726df6db68c8a38f20e320f08e83d701ab6"
OTHER = "0x" + "11" * 20
TOKEN = "0x" + "cc" * 20
TX = "0x" + "ab" * 32
TX2 = "0x" + "cd" * 32
ENV = {"OWNER_SKILLS": "python", "OWNER_WALLET_ADDRESS": OWNER, "OWNER_WALLET_CHAIN_IDS": "56,8453", "MIN_CONFIRMATIONS": "12"}


class FakeChain:
    """Read-only RPC stand-in. Records every method so tests can prove nothing writes."""

    def __init__(self, receipt=None, tx=None, head=1000, balance=0, decimals=6):
        self.receipt, self.tx, self.head, self.balance, self.decimals, self.calls = receipt, tx, head, balance, decimals, []

    def __call__(self, chain, method, params):
        self.calls.append(method)
        return {"eth_getTransactionReceipt": self.receipt, "eth_getTransactionByHash": self.tx,
                "eth_blockNumber": hex(self.head), "eth_getBalance": hex(self.balance),
                "eth_call": hex(self.decimals)}[method]


def native_payment(value_wei=10**17, block=900, status=1, to=OWNER):
    return FakeChain(receipt={"status": hex(status), "blockNumber": hex(block), "logs": []},
                     tx={"to": to, "value": hex(value_wei)})


def token_payment(raw=25_000_000, to=OWNER):
    padded = "0x" + "0" * 24 + to[2:]
    log = {"address": TOKEN, "topics": [treasury.TRANSFER_TOPIC, "0x" + "0" * 24 + OTHER[2:], padded], "data": hex(raw)}
    return FakeChain(receipt={"status": "0x1", "blockNumber": hex(900), "logs": [log]}, tx={"to": TOKEN, "value": "0x0"})


class Base(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.env = mock.patch.dict(os.environ, ENV, clear=True)
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def one(self, sql, *a):
        return self.conn.execute(sql, a).fetchone()

    def qualified_task(self):
        run_scout(self.conn, [Source([good()])])
        r = operator.step(self.conn)
        self.assertEqual(r["result"], "waiting_for_user")
        return r["action_id"]

    def submitted_payment(self):
        aid = self.qualified_task()
        actions.approve(self.conn, aid, "owner")
        actions.mark_submitted(self.conn, aid, "owner", "https://github.com/acme/repo/pull/5")
        return self.one("select id from payments")["id"]


class OperatorTest(Base):
    def test_draft_created_owner_blocked_never_submitted(self):
        aid = self.qualified_task()
        t = self.one("select status, blocked_reason from tasks")
        self.assertEqual((t["status"], t["blocked_reason"]), ("WAITING_FOR_USER", "owner review and submission"))
        d = self.one("select content from deliverables")["content"]
        self.assertIn("DRAFT", d)
        self.assertIn("[OWNER TO FILL]", d)  # never invents experience
        self.assertEqual(self.one("select status from submissions")["status"], "DRAFT")
        a = self.one("select * from user_actions where action_id=?", aid)
        self.assertEqual((a["status"], a["verified_url"]), ("OPEN", "https://github.com/acme/repo/issues/1"))
        self.assertEqual(self.one("select status from opportunities")["status"], "IN_PROGRESS")
        self.assertEqual(self.one("select count(*) c from notifications where priority='HIGH'")["c"], 1)

    def test_nothing_to_do_and_kill_switch(self):
        self.assertEqual(operator.step(self.conn), {"ran": True, "task": None})
        killswitch.pause_all(self.conn, "owner")
        self.assertFalse(operator.step(self.conn)["ran"])

    def test_unqualified_opportunity_task_is_cancelled(self):
        run_scout(self.conn, [Source([good()])])
        self.conn.execute("update opportunities set status='REJECTED'")
        self.assertEqual(operator.step(self.conn)["result"], "cancelled")

    def test_non_https_source_gets_no_link(self):
        run_scout(self.conn, [Source([good(source_url="https://github.com/a/b/issues/3")])])
        self.conn.execute("update opportunities set source_url='http://github.com/a/b/issues/3'")
        aid = operator.step(self.conn)["action_id"]
        self.assertIsNone(self.one("select verified_url from user_actions where action_id=?", aid)["verified_url"])


class ActionsTest(Base):
    def test_approve_then_submit_creates_pending_payment(self):
        pid = self.submitted_payment()
        self.assertEqual(self.one("select status from payments where id=?", pid)["status"], "AWAITING_PAYMENT")
        self.assertEqual(self.one("select status from tasks")["status"], "AWAITING_PAYMENT")
        self.assertEqual(self.one("select status from opportunities")["status"], "AWAITING_PAYMENT")
        self.assertEqual(self.one("select status, proof from submissions")["status"], "SUBMITTED")
        self.assertIn("payment.pending", [r["event"] for r in self.conn.execute("select event from events")])

    def test_cannot_submit_without_approval_or_after_expiry_or_with_bad_proof(self):
        aid = self.qualified_task()
        with self.assertRaises(actions.ActionError):
            actions.mark_submitted(self.conn, aid, "owner")
        actions.approve(self.conn, aid, "owner")
        with self.assertRaises(actions.ActionError):
            actions.mark_submitted(self.conn, aid, "owner", "javascript:alert(1)")
        old = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        self.conn.execute("update submissions set approved_at=?", (old,))
        with self.assertRaises(actions.ActionError) as cm:
            actions.mark_submitted(self.conn, aid, "owner")
        self.assertIn("expired", str(cm.exception))

    def test_reject_cancels_everything_and_double_decisions_fail(self):
        aid = self.qualified_task()
        actions.reject(self.conn, aid, "owner")
        self.assertEqual(self.one("select status from tasks")["status"], "CANCELLED")
        self.assertEqual(self.one("select status from opportunities")["status"], "REJECTED")
        with self.assertRaises(actions.ActionError):
            actions.approve(self.conn, aid, "owner")


class TreasuryTest(Base):
    def test_native_payment_verified_end_to_end(self):
        pid = self.submitted_payment()
        chain = native_payment()
        r = treasury.verify_payment(self.conn, pid, 56, TX, chain)
        self.assertEqual((r["asset"], r["amount"], r["usd"]), ("BNB", "0.1", None))
        led = self.one("select status, chain_id, transaction_hash, usd_value, valuation_source from ledger_entries")
        self.assertEqual((led["status"], led["chain_id"]), ("VERIFIED", 56))
        self.assertIsNone(led["usd_value"])  # no price source -> not counted as USD revenue
        self.assertEqual(self.one("select status from payments")["status"], "PAYMENT_VERIFIED")
        self.assertEqual(self.one("select status from tasks")["status"], "COMPLETED")
        self.assertTrue(set(chain.calls) <= {"eth_getTransactionReceipt", "eth_getTransactionByHash", "eth_blockNumber", "eth_call"})

    def test_owner_confirmed_stablecoin_counts_as_usd_revenue(self):
        pid = self.submitted_payment()
        with mock.patch.dict(os.environ, {"STABLECOIN_CONTRACTS": f"8453:{TOKEN}"}):
            r = treasury.verify_payment(self.conn, pid, 8453, TX, token_payment())
        self.assertEqual((r["amount"], r["usd"]), ("25", 25.0))
        t, _ = session(self.conn)[0], None
        c, _, out = dash.handle("GET", "/api/status", f"Bearer {t}", self.conn, b"")
        self.assertEqual(json.loads(out)["verified_revenue_usd"], 25.0)

    def test_rejections(self):
        pid = self.submitted_payment()
        cases = [
            (56, "0x123", native_payment(), "64 hex"),                         # malformed hash
            (1, TX, native_payment(), "not a monitored chain"),                # wrong chain
            (56, TX, FakeChain(receipt=None), "pending"),                      # unknown tx
            (56, TX, native_payment(status=0), "failed"),                      # reverted
            (56, TX, native_payment(block=995), "confirmations"),              # not final
            (56, TX, native_payment(to=OTHER), "did not pay the owner"),       # fake payment claim
            (56, TX, token_payment(to=OTHER), "did not pay the owner"),
        ]
        for chain, tx, rpc, msg in cases:
            with self.assertRaises(treasury.VerifyError) as cm:
                treasury.verify_payment(self.conn, pid, chain, tx, rpc)
            self.assertIn(msg, str(cm.exception), msg)
        self.assertEqual(self.one("select count(*) c from ledger_entries")["c"], 0)

    def test_duplicate_transaction_cannot_be_counted_twice(self):
        pid = self.submitted_payment()
        treasury.verify_payment(self.conn, pid, 56, TX, native_payment())
        with self.assertRaises(treasury.VerifyError):
            treasury.verify_payment(self.conn, pid, 56, TX, native_payment())
        self.conn.execute("insert into payments(id, opportunity_id, status, created_at) values ('pay_x', (select id from opportunities), 'AWAITING_PAYMENT', 'now')")
        with self.assertRaises(treasury.VerifyError) as cm:
            treasury.verify_payment(self.conn, "pay_x", 56, TX.upper().replace("0X", "0x"), native_payment())
        self.assertIn("already recorded", str(cm.exception))

    def test_requires_wallet_config_and_respects_kill_switch(self):
        pid = self.submitted_payment()
        killswitch.pause_all(self.conn, "owner")
        with self.assertRaises(treasury.VerifyError):
            treasury.verify_payment(self.conn, pid, 56, TX2, native_payment())
        killswitch.resume(self.conn, "owner")
        with mock.patch.dict(os.environ, {"OWNER_WALLET_ADDRESS": ""}):
            with self.assertRaises(treasury.VerifyError):
                treasury.verify_payment(self.conn, pid, 56, TX2, native_payment())

    def test_balance_watch_alerts_on_changes(self):
        r = treasury.check_balances(self.conn, FakeChain(balance=0))
        self.assertEqual(set(r["balances"]), {"BNB Chain", "Base"})
        treasury.check_balances(self.conn, FakeChain(balance=10**18))
        treasury.check_balances(self.conn, FakeChain(balance=10**17))
        pr = [x["priority"] for x in self.conn.execute("select priority from notifications order by created_at")]
        self.assertEqual(pr.count("MEDIUM"), 2)  # one rise per chain
        self.assertEqual(pr.count("CRITICAL"), 2)  # one drop per chain
        with mock.patch.dict(os.environ, {"OWNER_WALLET_CHAIN_IDS": ""}):
            self.assertFalse(treasury.check_balances(self.conn, FakeChain())["ran"])


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
    def test_tick_runs_agents_reports_once_a_day_and_honours_kill_switch(self):
        r = scheduler.tick(self.conn, [Source([good()])], FakeChain())
        self.assertTrue(r["daily_report"])
        self.assertEqual(r["scout"]["new"], 1)
        self.assertEqual(r["operator"][0]["result"], "waiting_for_user")
        self.assertTrue(r["treasury"]["ran"])
        r2 = scheduler.tick(self.conn, [Source([good()])], FakeChain())
        self.assertNotIn("scout", r2)  # not due yet
        self.assertNotIn("daily_report", r2)
        self.assertEqual(self.one("select count(*) c from notifications where title like 'Zero-to-Revenue daily%'")["c"], 1)
        killswitch.pause_all(self.conn, "owner")
        self.assertFalse(scheduler.tick(self.conn, [], FakeChain())["ran"])

    def test_agent_failure_is_alerted_not_swallowed(self):
        def boom(*a):
            raise RuntimeError("rpc down")
        with mock.patch.object(scheduler, "check_balances", boom):
            r = scheduler.tick(self.conn, [], FakeChain())
        self.assertIn("rpc down", r["treasury"]["error"])
        self.assertEqual(self.one("select status from agents where name='treasury'")["status"], "error")
        self.assertEqual(self.one("select count(*) c from notifications where title='Treasury agent failed'")["c"], 1)

    def test_deadline_alert(self):
        soon = (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat()
        run_scout(self.conn, [Source([good(deadline=soon)])])
        scheduler.tick(self.conn, [], FakeChain())
        self.assertEqual(self.one("select count(*) c from notifications where title='Deadline under 24 hours'")["c"], 1)


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
            dash.SCOUT_SOURCES, dash.TREASURY_RPC = [Source([])], FakeChain()
            try:
                c, r = self.call("GET", "/api/cron", raw_auth="Bearer " + "s" * 32)
            finally:
                dash.SCOUT_SOURCES = dash.TREASURY_RPC = None
            self.assertEqual((c, r["ran"]), (200, True))

    def test_full_owner_loop_over_http(self):
        t, _, _ = session(self.conn)
        for p in ("/api/operator/run", "/api/treasury/run", "/api/actions/x/approve", "/api/payments/x/verify"):
            self.assertEqual(self.call("POST", p)[0], 401)
        dash.SCOUT_SOURCES, dash.TREASURY_RPC = [Source([good()])], native_payment()
        try:
            self.call("POST", "/api/scout/run", t)
            self.assertEqual(self.call("POST", "/api/operator/run", t)[1]["steps"][0]["result"], "waiting_for_user")
            aid = self.call("GET", "/api/status", t)[1]["open_user_actions"][0]["action_id"]
            self.assertIn("DRAFT", self.call("GET", f"/api/actions/{aid}/draft", t)[1]["draft"])
            self.assertEqual(self.call("POST", f"/api/actions/{aid}/submitted", t, {"proof_url": ""})[0], 409)
            self.assertEqual(self.call("POST", f"/api/actions/{aid}/approve", t, {})[0], 200)
            self.assertEqual(self.call("POST", f"/api/actions/{aid}/submitted", t, {"proof_url": "https://github.com/acme/repo/pull/1"})[0], 200)
            pid = self.call("GET", "/api/payments", t)[1]["payments"][0]["id"]
            self.assertEqual(self.call("POST", f"/api/payments/{pid}/verify", t, {"chain_id": "56", "tx_hash": "nope"})[0], 422)
            c, r = self.call("POST", f"/api/payments/{pid}/verify", t, {"chain_id": "56", "tx_hash": TX})
            self.assertEqual((c, r["verified"]), (200, True))
            self.assertEqual(self.call("GET", "/api/payments", t)[1]["payments"][0]["status"], "PAYMENT_VERIFIED")
            self.assertTrue(self.call("GET", "/api/notifications", t)[1]["notifications"])
            self.assertEqual(self.call("POST", "/api/actions/../../x/approve", t)[0], 404)
        finally:
            dash.SCOUT_SOURCES = dash.TREASURY_RPC = None


if __name__ == "__main__":
    unittest.main()
