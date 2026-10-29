# Founder OS

Founder OS (formerly the "Zero-to-Revenue Agent System"; the GitHub repo keeps its old name) runs four businesses (BuildFlow, Agriloop, fashion, trading) from one owner-only control room, plus the 60-day challenge pipeline.
Pages: Founder, Challenge, BuildFlow, Agriloop, Fashion, Trading, Ventures, Lab, Growth, Overview, Scout, Operator, Treasury, Game plan.

Three cooperating agents — **Scout** (find opportunities), **Operator** (do the
work), **Treasury** (read-only accounting) — starting from **$0 capital**.

This is not a trading bot. No profit is assumed; only Treasury-verified payments count as revenue.

## Current status: Phase 10 — 60-day challenge OS (`LIVE` on Vercel, `LOCAL` otherwise)
- Challenge (1 Nov - 31 Dec 2026, $10k verified cash, annual plan + 2 months free + 1:1 onboarding for BuildFlow and AgriLoop): [docs/runbooks/CHALLENGE.md](docs/runbooks/CHALLENGE.md)
- Original foundation below (Phase 1, agents never act without owner approval)
- Spec: [MASTER_SYSTEM.md](MASTER_SYSTEM.md)
- Architecture & plan: [docs/architecture/PHASE0_ARCHITECTURE.md](docs/architecture/PHASE0_ARCHITECTURE.md)
- Security: [SECURITY.md](SECURITY.md)

Branch map, what was merged, open decisions: [docs/master/CONSOLIDATION.md](docs/master/CONSOLIDATION.md).

## Run tests
```
TEST_DATABASE_URL=postgresql://... python3 -m unittest discover -s tests -t .  # throwaway Postgres
```

Phase 1 pieces: SQLite schema (`database/migrations`), task queue with leases and
idempotency (`core/queue`), kill switch (`core/orchestrator`), append-only audit log,
owner-only password + authenticator-app login stored in Postgres (`core/auth`), notification service with a
mock WhatsApp backend. Setup steps: [docs/runbooks/PHASE1_SETUP.md](docs/runbooks/PHASE1_SETUP.md).
Dashboard + API run on Vercel with Neon Postgres (see [docs/runbooks/VERCEL_AND_APK.md](docs/runbooks/VERCEL_AND_APK.md)). Local: set `DATABASE_URL`, `python3 -m dashboard.app`. Scout ([docs](docs/architecture/SCOUT.md)), Operator, Treasury, the scheduler and notifications are all built; the Ventures workspace (tasks, decisions, experiments) is migration 008. State of the OS and what it still needs: [docs/master/OS_REVIEW.md](docs/master/OS_REVIEW.md).

## Using it
- Live: https://zero-to-revenue-neon.vercel.app (install it as an app from the browser).
- Local: `python scripts/run_local.py`, see [docs/runbooks/LOCAL_APP.md](docs/runbooks/LOCAL_APP.md).
- Pages: **Challenge** (default), Overview, Scout, Operator, Treasury, Game plan (BuildFlow launch plan: [docs/strategy/BUILDFLOW_LAUNCH_PLAN.md](docs/strategy/BUILDFLOW_LAUNCH_PLAN.md)).
