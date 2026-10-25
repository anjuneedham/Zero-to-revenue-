import os
import time
from unittest import mock

from core.auth import owner_login as ol

SETUP_TOKEN = "t" * 24
PASSWORD = "correct horse battery staple"


def code(secret, offset=0):
    """TOTP for the current step + offset (server accepts -1..+1; replays are rejected)."""
    return ol.totp_at(secret, int(time.time() // 30) + offset)


def provision(conn):
    """Complete first-time setup; returns (totp_secret, recovery_codes). Uses step -1 so the
    next login can use step 0 without tripping replay protection."""
    with mock.patch.dict(os.environ, {"OWNER_SETUP_TOKEN": SETUP_TOKEN}):
        secret = ol.begin_setup(conn, SETUP_TOKEN, PASSWORD)["secret"]
        codes = ol.confirm_setup(conn, SETUP_TOKEN, code(secret, -1))
    return secret, codes


def session(conn):
    secret, codes = provision(conn)
    return ol.login(conn, PASSWORD, code(secret, 0))["token"], secret, codes
