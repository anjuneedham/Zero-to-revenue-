# Founder OS audit: Phase 0-1 findings (29 Oct 2026)

Read-only audit plus one dead-file removal. No feature work was done, because the target spec is not in the repo (see "Blocker").

## Blocker: "Founder OS" does not exist in this repository
- `grep -ri "founder os|founder_os|founderos"` returns nothing in code, docs, prompts, config or commit history.
- The repo's own names for itself: "Zero-to-Revenue Agent System" (README, MASTER_SYSTEM.md, MCP server name),
  "BuildFlow AI Revenue OS" (IMPLEMENTATION_AUDIT.md, 26 Oct) and "Zero to Hero OS" (docs/master/HANDOFF.md, 28 Oct).
  So the product has been renamed at least twice on paper and never in code.
- The task brief was truncated at "RULE 2: Do not assume the newest code". The Founder OS feature list / spec was not part of it,
  and the "new Founder OS features coded but not integrated" it describes were not found. Per HANDOFF.md, the planned new
  modules (ventures, tasks, decisions, experiments, metrics, migration 007) have not been built.
- The brief is written for a JS/TS app (components, hooks, server actions, lint, tsc). This is Python 3.13 stdlib HTTP +
  Neon Postgres + vanilla JS, no build step. Phases 12/10 translate to: `unittest` against a throwaway Postgres, and no bundler.

## Phase 0: actual architecture
- Backend: `dashboard/app.py` (one `handle()` for local + Vercel via `api/index.py`), `dashboard/mcp.py` (read-only MCP), `dashboard/api_data.py`.
- Core: `core/{db,queue,policy,audit,actions,budget,events,notifications,orchestrator,auth,scheduler,reports,rates}`.
- Agents: Scout, Operator, Treasury (`agents/`). Integrations: Gmail, PayPal, Twilio WhatsApp (record-only), web fetch.
- DB: migrations 001-006 (init, owner auth, scout, operator/treasury, leads). Auth: scrypt + TOTP, hashed sessions.
- Frontend: `dashboard/pages/index.html` + `static/js/{core,main,overview,scout,operator,treasury,plan}.js`, PWA (`sw.js`).
- Cron: one daily Vercel Cron -> `/api/cron` -> `scheduler.tick`.
- Tests: 236 per IMPLEMENTATION_AUDIT. Not run this session: no Postgres server in this container (`psql` client only), and the suite needs `TEST_DATABASE_URL`.

## Phase 1: legacy classification
| Item | Class | Note |
|---|---|---|
| `dashboard/static/app.js` (212 lines) | E dead | Unreferenced by index.html, app.py, sw.js or tests. **Removed in this commit.** |
| README / MASTER_SYSTEM.md / docs/architecture | B/D stale | Describe the crypto "zero-capital" product; README says Operator/Treasury "not built yet" though they are. |
| MCP `serverInfo.name = "zero-to-revenue"` + instructions | C | Branding; rename only once the product name is decided (connector clients key on it). |
| `status.mode = "MOCK"`, `modechip` in index.html, `core/reports.py` | D misleading | PayPal and Gmail are live. |
| Scout marketplace sources, `opportunities` job/bounty model | A/F | Audit says demote to a side feed; not removed. |
| `integrations/notifications/whatsapp.py` MockWhatsApp vs `twilio_whatsapp.RecordOnly` | F | Two mock backends; check which is used before deleting. |
| `SCOUT_CLIENT = None` (`dashboard/app.py:44`) | gap | No AI runs anywhere; needs `ANTHROPIC_API_KEY`. |

## What I need to proceed (decisions only you can make)
1. The actual Founder OS spec (resend the brief from RULE 2 onward, or point me at the doc/repo).
2. Is "Founder OS" the new name for this repo, or a different codebase (e.g. `buildflow`) that should absorb it?
3. Keep the Python/Neon/Vercel stack (HANDOFF.md says yes)?
