from core.db import now


def audit(conn, actor: str, action: str, target: str | None = None, detail: str | None = None) -> None:
    conn.execute("INSERT INTO audit_events(at,actor,action,target,detail) VALUES (?,?,?,?,?)",
                 (now(), actor, action, target, detail))
