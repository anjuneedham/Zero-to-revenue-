"""Global kill switch (spec section 30). State lives in the database."""

from core.audit import audit
from core.db import now


class NotOwner(PermissionError):
    pass


def is_paused(conn) -> bool:
    return conn.execute("SELECT value FROM settings WHERE key='paused'").fetchone()["value"] == "1"


def _set(conn, value: str) -> None:
    conn.execute("UPDATE settings SET value=?, updated_at=? WHERE key='paused'", (value, now()))


def pause_all(conn, actor: str) -> None:
    """Anyone/anything (including an agent on a security concern) may pause."""
    _set(conn, "1")
    audit(conn, actor, "kill_switch.pause")
    # Stop scheduled work from being picked up; in-flight state is preserved.


def resume(conn, verified_owner: str | None) -> None:
    """Resuming needs an identity produced by core.auth (a verified owner)."""
    if not verified_owner:
        raise NotOwner("resume requires an authenticated owner")
    _set(conn, "0")
    audit(conn, verified_owner, "kill_switch.resume")
