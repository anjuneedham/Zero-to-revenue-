"""Single-owner login: password (scrypt) + authenticator-app code (TOTP, RFC 6238).

* Nothing secret is stored in plaintext except the TOTP seed (needed to verify codes);
  stealing the database alone still leaves the scrypt-hashed password to crack.
* Sessions are random bearer tokens; only their sha256 is stored. They expire, can be
  revoked, and "sign out everywhere" revokes all.
* Failed attempts are rate limited (global, because there is one account) and audited.
* First-time setup needs OWNER_SETUP_TOKEN (set by the owner in the host's env) and can
  complete exactly once; afterwards setup is permanently closed.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import struct
import time
from datetime import datetime, timedelta, timezone

from core.audit import audit
from core.db import now as iso_now

IDENTITY = "owner"
SESSION_HOURS = 24
MAX_FAILURES = 8           # per kind, per window
WINDOW_MINUTES = 15
MIN_PASSWORD_LEN = 12
MIN_SETUP_TOKEN_LEN = 20
ISSUER = "Founder OS"


class AuthError(PermissionError):
    """Generic on purpose: never says which factor failed."""


class LockedOut(AuthError):
    pass


class SetupDisabled(AuthError):
    pass


class SetupClosed(AuthError):
    pass


# --- password hashing -------------------------------------------------------

_N, _R, _P = 2 ** 15, 8, 1


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, maxmem=96 * 1024 * 1024)
    return "scrypt$%d$%d$%d$%s$%s" % (_N, _R, _P, salt.hex(), dk.hex())


def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, dk = stored.split("$")
        calc = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r),
                              p=int(p), maxmem=96 * 1024 * 1024)
        return hmac.compare_digest(calc.hex(), dk)
    except Exception:
        return False


_dummy = None


def _dummy_hash() -> str:
    global _dummy
    if _dummy is None:
        _dummy = hash_password("dummy-password-for-constant-work")
    return _dummy


# --- TOTP -------------------------------------------------------------------

def totp_at(secret_b32: str, step: int, digits: int = 6) -> str:
    key = base64.b32decode(secret_b32)
    h = hmac.new(key, struct.pack(">Q", step), hashlib.sha1).digest()
    o = h[-1] & 0x0F
    code = (struct.unpack(">I", h[o:o + 4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return str(code).zfill(digits)


def _verify_totp(conn, code: str, at: float) -> bool:
    row = conn.execute("SELECT totp_secret FROM owner_credentials WHERE id=1").fetchone()
    if row is None or not (code.isdigit() and len(code) == 6):
        return False
    cur = int(at // 30)
    for step in (cur - 1, cur, cur + 1):
        if hmac.compare_digest(totp_at(row["totp_secret"], step), code):
            # atomic replay guard: only a strictly newer step may be consumed
            return conn.execute("UPDATE owner_credentials SET totp_last_step=? WHERE id=1 AND totp_last_step < ?",
                                (step, step)).rowcount == 1
    return False


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _use_recovery_code(conn, code: str) -> bool:
    code = code.strip().lower()
    row = conn.execute("SELECT recovery_hashes FROM owner_credentials WHERE id=1").fetchone()
    if row is None:
        return False
    hashes = json.loads(row["recovery_hashes"])
    h = _sha(code)
    if h not in hashes:
        return False
    hashes.remove(h)  # single use
    return conn.execute("UPDATE owner_credentials SET recovery_hashes=? WHERE id=1 AND recovery_hashes=?",
                        (json.dumps(hashes), row["recovery_hashes"])).rowcount == 1


# --- rate limiting ----------------------------------------------------------

def _cutoff() -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=WINDOW_MINUTES)).isoformat()


def _check_lockout(conn, kind: str) -> None:
    n = conn.execute("SELECT count(*) c FROM auth_attempts WHERE kind=? AND ok=FALSE AND at > ?",
                     (kind, _cutoff())).fetchone()["c"]
    if n >= MAX_FAILURES:
        raise LockedOut("too many failed attempts; try again later")


def _record(conn, kind: str, ok: bool) -> None:
    conn.execute("INSERT INTO auth_attempts(kind, ok, at) VALUES (?,?,?)", (kind, ok, iso_now()))
    if not ok:
        audit(conn, "anonymous", f"auth.{kind}.failed")


# --- first-time setup -------------------------------------------------------

def _check_setup_token(conn, supplied: str) -> None:
    expected = os.environ.get("OWNER_SETUP_TOKEN", "")
    if len(expected) < MIN_SETUP_TOKEN_LEN:
        raise SetupDisabled("setup is not enabled")
    _check_lockout(conn, "setup")
    if not hmac.compare_digest(supplied.encode(), expected.encode()):
        _record(conn, "setup", False)
        raise AuthError("invalid setup token")


def setup_complete(conn) -> bool:
    row = conn.execute("SELECT setup_complete FROM owner_credentials WHERE id=1").fetchone()
    return bool(row and row["setup_complete"])


def setup_enabled() -> bool:
    return len(os.environ.get("OWNER_SETUP_TOKEN", "")) >= MIN_SETUP_TOKEN_LEN


def begin_setup(conn, setup_token: str, password: str) -> dict:
    """Step 1: store the password hash + a fresh TOTP seed (not active until confirmed)."""
    _check_setup_token(conn, setup_token)
    if len(password) < MIN_PASSWORD_LEN:
        raise ValueError(f"password must be at least {MIN_PASSWORD_LEN} characters")
    seed = base64.b32encode(os.urandom(20)).decode()
    cur = conn.execute(
        "INSERT INTO owner_credentials(id, password_hash, totp_secret, created_at) VALUES (1,?,?,?) "
        "ON CONFLICT (id) DO UPDATE SET password_hash=EXCLUDED.password_hash, totp_secret=EXCLUDED.totp_secret, "
        "totp_last_step=0 WHERE owner_credentials.setup_complete = FALSE",
        (hash_password(password), seed, iso_now()))
    if cur.rowcount == 0:
        raise SetupClosed("setup is already complete")
    audit(conn, "anonymous", "auth.setup.begin")
    uri = f"otpauth://totp/{ISSUER}:owner?secret={seed}&issuer={ISSUER}&digits=6&period=30"
    return {"secret": seed, "otpauth_uri": uri}


def confirm_setup(conn, setup_token: str, code: str, at: float | None = None) -> list[str]:
    """Step 2: prove the authenticator app works; returns one-time recovery codes."""
    _check_setup_token(conn, setup_token)
    if setup_complete(conn):
        raise SetupClosed("setup is already complete")
    if not _verify_totp(conn, code, time.time() if at is None else at):
        _record(conn, "setup", False)
        raise AuthError("invalid code")
    codes = [secrets.token_hex(5) for _ in range(8)]
    cur = conn.execute("UPDATE owner_credentials SET setup_complete=TRUE, recovery_hashes=? "
                       "WHERE id=1 AND setup_complete=FALSE", (json.dumps([_sha(c) for c in codes]),))
    if cur.rowcount == 0:
        raise SetupClosed("setup is already complete")
    audit(conn, IDENTITY, "auth.setup.complete")
    return codes


# --- login / sessions -------------------------------------------------------

def login(conn, password: str, code: str, at: float | None = None) -> dict:
    _check_lockout(conn, "login")
    row = conn.execute("SELECT password_hash FROM owner_credentials WHERE id=1 AND setup_complete").fetchone()
    pw_ok = verify_password(password, row["password_hash"] if row else _dummy_hash())
    second_ok = False
    if row and pw_ok:
        second_ok = _verify_totp(conn, code, time.time() if at is None else at) or _use_recovery_code(conn, code)
    if not (row and pw_ok and second_ok):
        _record(conn, "login", False)
        raise AuthError("invalid credentials")
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)
    conn.execute("DELETE FROM sessions WHERE expires_at < ? OR revoked", (iso_now(),))
    conn.execute("INSERT INTO sessions(token_hash, created_at, expires_at) VALUES (?,?,?)",
                 (_sha(token), iso_now(), expires.isoformat()))
    _record(conn, "login", True)
    audit(conn, IDENTITY, "auth.login")
    return {"token": token, "expires_at": expires.isoformat()}


def verify_session(conn, token: str) -> str:
    """Returns the owner identity or raises AuthError."""
    if not token:
        raise AuthError("unauthorized")
    row = conn.execute("SELECT expires_at, revoked FROM sessions WHERE token_hash=?", (_sha(token),)).fetchone()
    if row is None or row["revoked"] or row["expires_at"] < iso_now():
        raise AuthError("unauthorized")
    return IDENTITY


def logout(conn, token: str) -> None:
    conn.execute("UPDATE sessions SET revoked=TRUE WHERE token_hash=?", (_sha(token),))
    audit(conn, IDENTITY, "auth.logout")


def logout_everywhere(conn) -> None:
    conn.execute("UPDATE sessions SET revoked=TRUE")
    audit(conn, IDENTITY, "auth.logout_everywhere")
