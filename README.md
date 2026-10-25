# Zero-to-Revenue Agent System

Three cooperating agents — **Scout** (find opportunities), **Operator** (do the
work), **Treasury** (read-only accounting) — starting from **$0 capital**.

This is not a trading bot. No profit is assumed and nothing is "live" yet.

## Current status: Phase 1 (foundation) — `MOCK`, no external actions
- Spec: [MASTER_SYSTEM.md](MASTER_SYSTEM.md)
- Architecture & plan: [docs/architecture/PHASE0_ARCHITECTURE.md](docs/architecture/PHASE0_ARCHITECTURE.md)
- Security: [SECURITY.md](SECURITY.md)

## Run tests
```
python3 -m unittest discover -s tests -t .
```

Phase 1 pieces: SQLite schema (`database/migrations`), task queue with leases and
idempotency (`core/queue`), kill switch (`core/orchestrator`), append-only audit log,
owner-only Firebase token verification (`core/auth`), notification service with a
mock WhatsApp backend. Setup steps: [docs/runbooks/PHASE1_SETUP.md](docs/runbooks/PHASE1_SETUP.md).
Not built yet: dashboard UI, agents, scheduler, wallet monitoring.
