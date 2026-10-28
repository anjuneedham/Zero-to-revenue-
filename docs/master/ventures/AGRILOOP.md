# AGRILOOP — venture plan

Status: draft from evidence in `docs/master/HANDOFF.md` (verified 28 Oct). Items marked UNVERIFIED were not checked.
Cadence: Tue build, Sat growth. Touch only this venture's folder on those days.

## 1. Report
- Repo: `agriloopmain` (private; same commit 03eba34 as public `farm-market-place`; `agriloop` is the older 204-file predecessor).
- Stack: Next.js 16, Supabase Auth + RLS migrations, Capacitor Android shell.
- Live: agriloopmain.vercel.app returns 200, `/market` returns 200.
- Marketplace data uses an in-memory source (`AGRILOOP_DATA_SOURCE=memory`). The repo itself says "NOT production-safe".
- Prisma adapter is the repo's own "largest remaining item, blocker for real production traffic".
- No automated tests (only Android boilerplate).

## 2. Audit
| Area | State | Evidence |
|---|---|---|
| Auth | Supabase Auth + RLS migrations exist | repo |
| Marketplace data | In-memory, resets on restart/redeploy | repo docs |
| Persistence adapter | Not built | repo docs |
| Tests | None | repo |
| Live env data source | UNVERIFIED (Vercel env not inspected) | open decision |
| Backups / DR | UNVERIFIED | — |

## 3. Migration risks (memory -> persistent store)
1. **Data loss today.** If production runs `memory`, every listing/order since last cold start is already ephemeral. Confirm the live env value first (Vercel `filter_project_envs`, no decrypt) before anything else.
2. **Two sources of truth.** Supabase (auth/RLS) vs Prisma adapter: pick one database as system of record. Recommended: Prisma on the Supabase Postgres so RLS and app data share one DB. Decision needed.
3. **RLS vs Prisma bypass.** Prisma connects with a service-role/direct connection and bypasses RLS. Authorisation must be enforced in app code (or via per-request JWT claims), or RLS gives false assurance.
4. **Schema drift.** No tests means no safety net for the adapter swap. Write contract tests against the data-source interface first, run them against both `memory` and the new adapter.
5. **Irreversible migrations.** Ship reversible migrations only; snapshot before each; run on a Supabase branch first.
6. **Seed/demo data leaking to prod.** Memory source likely ships seed rows; gate seeding behind an env flag.
7. **Connection limits on serverless.** Vercel + Prisma needs pooling (pgbouncer/Supabase pooler URL) or connections exhaust under traffic.
8. **Android shell cache.** Capacitor app may cache old API shapes; version the API and force-update before breaking changes.
9. **Cutover.** Feature-flag `AGRILOOP_DATA_SOURCE` (`memory` | `prisma`), dual-run in preview, switch production only after acceptance criteria below pass; keep rollback by flipping the flag.

## 4. MVP scope
In: persistent listings/orders/users, enforced authorisation, basic tests on the data layer, production env documented.
Out (until MVP is live with real users): payments beyond manual, logistics, Android store release, analytics beyond basic.

## 5. Roadmap
- Wk 1 (Tue): verify live data source; decide DB of record; write data-source contract tests.
- Wk 2 (Tue): Prisma adapter + reversible migrations on a Supabase branch; auth enforcement.
- Wk 3 (Tue): preview dual-run, pooling, seed gating; cutover behind flag.
- Wk 4 (Tue): rollback drill, backup check, Android shell compatibility.

## 6. Growth plan (Saturdays)
Hypotheses to validate, not facts: recruit a small set of farmers/buyers in one locality, onboard manually, measure listing-to-order conversion before any paid acquisition. Growth work starts only after persistence is live.

## 7. Metrics
Listings created, active sellers, buyer sessions, listing-to-order conversion, order completion rate, 7-day seller retention, error rate, data-loss incidents (target 0).

## 8. Acceptance criteria
- Production `AGRILOOP_DATA_SOURCE` is persistent and verified.
- Data survives redeploy (test: create listing, redeploy, listing remains).
- Contract tests pass on both adapters.
- Authorisation tests prove a user cannot read/write another user's records.
- Backup/restore tested once; rollback via flag demonstrated.

## Open decisions
1. Live data source value (verify).
2. Database of record (Supabase Postgres + Prisma recommended).
3. Target locality/market for first users.
