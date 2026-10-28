# Master Plan: Zero to Hero OS (28 Oct 2026)

## Principle
One owner, four ventures, one OS. Revenue first: BuildFlow is closest to paying customers, so it gets the most weekly effort. Every claim in the OS is backed by a metric or marked unverified.

## Priority order
1. **BuildFlow**: clear the 5 blockers, then acquire first paying customers.
2. **Agriloop**: confirm data source; implement Prisma adapter before any real traffic.
3. **E-commerce**: owner picks the brand; validate one product with a small paid test.
4. **Trading**: no capital at risk until a backtest plus 30-day paper journal exist.

## Weekly allocation (from HANDOFF policy)
Mon BuildFlow, Tue Agriloop, Wed trading, Thu e-commerce, Fri BuildFlow growth, Sat Agriloop growth, Sun OS review. Each day touches only that venture's folder/repo. Claude usage is self-reported against this plan.

## OS phases
- **Phase 0 (now)**: docs (this file, CURRENT_STATE_AUDIT.md), venture docs in `docs/master/ventures/`.
- **Phase 1**: migration 007 (reversible, additive): `ventures`, `tasks`, `decisions`, `experiments`, `metrics`; venture-scoped views; weekly-allocation page. Stay on Python/Neon/Vercel.
- **Phase 2**: BuildFlow sales sidekick (needs `ANTHROPIC_API_KEY`, capped via `core/budget.py`).
- **Phase 3**: weekly review report ranking ventures by metric movement.

## Guardrails
Approval gates and kill switch stay on for all outbound actions. No real-money flows without an explicit owner go-ahead. Run tests once at the end of each phase.

## Success criteria (90 days)
- BuildFlow: blockers closed, >= 1 paying customer verified in Treasury.
- Agriloop: persistent data store live, smoke tests in CI.
- E-commerce: one validated product decision recorded in `decisions`.
- Trading: go/no-go recorded from evidence.
- OS: all four ventures tracked with weekly metrics.
