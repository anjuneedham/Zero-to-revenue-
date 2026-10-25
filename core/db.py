"""PostgreSQL connection + forward-only migrations.

Production: Neon via Vercel (DATABASE_URL, pooled -> no server-side prepared
statements). Rows support both row["name"] and row[0]. Statements use `?`
placeholders, translated to the driver's `%s`.
"""

import os
import re
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import psycopg

MIGRATIONS = Path(__file__).resolve().parents[1] / "database" / "migrations"
MIGRATION_LOCK = 7_262_025  # arbitrary app-wide advisory-lock key


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Row(dict):
    """Dict row that also allows positional access."""

    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


def _row_factory(cursor):
    names = [c.name for c in cursor.description or []]
    return lambda values: Row(zip(names, values))


class Connection:
    """Thin wrapper: autocommit, `?` placeholders, name/index rows."""

    def __init__(self, raw):
        self.raw = raw

    def execute(self, sql, params=()):
        return self.raw.execute(_translate(sql), params or None)

    def transaction(self):
        return self.raw.transaction()

    def close(self):
        self.raw.close()


def _translate(sql: str) -> str:
    if "?" not in sql:
        return sql
    return re.sub(r"\?", "%s", sql)


def connect(url: str | None = None, schema: str | None = None) -> Connection:
    url = url or os.environ.get("DATABASE_URL", "")
    if not url.startswith(("postgres://", "postgresql://")):
        raise RuntimeError("DATABASE_URL must be a postgres:// URL")
    raw = psycopg.connect(url, autocommit=True, row_factory=_row_factory, prepare_threshold=None)
    if schema:
        raw.execute(f'SET search_path TO "{schema}"')
    return Connection(raw)


def money(value) -> float:
    return float(value) if isinstance(value, Decimal) else float(value or 0)


def migrate(conn: Connection) -> list[str]:
    """Apply pending migrations; safe under concurrent cold starts (advisory lock)."""
    applied = []
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(%s)" % MIGRATION_LOCK)
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
        done = {r["name"] for r in conn.execute("SELECT name FROM schema_migrations")}
        for f in sorted(MIGRATIONS.glob("*.sql")):
            if f.name in done:
                continue
            conn.raw.execute(f.read_text())  # no params: multi-statement allowed
            conn.execute("INSERT INTO schema_migrations(name, applied_at) VALUES (?, ?)", (f.name, now()))
            applied.append(f.name)
    return applied
