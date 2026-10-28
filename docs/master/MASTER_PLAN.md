# Master Plan

## Principle
One OS, four ventures, one venture per day. Revenue-proximate work first; do not build more OS than the ventures need. Stack stays Python/Neon/Vercel.

## Priority order (by distance to first revenue)
1. **BuildFlow**: closest to launch. Fix the 5 blockers, then growth.
2. **Agriloop**: needs a persistent data layer before any real traffic.
3. **E-commerce**: storefronts exist; blocked only on the brand decision, then traffic/offer tests.
4. **Trading**: lowest priority until evidence of an edge exists. Gate: backtest + paper journal. No live capital before that.

## Weekly allocation
Mon BuildFlow, Tue Agriloop, Wed Trading, Thu E-commerce, Fri BuildFlow growth, Sat Agriloop growth, Sun OS review. Each day touches only that venture's folder. Suggested effort split: BuildFlow 35%, Agriloop 25%, E-commerce 20%, Trading 10%, OS 10%. Usage is self-reported (the app cannot read Claude usage).

## Phases
- **Phase 0 (now)**: this audit + plan; per-venture docs (step 2).
- **Phase 1**: OS tables `ventures`, `tasks`, `decisions`, `experiments`, `metrics` via reversible migration 007; venture-scoped views; weekly-allocation page.
- **Phase 2**: BuildFlow launch blockers (Storage, legal, prod Firebase run, notifications), then billing.
- **Phase 3**: Agriloop persistence (Prisma adapter, set data source, tests).
- **Phase 4**: BuildFlow sidekick (needs ANTHROPIC_API_KEY).

## Gates
- BuildFlow "ready": Storage works on prod Firebase, legal pages real, e2e green on prod project.
- Agriloop "ready": non-memory data source live, core flow tests exist.
- Trading "live": documented backtest + >=4 weeks paper results.
- Every phase: tests run once at the end; migrations reversible; approvals and audit log preserved.

## Risks
Solo-founder bandwidth; four ventures diluting focus (mitigated by day-per-venture and trading gate); unverified claims above (Neon backups, Agriloop env); Gmail token expiry ~2 Nov.

## Next
Step 2: docs/master/ventures/{BUILDFLOW,AGRILOOP,TRADING,ECOMMERCE}.md.
