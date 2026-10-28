# Current State Audit (28 Oct 2026)

Source: evidence in HANDOFF.md (gathered 28 Oct). "Not re-run" means taken from the repo's own reports, not verified here.

## Summary table
| Venture | Repo | Live | Tests | Readiness | Top blocker |
|---|---|---|---|---|---|
| Zero to Hero OS | Zero-to-revenue- | 200 (zero-to-revenue-neon.vercel.app) | 236 own suite (not re-run) | Working core, wrong shape for the brief | Lead-centric single-tenant model; no ventures/tasks/decisions/experiments/metrics |
| BuildFlow | buildflow | 200 (buildflow-app-beta.vercel.app) | 32 unit + rules + e2e + QA (not re-run) | NOT READY (own report, 25 Oct) | Firebase Storage not provisioned; never run on real prod Firebase |
| Agriloop | agriloopmain (= public farm-market-place @03eba34) | 200 (agriloopmain.vercel.app, /market 200) | None (Android boilerplate only) | Prototype | In-memory data source; Prisma adapter not built |
| Trading | mq5 | n/a (MT5) | In-MT5 unit-test script | No evidence of edge | No backtests, paper journal or stats |
| E-commerce | Kadeform- / NF-Fragrance- | not checked | n/a | Two storefronts, brand unconfirmed | Founder must pick the brand |

## Zero to Hero OS
- Exists: Python, Neon Postgres, Vercel; owner auth (scrypt+TOTP), append-only audit log, approval gates, kill switch, agent queue.
- Missing vs brief: projects, tasks (beyond agent queue), decisions, experiments, metrics, per-venture workspaces, weekly allocation.
- Unverified: Neon backup/PITR settings.
- Constraint: Claude usage cannot be read or enforced by the app. The allocation is a plan plus self-reported usage.

## BuildFlow
Next.js 16, Firebase (build-6fa95), Capacitor Android shell. Blockers (own report): Storage not provisioned so uploads fail; legal pages are placeholders; no real prod Firebase run; no billing (Stripe seam, manual mode); no push/email notifications.

## Agriloop
Next.js 16, Supabase Auth + RLS migrations, Capacitor Android. Repo docs: marketplace uses `AGRILOOP_DATA_SOURCE=memory` ("NOT production-safe"); Prisma adapter is the largest remaining item. `agriloop` is the older 204-file predecessor. UNVERIFIED: live Vercel env value for the data source (check key presence only, do not decrypt).

## Trading
MQL5 "Synthetic Edge EA" for Deriv synthetic indices, 20 files, last commit 26 Sep. Cannot run MT5 here. Treat as unproven until a backtest and 4+ weeks of paper results exist.

## E-commerce
Kadeform- (Shopify/Dawn, single hero product FlexBack Pro, 446 files) and NF-Fragrance- (static Netlify, five colognes, 24 files). No fashion repo found; Echo-Ai is private/inaccessible.

## Open decisions
1. Which e-commerce repo is the brand.
2. Gmail token expires ~2 Nov.
3. Agriloop live data source.
