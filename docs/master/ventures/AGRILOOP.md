# Agriloop (repo: `agriloopmain`, private)

Evidence source: docs/master/HANDOFF.md plus NEXT.md correction. Status: **pre-launch, NOT live** (founder-confirmed; supersedes the earlier handoff note of a live 200). Unverified items are marked.

## Report
- Next.js 16 marketplace, Supabase Auth + RLS migrations, Capacitor Android shell.
- Same commit (03eba34) as public `farm-market-place`; `agriloop` is the older 204-file predecessor (treat as archive).
- Repo docs state marketplace data uses an in-memory source (`AGRILOOP_DATA_SOURCE=memory`), "NOT production-safe". Prisma adapter is "largest remaining item, blocker for real production traffic".

## Audit
- Persistence: in-memory only; data lost on every restart/deploy. Hard blocker.
- Tests: none for the web app (only Android boilerplate).
- Auth/RLS: Supabase Auth and RLS migrations exist. UNVERIFIED: whether migrations are applied to a real Supabase project.
- Live env value of the data source: UNVERIFIED (not checked).
- Two data stacks are implied (Prisma/Postgres adapter vs Supabase): decision pending.

## Risks
- Launching on memory data loses all listings/orders.
- No tests: regressions when the data layer is swapped.
- Marketplace cold start: needs both suppliers and buyers; chicken-and-egg.
- Dual data-layer ambiguity (Prisma vs Supabase) can double the work.
- Payments, delivery, and food/agri regulation not scoped anywhere in the evidence.

## MVP scope
In: persistent data layer (one stack, chosen up front), core flow only (supplier lists produce, buyer browses and sends an order request), auth, tests for that flow, waitlist page.
Out: payments, delivery logistics, Android store release, ratings, analytics beyond basics.

## Roadmap
| Step | Work | Day |
|---|---|---|
| 0 | Founder decision: Prisma/Postgres vs Supabase as the data layer; target launch date | before Tue |
| 1 | Implement the chosen adapter behind the existing data-source switch | Tue |
| 2 | Set data source in env, migrate/apply schema to a real DB | Tue |
| 3 | Add tests for the core flow (list, browse, order request, auth) | Tue |
| 4 | Waitlist/landing capture live | Tue/Sat |
| 5 | Soft launch with a handful of suppliers | after gates |

## Growth plan (Sat, pre-launch = waitlist)
Recruit a small number of suppliers (the scarce side) by direct outreach; run a buyer waitlist; seed listings by hand; no paid acquisition before the data layer gate passes. Track outreach as OS tasks and experiments.

## Metrics
Suppliers contacted, suppliers onboarded, listings live, waitlist signups, order requests, repeat buyers. Pre-launch leading metrics: outreach reply rate, waitlist conversion.

## Acceptance criteria (gate "ready", from MASTER_PLAN)
- [ ] Non-memory data source live (data survives a redeploy)
- [ ] Core flow tests exist and pass
- [ ] Schema/RLS applied to a real Supabase/Postgres project (if applicable)
- [ ] Waitlist capture working
- [ ] Data-layer decision and launch date recorded in the OS `decisions` table
