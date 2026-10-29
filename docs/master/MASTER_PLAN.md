# Master Plan - Zero to Hero OS (28 Oct 2026)

Basis: `CURRENT_STATE_AUDIT.md`. Constraint: one founder, finite Claude usage, Python/Neon/Vercel stack kept.

## 1. Principles
1. **Revenue first, breadth second.** BuildFlow is the nearest to paying customers, so it gets the most effort until it earns; the others are kept alive, not equally funded.
2. **Evidence before spend.** Trading gets no capital and no new code until a backtest and paper-trading journal exist.
3. **Approval gates stay.** Nothing sends, pays or trades without the owner.
4. **Docs first, code second.** One task per chat, one phase per chat, tests once at phase end (see HANDOFF token rules).
5. **Claim only what is verified.** Unverified items are listed as such until checked.

## 2. Weekly cadence (from HANDOFF; each chat touches only that venture's folder)
| Day | Focus | Share of Claude allocation (planning target, self-reported) |
|---|---|---|
| Mon | BuildFlow build | 25% |
| Tue | Agriloop | 12% |
| Wed | Trading (evidence only) | 8% |
| Thu | E-commerce | 15% |
| Fri | BuildFlow growth | 20% |
| Sat | Agriloop growth | 5% |
| Sun | OS review / metrics / planning | 15% |
The app cannot measure Claude usage; the allocation is a plan plus manual logging.

## 3. Venture goals for the next 30 days
- **BuildFlow:** clear the NOT READY blockers (Storage, real legal pages, prod Firebase run, notifications), then first 3 manual-billing paying users. Exit test: a stranger can sign up, upload, and pay.
- **Agriloop:** confirm live data source; implement persistent adapter (Prisma/Supabase) and add smoke tests. No growth spend before persistence.
- **Trading:** produce backtest report and 30-day paper journal on demo; decision gate: proceed only with positive, statistically meaningful results. No live capital.
- **E-commerce:** founder picks the brand; then audit store, set up one acquisition channel and tracking, measure before expanding.

## 4. OS roadmap (stack unchanged)
- **Phase 0 (docs):** this audit/plan, then `ventures/*.md` (report, audit, risks, MVP, roadmap, growth, metrics, acceptance criteria).
- **Phase 1 (build):** reversible migration 007 adding `ventures`, `tasks`, `decisions`, `experiments`, `metrics`; venture-scoped views; weekly-allocation page. Keep owner-only auth, audit log, approval gates.
- **Phase 2:** BuildFlow prospect pipeline per `IMPLEMENTATION_AUDIT.md` sections 6-12 (needs `ANTHROPIC_API_KEY`, $80/mo cap already enforced).
- **Phase 3:** refresh stale docs, remove dead `app.js`, fix "MOCK" label, rotate pasted secrets.
Each phase ends with tests run once and an updated handoff file.

## 5. Metrics (north star: verified revenue per week)
Per venture weekly: revenue (verified via Treasury only), active users/customers, one leading indicator (BuildFlow: demos booked; Agriloop: listings; Trading: paper P&L and trade count; E-commerce: sessions and conversion). Decisions and experiments are logged with outcome.

## 6. Risks and kill criteria
- Spreading thin: if a venture shows no leading-indicator movement for 4 weeks, its allocation drops to review-only.
- Gmail token expiry ~2 Nov silently stops sending: fix first.
- Cold-email account risk, PII handling, prompt injection via screenshots: mitigations in `IMPLEMENTATION_AUDIT.md` sections 8-9.
- Backups unverified: check Neon PITR before Phase 1 migration.

## 7. Immediate next actions
1. Founder answers open decisions (audit section 7).
2. Next chat: `docs/master/ventures/{BUILDFLOW,AGRILOOP,TRADING,ECOMMERCE}.md`.
