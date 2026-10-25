import os
import unittest
from unittest import mock

from core.auth import owner_login as ol
from tests import authutil
from tests.authutil import PASSWORD, SETUP_TOKEN, code, provision
from tests.dbutil import make_conn


class TotpAndPasswordTest(unittest.TestCase):
    def test_rfc6238_vector(self):
        import base64
        secret = base64.b32encode(b"12345678901234567890").decode()
        self.assertEqual(ol.totp_at(secret, 59 // 30, digits=8), "94287082")  # RFC 6238 appendix B

    def test_password_hash_roundtrip(self):
        h = ol.hash_password("a long enough password")
        self.assertTrue(ol.verify_password("a long enough password", h))
        self.assertFalse(ol.verify_password("wrong", h))
        self.assertNotIn("a long enough password", h)
        self.assertFalse(ol.verify_password("x", "garbage"))


class SetupTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()

    def test_setup_disabled_without_token_env(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OWNER_SETUP_TOKEN", None)
            with self.assertRaises(ol.SetupDisabled):
                ol.begin_setup(self.conn, "x" * 24, PASSWORD)

    def test_short_setup_token_env_is_treated_as_disabled(self):
        with mock.patch.dict(os.environ, {"OWNER_SETUP_TOKEN": "short"}):
            with self.assertRaises(ol.SetupDisabled):
                ol.begin_setup(self.conn, "short", PASSWORD)

    def test_wrong_setup_token_and_weak_password_rejected(self):
        with mock.patch.dict(os.environ, {"OWNER_SETUP_TOKEN": SETUP_TOKEN}):
            with self.assertRaises(ol.AuthError):
                ol.begin_setup(self.conn, "w" * 24, PASSWORD)
            with self.assertRaises(ValueError):
                ol.begin_setup(self.conn, SETUP_TOKEN, "short")

    def test_setup_requires_working_authenticator_and_closes_forever(self):
        with mock.patch.dict(os.environ, {"OWNER_SETUP_TOKEN": SETUP_TOKEN}):
            secret = ol.begin_setup(self.conn, SETUP_TOKEN, PASSWORD)["secret"]
            with self.assertRaises(ol.AuthError):
                ol.confirm_setup(self.conn, SETUP_TOKEN, "000000")
            self.assertFalse(ol.setup_complete(self.conn))
            with self.assertRaises(ol.AuthError):  # cannot log in with an unconfirmed setup
                ol.login(self.conn, PASSWORD, code(secret, 0))
            codes = ol.confirm_setup(self.conn, SETUP_TOKEN, code(secret, -1))
            self.assertEqual(len(codes), 8)
            self.assertTrue(ol.setup_complete(self.conn))
            with self.assertRaises(ol.SetupClosed):  # even with the correct token
                ol.begin_setup(self.conn, SETUP_TOKEN, "another long password")
            with self.assertRaises(ol.SetupClosed):
                ol.confirm_setup(self.conn, SETUP_TOKEN, code(secret, 0))

    def test_setup_bruteforce_is_locked_out(self):
        with mock.patch.dict(os.environ, {"OWNER_SETUP_TOKEN": SETUP_TOKEN}):
            for _ in range(ol.MAX_FAILURES):
                with self.assertRaises(ol.AuthError):
                    ol.begin_setup(self.conn, "w" * 24, PASSWORD)
            with self.assertRaises(ol.LockedOut):  # now even the right token is refused
                ol.begin_setup(self.conn, SETUP_TOKEN, PASSWORD)


class LoginTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.secret, self.codes = provision(self.conn)

    def test_login_success_and_session(self):
        r = ol.login(self.conn, PASSWORD, code(self.secret, 0))
        self.assertEqual(ol.verify_session(self.conn, r["token"]), "owner")
        stored = self.conn.execute("select token_hash from sessions").fetchone()[0]
        self.assertNotEqual(stored, r["token"])  # only a hash is stored

    def test_each_factor_required_and_errors_are_generic(self):
        msgs = set()
        for pw, c in [("wrong password here", code(self.secret, 0)), (PASSWORD, "000000"), ("x", "y")]:
            with self.assertRaises(ol.AuthError) as cm:
                ol.login(self.conn, pw, c)
            msgs.add(str(cm.exception))
        self.assertEqual(msgs, {"invalid credentials"})

    def test_totp_code_cannot_be_replayed(self):
        c = code(self.secret, 0)
        ol.login(self.conn, PASSWORD, c)
        with self.assertRaises(ol.AuthError):
            ol.login(self.conn, PASSWORD, c)
        with self.assertRaises(ol.AuthError):  # an older step is also dead
            ol.login(self.conn, PASSWORD, code(self.secret, -1))
        ol.login(self.conn, PASSWORD, code(self.secret, 1))  # a newer step is fine

    def test_recovery_code_is_single_use(self):
        ol.login(self.conn, PASSWORD, self.codes[0])
        with self.assertRaises(ol.AuthError):
            ol.login(self.conn, PASSWORD, self.codes[0])
        ol.login(self.conn, PASSWORD, self.codes[1])

    def test_lockout_after_repeated_failures_even_for_correct_login(self):
        for _ in range(ol.MAX_FAILURES):
            with self.assertRaises(ol.AuthError):
                ol.login(self.conn, "nope nope nope nope", "000000")
        with self.assertRaises(ol.LockedOut):
            ol.login(self.conn, PASSWORD, code(self.secret, 0))
        actions = [r[0] for r in self.conn.execute("select action from audit_events")]
        self.assertEqual(actions.count("auth.login.failed"), ol.MAX_FAILURES)

    def test_session_expiry_revocation_and_logout_everywhere(self):
        t1 = ol.login(self.conn, PASSWORD, code(self.secret, 0))["token"]
        t2 = ol.login(self.conn, PASSWORD, code(self.secret, 1))["token"]
        for bad in ("", "garbage", t1 + "x"):
            with self.assertRaises(ol.AuthError):
                ol.verify_session(self.conn, bad)
        ol.logout(self.conn, t1)
        with self.assertRaises(ol.AuthError):
            ol.verify_session(self.conn, t1)
        self.assertEqual(ol.verify_session(self.conn, t2), "owner")
        self.conn.execute("UPDATE sessions SET expires_at='2000-01-01T00:00:00+00:00'")
        with self.assertRaises(ol.AuthError):
            ol.verify_session(self.conn, t2)
        t3 = ol.login(self.conn, PASSWORD, self.codes[2])["token"]
        ol.logout_everywhere(self.conn)
        with self.assertRaises(ol.AuthError):
            ol.verify_session(self.conn, t3)


class NoAccountTest(unittest.TestCase):
    def test_login_before_setup_fails_generically(self):
        conn = make_conn()
        with self.assertRaises(ol.AuthError) as cm:
            ol.login(conn, PASSWORD, "123456")
        self.assertEqual(str(cm.exception), "invalid credentials")

    def test_only_one_credentials_row_can_exist(self):
        conn = make_conn()
        provision(conn)
        with self.assertRaises(Exception):
            conn.execute("INSERT INTO owner_credentials(id,password_hash,totp_secret,created_at) VALUES (2,'x','y','z')")


if __name__ == "__main__":
    unittest.main()
