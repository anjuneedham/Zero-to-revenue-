# Current State Audit (28 Oct 2026)

Source: `HANDOFF.md` evidence (commands run 28 Oct) + `IMPLEMENTATION_AUDIT.md` (26 Oct) + founder's
updates of 28 Oct. Nothing here was re-gathered; items marked UNVERIFIED have not been checked.

## Founder updates (28 Oct, supersede the open decisions in HANDOFF.md)
- **E-commerce brand:** a NEW brand, **Choice-Yaad n Abroad**, for Jamaicans worldwide, later other markets
  culturally adjacent to Jamaicans, with a different style. It is not Kadeform or NF-Fragrance, and no repo exists yet.
- **Gmail token:** expires ~2 Nov. Not critical.
- **Agriloop:** target live by **15 Nov** on Google Firebase. Payments are a problem. BuildFlow already runs on
  Firebase (`build-6fa95`), so reuse that is preferred over starting fresh. Data source is still open.

## Ventures

| Venture | Repo | Live | Verified state | Blockers |
|---|---|---|---|---|
| Zero to Hero OS | `Zero-to-revenue-` | zero-to-revenue-neon.vercel.app (200) | 236 own tests; auth, audit log, approvals, kill switch work | Lead/opportunity-centric, single-tenant; no AI key set (`ANTHROPIC_API_KEY`); Gmail token expiry ~2 Nov; Neon backup/PITR UNVERIFIED |
| BuildFlow | `buildflow` | buildflow-app-beta.vercel.app (200) | Own report 25 Oct: NOT READY. 32 unit + rules + e2e suites exist, NOT re-run | Firebase Storage not provisioned; placeholder legal pages; never run on real prod Firebase; no billing; no push/email |
| Agriloop | `agriloopmain` (private; = public `farm-market-place` @03eba34) | agriloopmain.vercel.app (200, /market 200) | Next.js 16, Supabase Auth + RLS migrations, Android shell | In-memory data source (docs: "NOT production-safe"); Prisma adapter not done; no automated tests; live env data source UNVERIFIED; payments unresolved |
| Trading | `mq5` | n/a | MQL5 EA for Deriv synthetics, in-MT5 unit script | No backtest, journal or stats, so no evidence of an edge; cannot run MT5 here |
| E-commerce | none yet (Choice-Yaad n Abroad) | n/a | Existing stores (Kadeform, NF-Fragrance) are other products | Brand, niche, supplier, store platform all undecided |

## Key risks
1. **Agriloop 15 Nov is 18 days out** with an in-memory data layer, no tests and unsolved payments. A Firebase
   move means a data-layer rewrite from Supabase/Prisma plans to Firestore, plus a payment provider decision.
   Firebase has no payments of its own; BuildFlow's own payment gap (Stripe seam, manual mode) is the same problem.
2. **Two ventures share one unsolved dependency (payments).** Solve once, reuse in both.
3. **No AI running in the OS.** All "intelligence" is regex/templates until a key is set.
4. **Trading has no evidence of edge.** Keep it paper-only until backtests exist.
5. **Gmail send stops ~2 Nov** (OAuth app in Testing, 7-day refresh token).

## Decisions needed from founder
1. Agriloop: confirm "reuse BuildFlow's Firebase project" means (a) same project `build-6fa95` or (b) a new
   project using the same patterns. Confirm launch scope on 15 Nov (browse/list only vs. paid checkout).
2. Agriloop payments: which provider and region (card, mobile money, cash on delivery for launch?).
3. Choice-Yaad n Abroad: product category, first 5 SKUs, supplier/fulfilment route, Shopify vs. other.
