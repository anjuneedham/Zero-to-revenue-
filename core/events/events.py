"""Structured agent-to-agent events (spec section 36). Append-only, DB-backed."""

import json

from core.db import now


def emit(conn, event: str, source_agent: str, payload: dict) -> None:
    conn.execute("INSERT INTO events(at, event, source_agent, payload) VALUES (?,?,?,?)",
                 (now(), event, source_agent, json.dumps(payload, sort_keys=True)))
