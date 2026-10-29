# Founder OS

Founder OS (formerly "Zero-to-Revenue Agent System"; the GitHub repo keeps its old name) is an owner-only
control room with three cooperating agents: **Scout** (find opportunities and leads), **Operator** (draft and,
after owner approval, send outreach and applications) and **Treasury** (verify payments, read-only on chain,
PayPal order verification). Single-tenant, Python + Neon Postgres + Vercel, no build step.

## Status
- Live: Scout, Operator (Gmail send, approval-gated), Treasury (EVM + PayPal verification), leads import/draft/send, Game plan, read-only MCP connector.
- Not live: no AI model is wired in (`SCOUT_CLIENT = None`, needs `ANTHROPIC_API_KEY`); WhatsApp is record-only.
- Direction and gaps: [IMPLEMENTATION_AUDIT.md](IMPLEMENTATION_AUDIT.md), [docs/master/HANDOFF.md](docs/master/HANDOFF.md), [docs/master/FOUNDER_OS_AUDIT.md](docs/master/FOUNDER_OS_AUDIT.md).
- Original agent spec (still normative for safety rules): [MASTER_SYSTEM.md](MASTER_SYSTEM.md). Security: [SECURITY.md](SECURITY.md).

## Run tests
```
TEST_DATABASE_URL=postgresql://... python3 -m unittest discover -s tests -t .  # throwaway Postgres, never production
```

## Using it
- Live: https://zero-to-revenue-neon.vercel.app (install it as an app from the browser).
- Local: `python scripts/run_local.py`, see [docs/runbooks/LOCAL_APP.md](docs/runbooks/LOCAL_APP.md).
- Pages: Overview, Scout, Operator, Treasury, Game plan (BuildFlow launch plan: [docs/strategy/BUILDFLOW_LAUNCH_PLAN.md](docs/strategy/BUILDFLOW_LAUNCH_PLAN.md)).
