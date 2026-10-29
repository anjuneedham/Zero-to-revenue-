# Founder OS

Founder OS (formerly the "Zero-to-Revenue Agent System"; the GitHub repo keeps its old name) is an owner-only control room for
four businesses (BuildFlow, Agriloop, fashion, trading) plus the 60-day challenge sales pipeline. Python 3.13, Postgres (Neon),
Vercel, vanilla JS, no build step.

## What it does
- **Founder / BuildFlow / Agriloop / Fashion / Trading**: per-business workspaces (goals, tasks, KPIs, blockers, content, marketplace, shop, trading research).
- **Challenge**: prospect pipeline, copy-ready offer drafts per channel, deals, pace against $10,000 verified cash by 31 Dec 2026
  ([runbook](docs/runbooks/CHALLENGE.md)).
- **Lab / Growth**: research and evidence, prompt versions, experiments with decisions and learnings. The AI command center
  only runs when `ANTHROPIC_API_KEY` and the budget variables are set.
- **Payments**: request a PayPal payment link, check if it is paid, ledger of verified receipts. Only PayPal-confirmed payments count as revenue.
- **Overview / Game plan**: cash, kill switch, alerts, progress checklists.
- **Read-only MCP connector** so a Claude chat can ask "what needs my attention?".

Nothing is sent, charged or signed by the system. The old Scout, Operator and Treasury agents (gig-feed scanning, proposal
drafting and Gmail sending, crypto wallet watching) were removed on 29 Oct 2026; see [docs/master/CONSOLIDATION.md](docs/master/CONSOLIDATION.md).

## Run
- Live: https://zero-to-revenue-neon.vercel.app (install it as an app from the browser).
- Local: set `DATABASE_URL` (see `.env.example`), then `python scripts/run_local.py` ([runbook](docs/runbooks/LOCAL_APP.md)).
- Owner login is a password plus an authenticator app, stored in Postgres ([setup](docs/runbooks/PHASE1_SETUP.md)).

## Test
```
TEST_DATABASE_URL=postgresql://... python3 -m unittest discover -s tests -t .  # throwaway Postgres, never production
```

## Code map
`core/` domain logic (challenge, payments, founder, workspace, ai, growth, lab, weekly, scheduler, auth, audit, policy) ·
`dashboard/` HTTP handler, API modules, static UI · `api/index.py` Vercel entry · `integrations/` PayPal, Twilio WhatsApp (record-only),
web fetch · `database/migrations` forward-only SQL (rollbacks in `database/rollback`).

Spec history: [MASTER_SYSTEM.md](MASTER_SYSTEM.md) (original, partly historical) · [SECURITY.md](SECURITY.md) ·
[docs/master/CONSOLIDATION.md](docs/master/CONSOLIDATION.md) (branch map, open decisions).
