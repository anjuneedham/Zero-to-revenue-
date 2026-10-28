# MASTER PLAN (checklist: the first unchecked box is the next session's task)

Rules: one box per session. Read docs/master/STATE.md first. When a box is done: tick it, add the commit hash, update STATE.md "Done" and "Next", push. Evidence for every repo is in docs/master/HANDOFF.md; do not re-gather it.

## Goal
Run four ventures from one OS (this repo) with one venture per weekday, tracking tasks, decisions, experiments and metrics, and getting to verified revenue first (BuildFlow is the nearest).

## Ventures (one-line status)
- BuildFlow: live beta, verdict NOT READY (storage, legal pages, billing, notifications). Nearest to revenue. Plan: docs/strategy/BUILDFLOW_LAUNCH_PLAN.md.
- Agriloop: live, but marketplace data is in-memory; needs the database adapter before real traffic.
- Trading (mq5): no backtest or paper-trading evidence of an edge. Do not risk capital until that exists.
- Fashion / clothing brand: **PLACEHOLDER.** Name: UNKNOWN. Plan: UNKNOWN. Repo: UNKNOWN. Fill in at step 0.

## Steps

### Phase A: Capture and plan
- [ ] 0. Owner supplies fashion brand name, plan, repo (or "no repo yet"); record in STATE.md and the Fashion section below.
- [ ] 1. Write docs/master/CURRENT_STATE_AUDIT.md from HANDOFF.md evidence (gaps, risks, ranked by revenue impact).
- [ ] 2. Confirm open questions: Agriloop live data source, Gmail token (expires about 2 Nov), Neon backup settings.

### Phase B: One doc per venture (each: report, risks, MVP scope, roadmap, growth plan, metrics, acceptance criteria)
- [ ] 3. docs/master/ventures/BUILDFLOW.md
- [ ] 4. docs/master/ventures/FASHION.md
- [ ] 5. docs/master/ventures/AGRILOOP.md
- [ ] 6. docs/master/ventures/TRADING.md (first deliverable: a backtest/paper-trade protocol, not a launch)

### Phase C: Build the OS (reversible migrations, Python/Neon/Vercel)
- [ ] 7. Migration 007: ventures, tasks, decisions, experiments, metrics tables.
- [ ] 8. Venture-scoped views and API endpoints.
- [ ] 9. Weekly-allocation page in the dashboard (self-reported Claude usage).
- [ ] 10. Tests for 7-9, run once at the end.

### Phase D: Execute per venture (weekly rhythm)
Mon BuildFlow, Tue Agriloop, Wed trading, Thu fashion/e-commerce, Fri BuildFlow growth, Sat Agriloop growth, Sun OS review. Each session touches only that venture's file and repo. Tasks come from that venture's roadmap.
- [ ] 11. BuildFlow launch blockers cleared (storage, legal pages, billing path for Jamaica, notifications).
- [ ] 12. First paying BuildFlow customer (verified payment only).
- [ ] 13. BuildFlow sidekick work (needs ANTHROPIC_API_KEY).
- [ ] 14. Agriloop database adapter and tests.
- [ ] 15. Fashion MVP per FASHION.md.

## Fashion section (placeholder)
Name: UNKNOWN | Plan: UNKNOWN | Repo: UNKNOWN | Stage: UNKNOWN
