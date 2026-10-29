# Founder OS consolidation (29 Oct 2026)

Founder OS is the new name of this repo. The work for it was built in separate sessions on separate branches and never joined.
This file records what was found, what is now merged into one tree, and what is still open. Branch `ccr-65ceaa13-0k9m1u` is the
consolidated tree.

## Two lines of work, both built from `1b1c990`
| Line | Tip | What it is | Migrations |
|---|---|---|---|
| **A. Founder OS Phases 1-9** | `ccr-3cc67fe7` | `core/founder*`, `workspace`, `ai`, `growth`, `prompt_lab`, `knowledge`; pages Founder, BuildFlow, Agriloop, Fashion, Trading, Lab, Growth | 007_a_retire_early_dashboard_schema, 007_founder_os_core, 008_founder_dashboard, 009-015 |
| **B. Phase 10 challenge OS (what production runs)** | `ccr-42941a77` | `core/challenge`, `ingest`, `weekly`, `ventures`, `agents/operator/pitches`; pages Challenge, Ventures | 007_challenge, 008_ventures |

Both were merged here (B first, then A); the Phase 10 **Ventures** page was then removed as redundant (see finding 3), plus the progress bar, master-plan docs, venture docs, BuildFlow content engine and the
World Builders site. 433 tests pass on real Postgres. All 14 pages load in Chromium at desktop and phone width with no JS or API errors.

## Branch-by-branch
| Branch | Content | Status |
|---|---|---|
| `ccr-42941a77`, `claude/founder-os-phase-10` | Phase 10 (the second is the first three commits of the first) | merged |
| `ccr-3cc67fe7` | Phases 1-9 incl. Phase 9 (a9ab588) | merged |
| `ccr-79ad6026`, `ccr-edf0723c`, `ccr-9e3eecee` | Phase 7 / 8 / 6 tips, all ancestors of `ccr-3cc67fe7` | contained |
| `phase-9-experiments` | **Alternative** Phase 9 (DB-trigger lifecycle, `015_experiments_growth`) | **not merged**: see below |
| `ccr-b8a0a91d` | OS-wide progress bar (plan.json, core/overview/plan.js) | merged |
| `ccr-762d2b14` | CURRENT_STATE_AUDIT, MASTER_PLAN (longest of 5 near-identical drafts) | docs imported |
| `ccr-12f4a122`, `ccr-59621a0e`, `ccr-48dc1c9b`, `ccr-c5eb1654`, `ccr-a240a1bc` | earlier drafts of the same docs, NEXT.md, handoff edits | superseded, not merged |
| `ccr-7eefc2f4`, `ccr-cead2ead`, `ccr-af12f3f8` | docs/master/ventures/{BUILDFLOW,AGRILOOP,ECOMMERCE,TRADING}.md | imported (AGRILOOP from the fuller `cead2ead`) |
| `ccr-134f546c` | first Ventures migration (`007_ventures`) and API | superseded by B's `008_ventures`, not merged |
| `ccr-b2711e77`, `ccr-cf790779` | FOUNDER_OS_BUILD_PROTOCOL, PHASE_0_AUDIT | already in A |
| `claude/buildflow-content-dashboard` | partner playbook page, week-1 content data | imported to `docs/buildflow-content/` |
| `ccr-eb9fdb8a`, `ccr-8661f91e`, `claude/world-builders-landing` | World Builders PHP site + static landing | imported to `sites/world-builders/`. World Builders Construction is the agency's last client job and a side project; it is not an OS venture and nothing in the app depends on it |
| `claude/token-usage-optimization` | CLAUDE.md / STATE.md "one task per session" rules, MASTER_PLAN checklist | **not merged** (that session method was abandoned; its MASTER_PLAN would overwrite the imported one) |

## Findings
1. **Root cause of the 29 Oct outage.** B's incident note blames an "unrelated `decisions` table". It is line A's `007_founder_os_core`
   (creates `decisions`, `experiments`, `kpis`, ...), applied to the shared Neon DB by a preview deploy of an A branch. Preview
   deploys share the production database and run migrations on cold start. Any branch push can change production's schema.
2. **Two Phase 9 implementations.** `phase-9-experiments` and A's `a9ab588` both `ALTER experiments` with the same column names
   (`duration_days`, `result_value`, `decision`) but different values (`scale` vs `adopt`) and different migration file names
   (`015_experiments_growth` vs `015_experiment_growth`). They cannot both apply. This tree keeps A's. If a preview of
   `phase-9-experiments` ever ran on Neon, `015_experiment_growth` will fail with DuplicateColumn: check `schema_migrations`
   before deploying (see "Before you deploy").
3. **Ventures removed (owner decision, 29 Oct).** The Ventures page, `/api/ventures/*`, `core/ventures.py`, its tests and migration
   `008_ventures.sql` are deleted; the Founder workspaces (`businesses`, `work_tasks`, `decisions`, `experiments`) are the single
   source of truth. Production already applied 008, so its four tables (`ventures`, `venture_tasks`, `venture_decisions`,
   `venture_experiments`) still exist there, now unused. Check they are empty, then drop them by hand:
   `DROP TABLE venture_experiments, venture_decisions, venture_tasks, ventures;` and
   `DELETE FROM schema_migrations WHERE name='008_ventures.sql';`. Fresh databases never create them.
4. **Bugs fixed in this pass:** `Z.none()` was never defined, so Lab, Growth and parts of Agriloop showed "Could not load this page"
   (now `Z.empty`); the phone tab bar wrapped to two rows with 10 tabs (now one scrollable row); status mode was hardcoded `MOCK`
   (now LIVE/LOCAL; B had the same fix); product name was still Zero-to-Revenue in UI, PWA, MCP, auth issuer and reports.
5. **Body limits.** B added per-route limits (`body_limit`), A added a 48 KB read limit (`read_limit`). Both kept: handlers read
   `max(READ_LIMIT, body_limit(path)) + 1` bytes; each route enforces its own limit.

## Before you deploy (not verifiable from here)
- Query Neon: `SELECT name FROM schema_migrations ORDER BY name;`. Expect B's `007_challenge`, `008_ventures`; A's rows only if a preview ran.
  Migrating a database that has exactly B's eight migrations applied was tested here (10 pending, applied cleanly, second run no-op).
- Deploy to a **preview first, but remember it hits production's database**. After deploy check `GET /api/auth/state` (200) and `GET /api/challenge` (401), not the page.
- Not run: logged-in production smoke, a live vision call, Gmail send (token expires ~2 Nov), real PayPal order, Neon backups.

## Still open (from the earlier handoffs, unchanged)
Gmail token; `ANTHROPIC_API_KEY` + LLM budget/price vars; AgriLoop live data source; BuildFlow Storage/billing/legal; fashion brand
name/plan/repo (A's Fashion page exists, data is empty); rotate secrets pasted into chats; Scout gig features (keep or remove);
no CI; Twilio is record-only. The brief's remaining checklist (single design language, one nav, one source of truth per domain)
is mostly done; the 13-item nav is the main leftover.
