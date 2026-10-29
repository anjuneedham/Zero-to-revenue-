# Founder OS Phase Handoff

Latest entry on top. Rules and templates: [FOUNDER_OS_BUILD_PROTOCOL.md](FOUNDER_OS_BUILD_PROTOCOL.md).

---

## Phase 0: Audit and Reset. Completed 2026-10-29

**PHASE 0 COMPLETE**
**Overall status:** PASS (read-only audit; baseline tests green)
**Branch / last commit:** `ccr-b2711e77-m8rmgm`, based on `1b1c990`, merged with protocol commit `dda7d41`

### Objective
Establish the verified truth about the repo and decide what to keep, adapt or retire. No application code, schema, config or infrastructure changes.

### Work completed
- Inspected the whole repo: architecture, DB, APIs, auth, AI, agents, prompts, UI, integrations, scheduler, tests, config, docs (PASS)
- Located every piece of three-agent logic (audit section 2) (PASS)
- Ran the full test suite against a throwaway local Postgres (PASS, below)
- Checked protocol Section 0 claim by claim (audit section 0) (PASS)
- Merged the protocol file from `origin/ccr-cf790779-6k71zs`; it was absent from this branch at first (PASS)

### Files
- Created: `docs/PHASE_0_AUDIT.md`
- Modified: `docs/PHASE_HANDOFF.md` (this entry added on top; the Protocol Setup entry is kept below)
- Added via merge: `docs/FOUNDER_OS_BUILD_PROTOCOL.md`
- Removed: none

### Changes by area
- Database / API / UI / AI / Integrations: none (audit only)

### Tests
| Command | Result | Status |
|---|---|---|
| `TEST_DATABASE_URL=postgresql://postgres@/t0?host=/var/tmp&port=5433 python3 -m unittest discover -s tests -t .` (throwaway Postgres 16, deleted after) | Ran 236 tests in 46.0s, OK | PASS |
| Live site, real Neon DB, Gmail, PayPal, RPC, Anthropic | not exercised | NOT TESTED |

### Discrepancies found at start of phase
- Protocol file was not on this branch (it exists on another branch); now merged.
- Older audit says status mode is hard-coded "MOCK"; code now returns `LIVE`/`LOCAL` (only a default chip label and a docstring still say MOCK).
- Docs (`README`, `MASTER_SYSTEM`, `docs/architecture/*`) describe the old crypto/SQLite product, not the code.
- `dashboard/static/app.js` is unreferenced dead code.

### Known issues and technical debt
See audit section 8. Main ones: three-agent names hard-coded in policy enum, `agents` CHECK constraint, scheduler, queue/budget/events columns, routes, UI and tests; bounty-centric data model; no migration runner or rollback; no CI; no AI running; payments anchored to opportunities; `ResourceWarning` noise in tests.

### Decisions and assumptions
- Decision: keep Python + Neon + Vercel and the `core/` layer; retire the three-agent shape in stages (audit section 9).
- Decision: remaining founder questions (fashion repo, EVM code, API key, CI, sibling repos, credential rotation) are **non-blocking**. Phase 1 uses the defaults in audit section 12 and does not re-ask them.
- Assumption (unverified): Neon prod has the same migration state as 001-006 and has backups.

### Unfinished work
Nothing inside Phase 0. Not verified: Neon backups, prod env vars, sibling repos.

### Next phase
- Phase 1: Foundation and Architecture
- Prerequisites: protocol merged (done); baseline tests green (done, 236/236); a local throwaway Postgres to run tests (recipe: `initdb` in `/var/tmp`, start on port 5433 as the `postgres` user, set `TEST_DATABASE_URL`).

### Risks and recommended next actions
- Run the tests before and after every Phase 1 step; keep the 236 green.
- Take/verify a Neon backup before anyone applies migration 007 to production. Applying it is a production change needing founder approval in that chat.
- Gmail OAuth token lapses around 2 Nov and leaked credentials still need rotation (owner actions, outside Phase 1).
- Phase 1 scope per protocol: business-context model (`buildflow`, `agriloop`, `fashion`, `trading`), additive reversible migrations (businesses, tasks, decisions, metrics, experiments, knowledge placeholders), module boundaries, model-routing config and usage logging, app shell and navigation, reuse of auth/audit/kill switch/policy, retire or wrap the three-agent structure. Out of scope: workspaces, dashboard content, command center, automations.

### Ready-to-paste next-chat instruction
```
Read /docs/FOUNDER_OS_BUILD_PROTOCOL.md, then /docs/PHASE_HANDOFF.md, then /docs/PHASE_0_AUDIT.md.
Begin Phase 1: Foundation and Architecture.
Prerequisites to verify first: protocol present (PASS); 236 baseline tests green against a throwaway Postgres (PASS in Phase 0, re-run to confirm).
Known issues carried forward: three-agent coupling (audit section 2), no migration runner, no CI, AI disabled, bounty-centric data model.
Open founder questions are non-blocking; use the defaults in audit section 12 and do not re-ask them.
Then follow the protocol's start-of-phase checklist, complete only Phase 1, update /docs/PHASE_HANDOFF.md, report verified results, and stop.
Do not apply migrations to production or change infrastructure without my approval in that chat.
```

---

## Protocol Setup. Completed 2026-10-28
**Overall status:** PASS (documentation only)

- `docs/FOUNDER_OS_BUILD_PROTOCOL.md` created. `docs/PHASE_HANDOFF.md` created.
- No phase was completed by that task; no application code was audited, run, tested or modified.
- Section 0 of the protocol was an unverified snapshot; Phase 0 has now checked it (see the Phase 0 entry above and audit section 0).
- Legacy planning note `docs/master/HANDOFF.md` was treated as unverified input to Phase 0.
