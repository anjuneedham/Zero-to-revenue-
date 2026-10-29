import unittest


from core import db
from core.notifications.notify import SecretInNotification, notify
from core.orchestrator import killswitch

OWNER = "owner"


from tests.dbutil import make_conn  # noqa: E402  (isolated Postgres schema per call)


class DbTest(unittest.TestCase):
    def test_migrate_is_idempotent_and_has_all_tables(self):
        c = make_conn()
        self.assertEqual(db.migrate(c), [])
        names = {r[0] for r in c.execute(
            "select table_name from information_schema.tables where table_schema=current_schema()")}
        for t in "users settings agents agent_runs opportunities tasks task_events user_actions deliverables "\
                 "submissions payments wallets transactions ledger_entries notifications audit_events".split():
            self.assertIn(t, names)

    def test_audit_is_append_only(self):
        c = make_conn()
        killswitch.pause_all(c, "test")
        with self.assertRaises(Exception):
            c.execute("DELETE FROM audit_events")
        with self.assertRaises(Exception):
            c.execute("UPDATE audit_events SET actor='x'")

    def test_wallet_cannot_be_non_read_only(self):
        c = make_conn()
        with self.assertRaises(Exception):
            c.execute("INSERT INTO wallets(id,address,mode) VALUES ('w','0x1','READ_WRITE')")

    def test_duplicate_chain_tx_rejected(self):
        c = make_conn()
        c.execute("INSERT INTO wallets(id,address,chain_id) VALUES ('w','0x1',56)")
        q = "INSERT INTO transactions(id,wallet_id,chain_id,tx_hash,seen_at) VALUES (?,?,?,?,'t')"
        c.execute(q, ("a", "w", 56, "0xabc"))
        with self.assertRaises(Exception):
            c.execute(q, ("b", "w", 56, "0xabc"))
        c.execute(q, ("c", "w", 1, "0xabc"))  # same hash on another chain is distinct


class NotifyTest(unittest.TestCase):
    def test_dedupe_and_secret_refusal_and_failure_recorded(self):
        class Spy:
            sent = []

            def send(self, *a):
                self.sent.append(a)
        c, w = make_conn(), Spy()
        self.assertTrue(notify(c, w, "+1", "HIGH", "k", "Action required", "approve"))
        self.assertFalse(notify(c, w, "+1", "HIGH", "k", "Action required", "approve"))
        self.assertEqual(len(w.sent), 1)
        with self.assertRaises(SecretInNotification):
            notify(c, w, "+1", "LOW", "k2", "x", "private key: abc")

        class Boom:
            def send(self, *a): raise RuntimeError("down")
        self.assertFalse(notify(c, Boom(), "+1", "LOW", "k3", "t", "b"))
        self.assertEqual(c.execute("select status from notifications where dedupe_key='k3'").fetchone()[0], "FAILED")


if __name__ == "__main__":
    unittest.main()
