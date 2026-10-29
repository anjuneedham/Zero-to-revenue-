# Founder OS Phase Handoff

Latest entry on top. Rules and templates: [FOUNDER_OS_BUILD_PROTOCOL.md](FOUNDER_OS_BUILD_PROTOCOL.md).

## Phase 9: Experiment and Growth Engine. Completed 2026-10-29

**Overall status: PASS for the deterministic scope, with gaps listed below.** 384 tests pass locally (17 new). Phase 9 contains no model call at all, so nothing in it is NOT TESTED for lack of an API key. Migration 015 is applied only to throwaway local Postgres, **not to Neon**. The UI got a mobile/tablet/desktop width check and one end-to-end form flow, not a full accessibility pass.
**Branch:** local branch `phase-9-experiments`, created from `ccr-edf0723c-id0y6l` (Phase 8, `9b907a7`). **Not pushed** (founder chose to hold the push; any push may trigger a Vercel preview against the shared Neon DB). No preview/production URL was opened.

### Objective
Structured experiments and growth tracking per business: hypothesis, metric, duration, result and decision records; a lifecycle; funnels from real data; learnings written back to business knowledge. Out of scope and not built: executing experiments (automatically or otherwise), cross-business synthesis.

### Design (verify these first)
- **Records only.** Nothing here runs, sends or changes anything outside the database; the founder runs the experiment and records what happened.
- **Lifecycle** (`core/experiments.py`, enforced again by a DB trigger in migration 015): `proposed -> running -> succeeded | failed | inconclusive`, or `proposed|running -> abandoned`. New experiments are always `proposed` (a requested status is ignored). The generic CRUD can no longer set `status` (400); it still edits the plan while proposed.
- **Start** needs a success metric and a planned duration, then **locks the plan** (hypothesis, method, metric, KPI, baseline, target, duration, minimum sample). An empty baseline is filled from the linked KPI's current value (real data), never invented. Linked KPI/goal must be in the same business.
- **Conclude** (`POST /api/growth/experiments/<id>/conclude`) needs outcome, a result (number and/or text), learnings and a decision (`scale|iterate|stop`), then the result is fixed. Rules: the outcome may not contradict the numbers (`succeeded` with a result worse than baseline, or `failed` with the target met, is rejected; `down` KPIs are read the right way round); `scale` requires `succeeded`. Warnings (not blocks) for no sample size, sample below your minimum, concluded before the planned duration, and "one run is evidence, not proof". One transaction writes: the experiment result, a **decision record** (`decisions.experiment_id`), and the **learning**.
- **Learning write-back:** a knowledge note (tag `experiment`) plus an evidence row labelled **`assumed`**, with an `internal` source of reliability `unknown` ("numbers were typed in"). It never starts as verified; it only becomes verified through the Phase 8 evidence flow with a real source. If verified later on that source, the Lab flags it as weak.
- **Funnels** (`core/growth.py`, read-only, one business): built from existing records. BuildFlow: posts, views, signups from content items, view-to-signup rate over posts that have both numbers, primary KPI shown separately. Agriloop: farmers/buyers recorded, onboarded-or-active, active, listings, requests, deals, rates. Fashion: live products, campaigns, attributed orders, sales, customers, repeat rate. Trading: **no funnel** (research only). An untracked stage is `null` ("not tracked"), never 0; every rate carries its sample size and is flagged small-sample under 30 observations.
- **Ready to conclude:** a running experiment past `started + duration` is flagged so it cannot sit open silently.

### Work completed
- Migration `015_experiments_growth.sql` (adds `inconclusive` status; experiment columns `kpi_id, duration_days, min_sample, sample_size, result_value, decision, abandon_reason, learning_knowledge_id`; `decisions.experiment_id`; lifecycle trigger), rollback `database/rollback/015_experiments_growth_down.sql`.
- `core/experiments.py`, `core/growth.py`, `dashboard/growth_api.py`; edits to `core/founder.py` (experiments spec: forced `proposed`, `status` not editable, plan-lock guard), `dashboard/app.py`.
- API (owner auth): `GET /api/growth/<slug>` (experiments with evaluation, counts, ready list, funnel), `POST /api/growth/experiments/<id>/start|conclude|abandon`; create/edit-plan via the existing `experiments` CRUD.
- UI: new **Growth** page (`dashboard/static/js/growth.js`, nav "Growth", service-worker cache `z2r-shell-v11`); the old "Add experiment" form in `founder.js` no longer offers a status and now takes duration and minimum sample.

### Files
- Created: `core/experiments.py`, `core/growth.py`, `dashboard/growth_api.py`, `dashboard/static/js/growth.js`, `database/migrations/015_experiments_growth.sql`, `database/rollback/015_experiments_growth_down.sql`, `tests/unit/test_experiments.py`.
- Modified: `core/founder.py`, `dashboard/app.py`, `dashboard/static/js/founder.js`, `dashboard/static/js/main.js`, `dashboard/static/sw.js`, `dashboard/pages/index.html`, `tests/unit/test_founder_dashboard.py` (one test created experiments directly as `running`/`failed`; it now goes through start/abandon), docs.
- Removed: none.

### Tests
| Command | Result | Status |
|---|---|---|
| Local Postgres 16, before changes | 367 OK | PASS |
| `python3 -m unittest discover -s tests -t .` after changes | **384 OK** (17 new in `test_experiments.py`: forced `proposed`, status not editable, start preconditions, plan lock in API and DB, illegal DB transitions, baseline from KPI and cross-business KPI rejected, conclude records result/decision and locks, outcome-vs-numbers contradictions, `scale` rule, validation leaves nothing half-applied, `down` direction, abandon, warnings, 404/401, learning written as assumed with internal source and invisible to other businesses, funnel uses only recorded numbers and treats untracked as null, per-business scoping and no trading funnel, Agriloop/Fashion funnels, API ready flag, migration columns) | PASS |
| Browser, throwaway local DB, `AUTH_DISABLED=1`: Growth page, Start button, Record-result form submit -> experiment `succeeded`, no JS errors; no horizontal scroll at 390/768/1280 px (a long pill overflowed at 390 px; fixed and re-checked) | | PASS (partial: edit-plan, abandon and add-experiment dialogs, keyboard/screen-reader use not exercised) |
| Migration 015 on Neon, any preview/production URL | not applied, not opened | NOT TESTED |

### Acceptance criteria
- Hypothesis, metric, duration, result and decision records: PASS
- Experiment lifecycle: PASS (code and DB)
- Growth funnels from real data: PASS for BuildFlow, Agriloop, Fashion (thin where records are thin); Trading intentionally none
- Learnings written back to business knowledge: PASS (assumed, source-traced)
- Automated execution / cross-business synthesis: not built, by design

### Discrepancies found at start of phase
- The existing generic CRUD let any experiment be created or edited straight into `running`/`succeeded` with free-text results, and the 4-state status enum had no "inconclusive". Both changed (behaviour change; pre-existing test updated).

### Known issues and technical debt
- Result numbers are typed by the founder; nothing links an experiment to the KPI readings or content metrics recorded during its window. The evaluation compares one number to baseline and target, with no significance test.
- The contradiction guard only applies when a baseline exists; with no baseline the verdict says it cannot judge and the outcome is trusted.
- Funnel definitions are code per business, not data; changing a stage means a code change. Agriloop onboarding rate counts churned parties in the base (history is not tracked). BuildFlow's primary KPI is shown but kept out of rates because its unit is unknown.
- No reminder or notification when an experiment is ready to conclude (only a flag and a pill; reminders belong to Phase 10).
- Learnings are not re-checked later (no staleness date).
- Migrations 007_a, 007, 008-015 are all unapplied on production Neon.

### Decisions and assumptions
- Learning evidence starts `assumed` even when the experiment succeeded: a single founder-entered result is not independent verification.
- Contradictory outcomes are blocked rather than warned, so a record cannot say "succeeded" beside a worse-than-baseline number; `inconclusive` is the honest escape hatch.
- Status changes only via the lifecycle endpoints so every transition is audited (`experiment.start|conclude|abandon`).

### Unfinished work
- Tie experiment windows to KPI readings/content metrics so results can be pre-filled from data; funnel stage definitions as data; per-experiment audience/segment fields; reminders (Phase 10); Command Center context from experiments (not added).
- Push and Neon rollout (founder-gated).

### Next phase
Phase 10: Automation Engine, **not started**. Before it: founder Neon backup + "apply to Neon" (migrations 007_a, 007, 008-015), and a decision on which branch to push.

### Ready-to-paste next-chat instruction
```
Repo: anjuneedham/Zero-to-revenue- (attach with add_repo, push access). Phases 0-9 are on branch phase-9-experiments if it was pushed, otherwise on the local commit(s) descending from ccr-edf0723c-id0y6l (Phase 8, 9b907a7); check git branch -a and git log first and ask me where Phase 9 lives if you cannot find it. None of this is on the default branch. Check it out, then create a new branch from it for this work. Do not push to ccr-79ad6026-fa1uuh or ccr-edf0723c-id0y6l (pushes auto-deploy a Vercel preview against the shared Neon database); hold pushes until I name a branch.
Read, in order: docs/CONTINUE_FROM_HERE.md, docs/FOUNDER_OS_BUILD_PROTOCOL.md, docs/PHASE_HANDOFF.md (Phase 9 entry first), docs/FOUNDER_OS_ARCHITECTURE.md. The correct test baseline after Phase 9 is 384.
Verify first: start local Postgres 16 per the recipe in CONTINUE_FROM_HERE.md; check that pip install "psycopg[binary]>=3.2" --break-system-packages works (if PyPI is blocked, stop and tell me); run python3 -m unittest discover -s tests -t . (expect 384 OK); inspect core/founder.py, core/experiments.py, core/orchestrator (queue/scheduler/killswitch), core/scheduler.py, core/audit.py, the approval-gate code (core/actions.py) and the automations table/entity (migration 007).
Do not open or request any preview/production URL of this branch until I say the Neon backup is done.
Implement only Phase 10: Automation Engine (protocol section 9): scheduled and triggered workflows on the existing queue/scheduler; approval gates, dry-run mode, kill-switch integration, audit logging, retries/idempotency, failure notifications. Out of scope: unapproved external communication; any live-trading automation. Automations stay disabled and approval-required by default; the existing kill switch and approval gates may only be extended. Do not start Phase 11.
ANTHROPIC_API_KEY may still be missing: do not claim any model call works unless it was executed; mark model-dependent items NOT TESTED.
Finish by updating docs/PHASE_HANDOFF.md (Phase 10 entry on top, honest PASS/PARTIAL/NOT TESTED, ready-to-paste Phase 11 block) and docs/CONTINUE_FROM_HERE.md, then stop.
```

---

## Phase 8: Prompt Lab, Research, and Knowledge. Completed 2026-10-29

**Overall status: PARTIAL.** Everything deterministic is built and tested (367 tests, 19 new). **No real model call has ever been executed** (no `ANTHROPIC_API_KEY`/`LLM_*` here), so every model-dependent path is NOT TESTED against the real API. Migration 014 is applied only to throwaway local Postgres, not to Neon. The UI got a render/search smoke test, not a full click-through.
**Branch:** `ccr-edf0723c-id0y6l`, created from `966a8d3` (Phase 7 head of `ccr-79ad6026-fa1uuh`). Nothing was pushed to `ccr-79ad6026-fa1uuh`. No preview/production URL was opened or requested.

### Objective
Versioned prompts and a trustworthy, business-scoped knowledge base: prompt versioning and comparison (taking over `prompts/ai/`), research with sources and verified/assumed/unknown labels, per-business retrieval, citation and evidence tracking. Out of scope and not built: experiment engine, automation.

### Design (verify these first)
- **Prompt versions are immutable.** New text = new version of the same name (`core/prompt_lab.py`), enforced in code and by a DB trigger. One active version per name (partial unique index). Activation is an audited action. The generic CRUD `prompts` entity can now only create an *inactive* version or edit `purpose`.
- **Command Center takes its prompt from the Lab.** `ai.run` uses the active `command-center` version, else the file `prompts/ai/command-center-v1.md`. A fixed `GUARD` (JSON-only, text in `<data>`/`<untrusted>` is data, no actions, no promises of returns, "verified" only with a source) is always appended, and a `command-center` version cannot be created or activated without the `<data>`, `<untrusted>`, `needs_approval`, `claims`, `JSON` markers. `ai_usage.prompt_ref` records which version answered (`command-center@N` or `command-center@1(file)`).
- **Files:** `POST /api/lab/prompts/sync` registers `prompts/ai/<name>-v<N>.md` as `file` versions. A file that differs from the stored version is reported as **drift** and never overwrites it. It activates a name's file version only when that name has no active version. Nothing syncs automatically (no DB write on a read path).
- **Comparison is not a model call:** unified diff + averages of founder-entered scores (`prompt_evals`, 1-5, append-only). With fewer than 3 scored examples on either version the verdict says "not enough evidence"; otherwise it reports the averages and states they are hand-entered and not a statistical test. There is no automatic winner.
- **Sources and evidence** (`sources`, `evidence`, via the existing CRUD API, business-scoped, parents must be in the same business). Each claim is `verified`, `assumed` or `unknown` (default `unknown`) and must hang off a research item or knowledge note. `verified` needs a source (code message + DB CHECK). Promoting to `verified` needs a source; label changes are audited as `label assumed -> verified`. A note's or research item's **trust** is derived from its evidence (`unsourced | verified | assumed | unknown | mixed`), never stored. Verified claims on a `low`/`unknown`-reliability source are flagged.
- **Retrieval** (`core/knowledge.py`): keyword scoring (ILIKE on words of 3+ letters, escaped, top N), no embeddings, no model. Always `WHERE business_id = <this business>`. Global notes (`business_id NULL`) appear only with `include_global: true` and are labelled `global`. No cross-business search exists (Phase 11).
- **Command Center integration:** knowledge/research/evidence context is retrieved for the request (best match, else most recent) from that business only. Each item is shown to the model with its trust/label. A claim the model labels `verified` is kept only if its cited source is in the supplied context and is not itself assumed/unknown: citing an assumed evidence row gives `assumed`; an unsourced note gives `assumed`. This **changes Phase 7 behaviour**: a knowledge note cited as `verified` is now downgraded unless it has verified evidence.
- **Citations:** every claim of a parsed answer is stored in `ai_citations` (claim, label, cited source id) linked to the `ai_usage` row. Discarded (`bad_output`) answers store none.
- **Request body limit:** the server read limit was 4 KiB (`MAX_BODY`), too small for prompts. Added `READ_LIMIT = 48_000` in `dashboard/app.py`, used by `serve` and `api/index.py`; each route still enforces its own smaller limit (login/AI stay at 4 KiB, CRUD at 8 KiB, lab at 40 KB).

### Work completed
- Migration `014_prompt_lab_knowledge.sql` (additive; first normalises any multiple-active prompts so the unique index can be created), rollback `database/rollback/014_prompt_lab_knowledge_down.sql` (drops Phase 8 data).
- `core/prompt_lab.py`, `core/knowledge.py`, `dashboard/lab_api.py`; edits to `core/ai.py`, `core/ai_config.py` (evidence in `research_summary`/`draft_content` context), `core/founder.py` (entities `sources`, `evidence`; prompt restrictions; evidence rules), `dashboard/app.py`, `api/index.py`.
- API (owner auth): `GET/POST /api/lab/prompts`, `GET /api/lab/prompts/<id>`, `POST /api/lab/prompts/sync`, `.../<id>/activate`, `.../<id>/evals`, `POST /api/lab/compare`, `GET /api/knowledge/<slug>`, `POST /api/knowledge/<slug>/search`, plus CRUD `sources`, `evidence`. (Search and compare are POST because the server strips query strings.)
- UI: new **Lab** page (`dashboard/static/js/lab.js`, nav "Lab", service-worker cache `z2r-shell-v10`): Knowledge tab (business picker, search with opt-in global notes, research/notes with trust pills, claims, verify-with-source, sources) and Prompts tab (versions, view, score, new version, compare, activate, register files).

### Files
- Created: `core/prompt_lab.py`, `core/knowledge.py`, `dashboard/lab_api.py`, `dashboard/static/js/lab.js`, `database/migrations/014_prompt_lab_knowledge.sql`, `database/rollback/014_prompt_lab_knowledge_down.sql`, `tests/unit/test_lab_knowledge.py`.
- Modified: `core/ai.py`, `core/ai_config.py`, `core/founder.py`, `dashboard/app.py`, `dashboard/founder_api.py`, `dashboard/pages/index.html`, `dashboard/static/js/main.js`, `dashboard/static/sw.js`, `api/index.py`, docs.
- Removed: none.

### Tests
| Command | Result | Status |
|---|---|---|
| `pip install "psycopg[binary]>=3.2" --break-system-packages` | worked (PyPI reachable) | PASS |
| `python3 -m unittest discover -s tests -t .` before changes (local Postgres 16) | 348 OK | PASS |
| same command after changes | **367 OK** (19 new in `tests/unit/test_lab_knowledge.py`: immutable versions, trigger and unique index, generic-CRUD lock-down, diff and evidence threshold, command-center marker check, file sync and drift, active version used by `ai.run` with GUARD and `prompt_ref`, API flow and auth, verified-needs-source, cross-business references rejected, promotion audited, trust derivation, business-scoped search and opt-in global, LIKE/quote safety, retrieval for the request, assumed evidence cited as verified downgraded, citations stored, unsourced note not verified, no citations on bad output, migration repairs multiple active prompts) | PASS |
| Browser smoke on a throwaway local DB, 390 px wide, `AUTH_DISABLED=1`: Lab page loads, sources/evidence/notes render, search returns results, Prompts tab shows the registered file, no horizontal scroll, no JS errors | | PASS (partial: forms/dialogs, activate, compare drawer, desktop/tablet widths not exercised) |
| Any real Anthropic call using a Lab prompt, real token usage, real citation behaviour of a real model | **never executed** | NOT TESTED |
| Migration 014 on Neon, any preview/production URL | not applied, not opened | NOT TESTED |

### Acceptance criteria
- Prompt versioning and comparison: PASS (diff + manual scores; no model-run comparison, see Unfinished work)
- Research capture with sources and verified/assumed/unknown labels: PASS
- Per-business knowledge stores, retrieval scoped by business: PASS (keyword retrieval only; relevance quality is unmeasured)
- Citation and evidence tracking: PASS in tests with a fake client; whether real models cite source ids correctly is NOT TESTED
- UI: PARTIAL (smoke only, no accessibility pass)

### Discrepancies found at start of phase
- `CONTINUE_FROM_HERE.md` said 325 tests; the correct baseline after Phase 7 was 348 (confirmed).
- The server read only 4 KiB of a request body, so large bodies were silently truncated before route limits; fixed with `READ_LIMIT`.

### Known issues and technical debt
- A prompt version does not change the code that parses its output: a Lab prompt that asks for another format will just produce `bad_output` (billed). The marker check is a floor, not a guarantee.
- Search is keyword-only (English-ish tokens, 3+ letters, no stemming/synonyms). Evidence of a retrieved note is not auto-included; only evidence matching the request is.
- `sources` have no dedupe, and a source's `reliability` is the founder's judgement, not checked.
- Evidence `verified` means "has a source", not "the source says that": nothing verifies quotes against URLs.
- The old `research.source_url` and `knowledge.source_url` fields remain and are not linked to `sources` (kept to avoid breaking Phases 3-6).
- Prompts for other names (`scout-enrich-v1`, business prompts) are not registered or resolved through the Lab; only `command-center` is wired. Business-scoped prompts are stored but never auto-selected.
- Migrations 007_a, 007, 008-014 are all unapplied on production Neon.
- Pushing this branch can itself trigger a Vercel preview build against the shared Neon database; the first API request to any deployment applies pending migrations, so do not open it before the backup.

### Decisions and assumptions
- Compare is manual-scored, not model-run, to avoid a second spend path outside the Command Center's budget and ledgers.
- "Trust" is computed, so an assumption can never be stored as a fact by editing a note.
- Unsourced knowledge notes are treated as `assumed` for the model (stricter than Phase 7; the founder can attach verified evidence to raise them).
- Search/compare are POST (query strings are stripped by the server).

### Unfinished work
- Run a prompt version against a test input through the Command Center and record the output as a scored eval (needs budget gating and a real key).
- Migrate Scout's prompt and any future prompts under the Lab; business-specific prompt selection.
- Link legacy `source_url` to `sources`; quote/URL verification; staleness (re-check dates) for verified evidence.
- Command Center UI/conversation persistence, approval prompts, quality feedback (still Phase 7 gaps).
- First real model call (see below).

### Next phase
Phase 9: Experiment and Growth Engine, **not started**. Before it: founder Neon backup + "apply to Neon" (migrations 007_a, 007, 008-014). To verify Phases 7-8 for real: in a throwaway environment set `ANTHROPIC_API_KEY`, a small `LLM_MONTHLY_BUDGET_USD`, and `LLM_PRICE_*` from the provider's pricing page, add one verified and one assumed evidence row, make one `POST /api/ai/run` with a research request, then check `llm_usage`, `ai_usage.prompt_ref` and `ai_citations`.

### Ready-to-paste next-chat instruction
```
Repo: anjuneedham/Zero-to-revenue- (attach with add_repo, push access). Phases 0-8 live on branch ccr-edf0723c-id0y6l (check the latest commit with git log; Phase 8 head). They are NOT on the default branch. Check that branch out, then create a new branch from it for this work. Do not push to ccr-edf0723c-id0y6l or ccr-79ad6026-fa1uuh: pushes auto-deploy a Vercel preview against the shared Neon database.
Read, in order: docs/CONTINUE_FROM_HERE.md, docs/FOUNDER_OS_BUILD_PROTOCOL.md, docs/PHASE_HANDOFF.md (Phase 8 entry first), docs/FOUNDER_OS_ARCHITECTURE.md. The correct test baseline after Phase 8 is 367.
Verify first: start local Postgres 16 per the recipe in CONTINUE_FROM_HERE.md; check that pip install "psycopg[binary]>=3.2" --break-system-packages works (if PyPI is blocked, stop and tell me); run python3 -m unittest discover -s tests -t . (expect 367 OK); inspect core/founder.py, core/workspace.py, core/ai.py, core/knowledge.py, core/prompt_lab.py and the experiments table/entity from migrations 007 and 008.
Do not open or request any preview/production URL of this branch until I say the Neon backup is done.
Implement only Phase 9: Experiment and Growth Engine (protocol section 9): hypothesis, metric, duration, result and decision records; experiment lifecycle; growth funnels from real data; learnings written back to business knowledge (as evidence-labelled notes, never as verified without a source). Out of scope: automated execution of experiments without approval, cross-business synthesis. Do not start Phase 10.
ANTHROPIC_API_KEY may still be missing: do not claim any model call works unless it was executed; mark model-dependent items NOT TESTED.
Finish by updating docs/PHASE_HANDOFF.md (Phase 9 entry on top, honest PASS/PARTIAL/NOT TESTED, ready-to-paste Phase 10 block) and docs/CONTINUE_FROM_HERE.md, then stop.
```

---

## Phase 7: AI Command Center. Completed 2026-10-29

**Overall status: PARTIAL.** Routing, context, structured output, budget and ledgers are built and tested with a fake client (348 tests). **No real model call has ever been executed**: `ANTHROPIC_API_KEY` and `LLM_*` pricing are not set in this environment, so `AnthropicClient` is untested against the live API. Not applied to production Neon (awaiting founder backup + approval); no lint/type/build tooling. No UI and no conversation persistence were built (see Unfinished work).
**Branch:** `ccr-79ad6026-fa1uuh`, stacked on Phase 6 (`ccr-9e3eecee-aucmfd`). Phases 0-6 were found on that branch after the first attempt looked in the wrong place.

### Objective
One orchestration layer for every Founder OS model call: classify the task, route it to NO AI / LOW / STANDARD / HIGH from one config file, give the model only that business's records, require a strict JSON reply, log usage to the existing ledgers, and stop at a hard budget.

### Design (verify these first)
- **One config location:** `core/ai_config.py` holds the level -> model map (`claude-haiku-5-5` / `claude-sonnet-5-5` / `claude-opus-5-5`, each overridable with `LLM_MODEL_LOW|STANDARD|HIGH`), token limits per level, the task-type table (level, context kinds, stakes) and the keyword rules. Business code never names a model.
- **Classification is code, not a model.** `ai.classify` uses the caller's `task_type` if given, else keyword rules, else `general_question`. Stakes words (live trading, real money, invest, publish, delete...) raise the level one step and force `needs_approval`; keywords can only add caution. `min_level` lets the caller escalate manually (no automatic escalation yet).
- **NO AI never reaches a model** and writes no ledger row. Currently only the `calculation` task type routes there.
- **Business isolation:** `ai.select_context` runs `WHERE business_id = <this business>` for goals, tasks, KPIs, blockers, decisions, knowledge, research, trading strategies and runs. Global (`business_id IS NULL`) rows are NOT included. Each row carries a source id such as `goals:goal_x`. Records go to the model inside `<data>`, the request inside `<untrusted>`; the prompt (`prompts/ai/command-center-v1.md`) says to ignore instructions there.
- **Structured output:** strict envelope `{answer, claims[{text,label,source}], next_steps, needs_approval, fields}`. Anything else is discarded (`bad_output`, still billed and logged). A claim labelled `verified` without a source id from the supplied context is downgraded to `unknown`. Guarantee/risk-free language adds a warning. The result is advisory: nothing is executed.
- **Hard budget:** reuses and extends `core/budget.py`. Each call reserves its worst-case cost under the advisory lock before the call, so the monthly cap (`LLM_MONTHLY_BUDGET_USD`, shared with Scout) cannot be overshot. Added: optional per-level prices `LLM_PRICE_IN|OUT_PER_MTOK_<LOW|STANDARD|HIGH>` (fall back to the global pair, so Scout is unchanged). Disabled (no row, no call) unless key, cap and prices are set. A client exception keeps the worst-case hold (`FAILED`). The kill switch pauses all calls.
- **Ledgers:** every attempted call writes one `llm_usage` row (agent `command_center`; this is the row the cap counts) and one `ai_usage` row (business-scoped) with routing level, task type, latency, outcome (`ok|bad_output|error`) and the `llm_usage` id. Error rows record the held worst-case cost. The Founder Dashboard's "Scout (llm_usage)" source now excludes `command_center` rows so one call is not shown twice.

### Work completed
- Migration `013_ai_command_center.sql` (additive columns on `ai_usage`), rollback `database/rollback/013_ai_command_center_down.sql`.
- `core/ai_config.py`, `core/ai.py` (`classify`, `select_context`, `build_prompt`, `parse_reply`, `AnthropicClient`, `run`, `status`), `prompts/ai/command-center-v1.md`.
- API (owner auth required): `GET /api/ai/status`, `POST /api/ai/classify` (no model), `POST /api/ai/run {business, request, task_type?, min_level?}` returning `status` = `ok | no_ai | disabled | paused | budget_exceeded | bad_output | error`. Errors are generic.
- `core/budget.py` extended (backward compatible); `core/founder_dashboard.py` ledger note/filter.

### Files
- Created: `core/ai.py`, `core/ai_config.py`, `prompts/ai/command-center-v1.md`, `database/migrations/013_ai_command_center.sql`, `database/rollback/013_ai_command_center_down.sql`, `tests/unit/test_ai.py`.
- Modified: `core/budget.py`, `core/founder_dashboard.py`, `dashboard/app.py`, docs.
- Removed: none.

### Tests
| Command | Result | Status |
|---|---|---|
| Local Postgres 16 per the recipe, before changes | 325 OK | PASS |
| `python3 -m unittest discover -s tests -t .` after changes | **348 OK** (23 new in `test_ai.py`: routing and escalation, single-config models, strict parsing and verified-claim downgrade, NO AI makes no call, disabled makes no call/row, both ledgers on success, business and global-row isolation, trading validation scope, bad output, client error keeps hold, hard cap incl. Scout spend, per-level prices, kill switch, injection, API auth/errors) | PASS |
| Real Anthropic API call, real model ids, real token/usage fields, real pricing | **never executed** (no key, no prices; tests use a fake client) | NOT TESTED |
| Any preview/production URL, production Neon, migration 013 on Neon | not opened, not applied | NOT TESTED |

### Acceptance criteria
- Task classification: PASS (deterministic rules; accuracy beyond the tested examples is unmeasured)
- One config for NO AI/LOW/STANDARD/HIGH: PASS (`core/ai_config.py`)
- Business-scoped context: PASS for the listed record types
- Structured outputs: PASS (strict envelope, source-traced `verified`)
- Usage logging to existing ledgers + hard budget: PASS in tests with a fake client; token counts, cost and cap are only as right as the real SDK usage fields and your `LLM_PRICE_*` values
- Command/chat UI, tool access scoped by business, approval prompts, conversation/task persistence (protocol Phase 7 list): NOT BUILT
- Quality tracking (protocol wants it "when the architecture supports it"): NOT BUILT (no thumbs/outcome feedback; only ok/bad_output/error)

### Known issues and technical debt
- `AnthropicClient` is unverified; model ids come from the project's model list and the existing Scout config, not from a live check. `ClaudeClient` in Scout still reads `CLAUDE_MODEL` separately (left alone: out of scope).
- Token estimate is characters/3 (deliberately high). The reservation uses the full estimated prompt, so each call reserves slightly more than it uses until settled.
- A call that overshoots `max_tokens` is cut by the API; the reply then fails parsing and is discarded as `bad_output`.
- Keyword classification is crude (English only, substring match). Stakes words can over-flag.
- No cross-business opt-in path exists yet (by design: Phase 11).
- Migrations 007_a, 007, 008-013 are all unapplied on production Neon.

### Decisions and assumptions
- Escalation is manual (`min_level`) rather than automatic retry, to avoid hidden spend.
- Failed calls are logged at worst-case cost (fail safe), which can overstate spend.
- Ledger split: `llm_usage` enforces the cap, `ai_usage` answers "per business"; the dashboard avoids double display.

### Unfinished work
Command Center UI and conversation/task persistence; approval prompts wired to the existing approval gates; per-business tool scoping; output-quality feedback; first real call (see below). Phase 8 (Prompt Lab) must take over `prompts/ai/` versioning.

### Next phase
Phase 8: Prompt Lab, Research, and Knowledge, **not started**. Before it: founder Neon backup + "apply to Neon"; to verify Phase 7 for real, set `ANTHROPIC_API_KEY`, `LLM_MONTHLY_BUDGET_USD` (small, e.g. 1) and `LLM_PRICE_*` from the provider's pricing page in a throwaway environment, then make one `POST /api/ai/run` and check the two ledger rows.

### Ready-to-paste next-chat instruction
```
Read /docs/CONTINUE_FROM_HERE.md, then /docs/FOUNDER_OS_BUILD_PROTOCOL.md, then /docs/PHASE_HANDOFF.md (Phase 7 entry first) and /docs/FOUNDER_OS_ARCHITECTURE.md.
Verify first: tests against a throwaway Postgres (expect 348 OK); inspect core/ai.py, core/ai_config.py, core/budget.py.
Do not open any preview/production URL until I say the Neon backup is done.
Implement only Phase 8: Prompt Lab, Research, and Knowledge. Do not claim a model call works unless it was executed. Update /docs/PHASE_HANDOFF.md and stop.
```

---

## Phase 6: Trading Workspace. Completed 2026-10-29

**Overall status: PARTIAL.** Built and tested locally (325 tests + browser check at 3 sizes). Not applied to production Neon (awaiting founder approval + backup); no lint/type/build tooling. Phase 5 was reviewed first (no defects found).
**Branch:** `ccr-9e3eecee-aucmfd` (stacked, PR #1).

### Objective
Research-and-paper-trading workspace for the trading project: hypotheses, strategies, data notes, test results, risk limits, explicit failure conditions, with a hard human-approval boundary.

### Safety design (verify these first)
- **No live trading exists.** `trading_runs.mode` allows only backtest / out_of_sample / walk_forward / paper and `trading_strategies.status` has no live/deployed value; both are enforced by API enums AND database CHECK constraints (a test inserts `live` directly and the database refuses it). Nothing in the system places orders or reads a broker/exchange.
- Modes are never combined or averaged. Runs are **append-only** (edits are rejected); corrections are new results.
- The workspace never scores a strategy or predicts profit. For each strategy it lists the research steps still missing and any breached recorded failure condition, and its verdict text says that even a complete checklist is not a prediction and that live trading is outside the system. A permanent "Research only" banner appears on the page.

### Work completed
- Migration `012_trading_research.sql`: `trading_strategies` (hypothesis, instrument, stage, data notes, risk notes, failure conditions, max-drawdown limit %, min trades) and `trading_runs` (mode, period, trades, net return %, max drawdown %, costs included, cost bps, slippage bps, data source, params, notes).
- `core/trading_eval.py`: `run_warnings` (too few trades, costs not confirmed, no slippage assumption, no drawdown, "positive in-sample backtest is not evidence") and `evaluate` (breached drawdown limit, 9-item research checklist incl. data-quality notes, failure conditions, costed backtest, out-of-sample, walk-forward, paper run of >= 30 days). Thresholds (30 trades, 30 paper days) are documented rules of thumb, not statistical guarantees.
- `workspace(conn, "trading")` adds `research_lab`; UI `dashboard/static/js/trading.js` (`#trading`: Overview, Strategies, Notes).

### Files
- Created: `database/migrations/012_trading_research.sql`, `database/rollback/012_trading_research_down.sql`, `core/trading_eval.py`, `dashboard/static/js/trading.js`, `tests/unit/test_trading.py`.
- Modified: `core/founder.py` (2 entities), `core/workspace.py`, `main.js`, `index.html`, `sw.js`, docs.
- Removed: none.

### Tests
| Command | Result | Status |
|---|---|---|
| `python3 -m unittest discover -s tests -t .` (local Postgres 16) | **325 OK** (10 new in `test_trading.py`: evaluation rules, no-profit-claim verdict, breach detection, live mode/status rejected by API and DB, append-only runs, isolation, validation) | PASS |
| Headless Chromium, 3 tabs x phone/tablet/desktop | 0 px overflow, 0 console errors; breach shown, result recorded; no `live` option exists in the form | PASS |
| The existing MQL5 EA (`mq5` repo), real market data, any broker | not touched or verified | NOT TESTED |

### Acceptance criteria
- Hypotheses, strategies, data notes, backtests, validation, risk, paper trading, failure conditions: PASS (records only)
- Backtest / paper / live separated; live needs human approval: PASS by construction (live does not exist; a future phase must add an explicit approval flow)
- No profitability claims: PASS (copy and tests)
- Code and data pipeline management, parameter-sensitivity and robustness analysis, liquidity assumptions: NOT BUILT (only free-text `params`/`data_source` fields; no stored curves or statistics)
- Import of real results from MT5/exports: NOT BUILT (manual entry; numbers are only as good as what the founder types)

### Known issues and technical debt
- Results are self-reported; nothing verifies them against data. Drawdown breach uses only recorded runs.
- No tracking of strategy code versions or parameter sets beyond text.
- Migrations 007_a, 007, 008, 009, 010, 011, 012 are all unapplied on production Neon.

### Decisions and assumptions
- Conservative on purpose: omit rather than disable live mode; append-only results; checklist instead of a score.

### Unfinished work
Robustness/parameter-sensitivity records, result import, strategy code/version links, a formal live-authorization design (only if the founder later asks for it, in its own phase, with risk limits and a verified kill switch).

### Next phase
Phase 7: AI Command Center. Prerequisites: `ANTHROPIC_API_KEY` and pricing env vars are not set in this environment, so model calls cannot be tested here (the existing Scout budget code in `core/budget.py` already fails closed without them). Founder approval + Neon backup before any deployment is requested.

### Ready-to-paste next-chat instruction
```
Read /docs/FOUNDER_OS_BUILD_PROTOCOL.md (sections 5 and 7), then /docs/PHASE_HANDOFF.md (Phase 6 entry first), then /docs/FOUNDER_OS_ARCHITECTURE.md.
Verify first: tests against a throwaway Postgres (expect 325 OK); inspect core/budget.py, core/workspace.py, core/founder.py, agents/scout/enrich.py (the only existing model caller), migrations 004 and 007-012.
Preview and production share one Neon database and migrate on first request: do not open any preview/production URL until I approve and back up Neon.
Implement only Phase 7: AI Command Center (task classification, NO AI/LOW/STANDARD/HIGH routing config in one place, context selection scoped by business, structured outputs, usage logging to the existing ledgers, hard budget). Do not claim any model integration works unless it was actually called. Update /docs/PHASE_HANDOFF.md and stop.
```

---

## Phase 5: Fashion Workspace. Completed 2026-10-29

**Overall status: PARTIAL.** Built and tested locally (315 tests + browser check at 3 sizes). Not applied to production Neon (awaiting founder approval + backup); no lint/type/build tooling. Phase 4 was reviewed first (no defects found).
**Branch:** `ccr-9e3eecee-aucmfd` (stacked, PR #1).

### Objective
Consumer/e-commerce workspace for the founder's brand (Yaad n Abroad: "Pain into Art", Jamaican-inspired wear): products, margins, inventory, sales, campaigns, content, customer feedback. No SaaS metrics.

### Work completed
- Migration `011_shop.sql`: `shop_products` (stage idea/sampling/ready/live/discontinued, unit cost, price, currency, stock, reorder point), `shop_sales` (units, revenue, currency, channel, customer reference), `shop_campaigns` (spend, attributed revenue, orders). Also updates the `fashion` business **description** to the brand name the founder gave (only if it still holds the Phase 1 "not confirmed" text; name/slug/id unchanged).
- `core/workspace.py`: `shop` section for `fashion` plus tested helpers `product_view` (margin % only when price and cost exist; stock value; out-of-stock / reorder / below-cost flags), `sales_summary` (revenue per currency, never mixed; average order value; last 30 days; repeat customers only when a customer reference is on each sale; unvalued orders counted), `campaign_view` (ROAS and cost per order only when the inputs exist).
- Content tracking and customer feedback (feedback -> task) from Phase 3 are reused unchanged for Fashion (business-scoped).
- UI `dashboard/static/js/fashion.js` (`#fashion`: Overview, Products, Sales, Campaigns, Content, Customers, Notes); shared Overview/Notes/Content/Feedback via `Z.ws`.

### Files
- Created: `database/migrations/011_shop.sql`, `database/rollback/011_shop_down.sql`, `dashboard/static/js/fashion.js`, `tests/unit/test_shop.py`.
- Modified: `core/founder.py` (3 entities; `no_updated_at` support; sale timestamp default), `core/workspace.py`, `dashboard/static/js/buildflow.js` (content/feedback parametrised by business), `main.js`, `index.html`, `sw.js`, docs.
- Removed: none.

### Tests
| Command | Result | Status |
|---|---|---|
| `python3 -m unittest discover -s tests -t .` (local Postgres 16) | **315 OK** (12 new in `test_shop.py`: margin/stock math and flags, currency-safe sales, repeat customers, ROAS inputs, end-to-end flow, validation, isolation, brand description, reuse of content/feedback) | PASS |
| Headless Chromium, 7 tabs x phone/tablet/desktop | 0 px overflow, 0 console errors; margin shown, product added via the form | PASS |
| Production Neon, a real storefront (Shopify/Netlify), payment/ad platforms | not exercised | NOT TESTED |

### Acceptance criteria
- Brand, products, customers/feedback, content, campaigns, pricing, inventory, margins, sales, experiments, decisions: PASS (manual entry)
- Brand positioning / research: PARTIAL (only via the shared Notes/Research entities; no dedicated positioning view)
- Margins treat shipping, fees, returns, tax: NOT BUILT (margin is price minus unit cost only; stated on screen)
- Storefront/payments/ads integration: NOT BUILT (the audit found two storefront repos, neither confirmed as this brand)
- Business isolation: PASS (tested)

### Known issues and technical debt
- Everything is manual entry; sales are not pulled from any store. Attribution of campaign revenue is the founder's judgement.
- No per-size/variant inventory; one stock number per product. No delete UI.
- Migrations 007_a, 007, 008, 009, 010, 011 are unapplied on production Neon.

### Decisions and assumptions
- The brand name was taken from the founder's brief; the `fashion` row keeps its short name "Fashion" to avoid breaking references. Currency is never mixed. SaaS metrics are deliberately absent.

### Unfinished work
Variants/sizes, landed-cost margin (shipping, fees, returns), store integration, positioning workspace.

### Next phase
Phase 6: Trading Workspace. Prerequisites: founder approval + Neon backup before any deployment is requested. Safety: backtest, paper and live must be separate modes; live requires explicit human approval; nothing may imply profitability.

### Ready-to-paste next-chat instruction
```
Read /docs/FOUNDER_OS_BUILD_PROTOCOL.md (section 7 safety rules especially), then /docs/PHASE_HANDOFF.md (Phase 5 entry first), then /docs/FOUNDER_OS_ARCHITECTURE.md.
Verify first: tests against a throwaway Postgres (expect 315 OK); inspect core/workspace.py, core/founder.py, dashboard/static/js/{buildflow,agriloop,fashion}.js, migrations 007-011.
Preview and production share one Neon database and migrate on first request: do not open any preview/production URL until I approve and back up Neon.
Implement only Phase 6: Trading Workspace (slug 'trading'): hypotheses, strategies, data, backtests, validation, risk, paper trading, explicit failure conditions, human-approval boundary for live trading. No profitability claims. Update /docs/PHASE_HANDOFF.md and stop.
```

---

## Phase 4: Agriloop Workspace. Completed 2026-10-29

**Overall status: PARTIAL.** Built and tested locally (303 tests + browser check at 3 sizes). Not applied to production Neon (awaiting founder approval + backup); no lint/type/build tooling. Phase 3 was reviewed before starting (no defects found; its handoff lists its limits).
**Branch:** `ccr-9e3eecee-aucmfd` (stacked, PR #1).

### Objective
Agriloop marketplace workspace: farmers, buyers, supply, demand, matching, transactions, retention, partner-opportunity validation, using only recorded data.

### Work completed
- Migration `010_marketplace.sql`: `market_parties` (role farmer|buyer, stage lead/onboarded/active/churned), `market_listings` (supply, must belong to a farmer), `market_demand` (buyer requests, must belong to a buyer), `market_transactions` (proposed/agreed/completed/cancelled). Business-scoped; money rows carry their own currency.
- `core/workspace.py`: `marketplace` section for `agriloop` (funnel by role/stage, liquidity per product, suggested matches, deal summary, repeat buyers). Pure, tested helpers `suggest_matches`, `liquidity`, `transaction_summary`.
- Matching is rule-based and labelled **inference**: same product (case-insensitive) required; a known location mismatch or a known price above the buyer's max (same currency) rules a pair out; unknown fields neither help nor hurt and are listed as unknowns. Score = 50 base + location/price/quantity evidence. One click records a *proposed* deal; nothing is auto-confirmed.
- Money: completed deal value is summed per currency, never across currencies; completed deals without an amount/currency are counted but not valued.
- Partner hypothesis: knowledge notes tagged `partner-hypothesis` render as "HYPOTHESIS, not validated"; nothing about a partner is stored as fact.
- UI `dashboard/static/js/agriloop.js` (`#agriloop`: Overview, Supply & demand, Matches, Deals, People, Notes). Overview/Notes are shared with BuildFlow via `Z.ws`. Side-nav entry; phones reach it from the Founder business card.

### Files
- Created: `database/migrations/010_marketplace.sql`, `database/rollback/010_marketplace_down.sql`, `dashboard/static/js/agriloop.js`, `tests/unit/test_marketplace.py`.
- Modified: `core/founder.py` (4 entities, party-role check, `occurred_at` stamping), `core/workspace.py`, `dashboard/static/js/buildflow.js` (shared helpers, `Z.ws`), `main.js`, `index.html`, `sw.js`, docs.
- Removed: none.

### Tests
| Command | Result | Status |
|---|---|---|
| `python3 -m unittest discover -s tests -t .` (local Postgres 16) | **303 OK** (12 new in `test_marketplace.py`: matching rules, liquidity, currency-safe money, end-to-end flow, farmer/buyer role enforcement, cross-business rejection, validation, repeat buyers) | PASS |
| Headless Chromium, 6 tabs x phone/tablet/desktop | 0 px overflow, 0 console errors; match shown, add farmer via form | PASS |
| Production Neon, the real Agriloop product/data source, real users | not exercised | NOT TESTED |

### Acceptance criteria
- Farmers/buyers/supply/demand/matching/transactions views: PASS
- Retention: PARTIAL (funnel stage and repeat-buyer count only; no cohort or time-based retention)
- Partner opportunity as hypothesis: PASS (tag-based; no formal validation workflow, see Phase 9)
- Experiments/metrics/decisions: PASS (shared Overview/Notes)
- Business isolation: PASS (tested)
- Geographic expansion: NOT BUILT (location is free text; no parish/region model or expansion tracking)
- Integration with the live Agriloop product: NOT BUILT (audit says its marketplace may be on an in-memory store; unverified)

### Known issues and technical debt
- All data is manual entry. Matching is naive text equality on product names (no synonyms, units are not converted).
- No edit for all fields of listings/requests; no delete UI.
- Migrations 007_a, 007, 008, 009, 010 are all unapplied on production Neon.

### Decisions and assumptions
- Matching is a suggestion list, never an automatic action. Currency never mixed. A proposed deal is the only thing the UI creates from a match.

### Unfinished work
Geography model, retention cohorts, product integration, unit conversion/product catalogue, partner validation workflow.

### Next phase
Phase 5: Fashion Workspace ("Yaad n Abroad": Pain into Art, Jamaican-inspired wear). Prerequisites: founder approval + Neon backup before any deployment is requested. The `fashion` business row is named "Fashion" with a description that says the brand is unconfirmed; updating it to the real brand name is a data change for the founder to approve.

### Ready-to-paste next-chat instruction
```
Read /docs/FOUNDER_OS_BUILD_PROTOCOL.md, then /docs/PHASE_HANDOFF.md (Phase 4 entry first), then /docs/FOUNDER_OS_ARCHITECTURE.md.
Verify first: tests against a throwaway Postgres (expect 303 OK); inspect core/workspace.py, core/founder.py, dashboard/static/js/{buildflow,agriloop}.js, migrations 007-010.
Preview and production share one Neon database and migrate on first request: do not open any preview/production URL until I approve and back up Neon.
Implement only Phase 5: Fashion Workspace (slug 'fashion'): consumer/e-commerce, NOT SaaS metrics. Reuse the workspace pattern. Update /docs/PHASE_HANDOFF.md and stop.
```

---

## Phase 3: BuildFlow Workspace. Completed 2026-10-29

**Overall status: PARTIAL.** Built, tested (291 tests) and exercised in a real browser against a local Postgres 16. Not applied to or verified on production Neon (still awaiting founder approval + backup); no lint/type/build tooling exists.
**Branch:** `ccr-9e3eecee-aucmfd` (stacked on Phase 2, same PR #1). Phase 2 was reviewed first: no defects found in its code (the automated review only flagged pre-existing planning docs, not this work).

### Objective
Priority-1 business workspace: objectives, KPIs, tasks, blockers, experiments, decisions, knowledge/constraints, plus a measurable content workflow and a customer-feedback-to-action workflow, scoped to BuildFlow only.

### Work completed
- Migration `009_workspace_content_feedback.sql`: `content_items` (platform, topic, hook, format, status, posted_at, url, views/likes/comments/shares/signups, all NULL until recorded) and `feedback_items` (source, contact, body, kind, status, `work_task_id`). Business-scoped, so Phases 4-5 can reuse them.
- `core/workspace.py` + `GET /api/founder/workspace/<slug>`: per-business read model (generic for any slug; BuildFlow adds the legacy `leads` pipeline counts). Sections fail independently. Nothing from another business is returned (tested).
- Content workflow: add idea -> update to posted + record metrics. Summary shows posted today / last 7 days / posted-without-metrics and breakdowns by platform, format and topic. Averages use ONLY posts with recorded views and carry a small-sample caveat; no targets are invented.
- Feedback workflow: log feedback -> "Create task" (`POST /api/founder/feedback-items/<id>/to-task`, atomic and idempotent, same business) or triage/dismiss.
- "Import launch plan as tasks": creates work tasks once each from the owner's own `plan.json` (BuildFlow launch plan), honouring ticked items. Only runs when clicked.
- UI `dashboard/static/js/buildflow.js`: page `#buildflow` with Overview / Content / Feedback / Pipeline / Notes tabs. Side-nav entry; on phones reach it from the Founder business card ("Open workspace") to keep the tab bar at 6 items. Form builder from Phase 2 refactored into reusable `Z.formDialog`.

### Files
- Created: `core/workspace.py`, `dashboard/static/js/buildflow.js`, `database/migrations/009_workspace_content_feedback.sql`, `database/rollback/009_workspace_content_feedback_down.sql`, `tests/unit/test_workspace.py`.
- Modified: `core/founder.py` (entities `content_items`, `feedback_items`, `feedback_to_task`, `posted_at` stamping), `dashboard/founder_api.py` (to-task route), `dashboard/app.py` (workspace routes), `dashboard/static/js/founder.js` (reusable form dialog, workspace link), `main.js`, `index.html`, `sw.js`, `tests/unit/test_founder_dashboard.py`, docs.
- Removed: none.

### Tests
| Command | Result | Status |
|---|---|---|
| `python3 -m unittest discover -s tests -t .` (local Postgres 16) | **291 OK** (13 new in `test_workspace.py`: content math, isolation, content flow, feedback-to-task idempotency, plan import, legacy leads, section failure, auth) | PASS |
| Headless Chromium, 5 tabs x phone/tablet/desktop | 0 px overflow, 0 console errors; feedback->task, plan import, add content verified | PASS |
| Production Neon, deployed site, real BuildFlow product, social platform APIs | not exercised | NOT TESTED |

### Acceptance criteria
- Objectives/KPIs/tasks/blockers/experiments/decisions/knowledge views: PASS
- Measurable content workflow: PASS (manual metrics entry; no platform API integration)
- Feedback-to-action workflow: PASS
- Business isolation: PASS (tested)
- Customers/projects/contractor-discovery views: PARTIAL (only the legacy outreach `leads` counts exist; there is no BuildFlow customer/contractor data source, and no integration with the BuildFlow product was verified or built)
- Loading/empty/error states: PARTIAL (per-section error tested via API; browser error path not exercised)
- Mobile/tablet/desktop: PASS
- Tests: PARTIAL (no lint/type/build tools exist)

### Known issues and technical debt
- Content metrics are typed in by hand; nothing is pulled from YouTube/TikTok/Instagram/Facebook. Attribution of signups to a post is the founder's own judgement.
- No edit UI for goals/KPIs/knowledge; no BuildFlow product integration (read-only Firebase/Vercel metrics would be a future, separately verified step).
- Creates are not idempotent server-side (buttons disable while saving).
- `leads` stays a legacy table; the audit's plan to extend it into a prospect pipeline is not done.
- Migrations 007_a, 007, 008, 009 are all unapplied on production Neon. Preview and production share one database and migrate on first request.

### Decisions and assumptions
- Content/feedback tables are generic (business-scoped), BuildFlow-specific only in the UI. Decisions on the workspace show only that business's rows (cross-business ones stay on the Founder dashboard).
- Assumption: manual metrics are acceptable for now; platform APIs need separate verification.

### Unfinished work
Product integration, contractor/customer CRM, edit/delete UI, retirement of legacy agent pages.

### Next phase
Phase 4: Agriloop Workspace. Prerequisites: founder approval + Neon backup before any deployment is requested; confirm Agriloop's real data source (audit says marketplace may be on an in-memory store).

### Ready-to-paste next-chat instruction
```
Read /docs/FOUNDER_OS_BUILD_PROTOCOL.md, then /docs/PHASE_HANDOFF.md (Phase 3 entry first), then /docs/FOUNDER_OS_ARCHITECTURE.md.
Verify first: run the tests against a throwaway Postgres (expect 291 OK); inspect core/workspace.py, core/founder.py, dashboard/static/js/buildflow.js and migrations 007-009.
Preview and production share one Neon database and migrate on first request: do not open any preview/production URL until I approve and back up Neon.
Implement only Phase 4: Agriloop Workspace (slug 'agriloop'), reusing core/workspace.py and the Phase 3 patterns. Update /docs/PHASE_HANDOFF.md and stop.
```

---

## Phase 2: Founder Dashboard. Completed 2026-10-29

**Overall status: PARTIAL.** Built, tested against a local Postgres 16 and in a real browser; not verified on the real Neon database or the deployed site, and no lint/type/build tooling exists in the repo.
**Branch:** `ccr-9e3eecee-aucmfd` (PR #1). Merged here: Phase 0 branch `ccr-b2711e77-m8rmgm` (protocol, audit) and Phase 1 branch `ccr-61f6bbc1-7gtbiy` (data model + CRUD API).

### Objective
One mobile-first founder home across the four businesses: next-action recommendation, ranked tasks, blockers, goals/KPIs, experiments, AI usage, decisions, quick actions.

### Discrepancies found at start of phase (read this)
- My first Phase 2 pass was built on `main`'s base **without** the protocol, Phase 0 audit or Phase 1, because only the default branch was visible. It created its own tables (`ventures`, `founder_tasks`, ...) that collided with Phase 1's. It was rebuilt on Phase 1: its migration and API were deleted, and the dashboard now reads Phase 1 tables.
- **Production database side effect (needs founder awareness).** Preview and production share one Neon `DATABASE_URL` (verified via Vercel env list), and the first API request on any new deployment runs pending migrations. A preview of the first draft therefore applied the draft's `007_founder.sql` to **production Neon** (verified: its `/api/founder/dashboard` returned the seeded four businesses from the real DB; no user data in it). This was done without the approval the protocol requires. It is repaired by `007_a_retire_early_dashboard_schema.sql`, which renames (never drops) those tables to `early_*` before Phase 1's migration runs. Tested on a simulated copy of that state (`EarlyDraftRepairTest`); NOT yet run on Neon.
- Nothing from Phase 1 (007_founder_os_core) or 008 has run on production yet. Any request to a deployment of this branch (preview or production) will apply 007_a, 007_founder_os_core and 008 to the shared Neon DB. Take or verify a Neon backup/branch first; Neon PITR is unverified.

### Work completed
- `core/founder_dashboard.py`: read model + ranking + recommendation + KPI progress/trend. Each section is isolated, so one failing query shows an error card with Retry while the rest renders.
- `GET /api/founder/dashboard` (in `dashboard/app.py`, mounted before Phase 1's router). All writes reuse the Phase 1 API (`/api/founder/businesses/<slug>/<entity>`, `/api/founder/<entity>/<id>`, KPI readings); the dashboard adds no write endpoints.
- `dashboard/static/js/founder.js`: new first nav item "Founder" (default landing page): header + "What should I do next?", recommendation card (with founder override), four business cards, today's priorities (filters), blockers (recorded vs inferred), goals/KPIs, experiments, AI usage, decisions, quick actions.
- `AUTH_DISABLED=1` (local and Vercel preview only; ignored when `VERCEL_ENV=production`) skips login. Set on Vercel for the Preview of branch `ccr-9e3eecee-aucmfd` only. Preview has live PayPal/Gmail env and the shared DB: keep Vercel Deployment Protection on, and remove the variable when finished.

### Files
- Created: `core/founder_dashboard.py`, `dashboard/static/js/founder.js`, `database/migrations/007_a_retire_early_dashboard_schema.sql`, `database/migrations/008_founder_dashboard.sql`, `database/rollback/008_founder_dashboard_down.sql`, `tests/unit/test_founder_dashboard.py`, `tests/fixtures/early_007_founder.sql`, `docs/screenshots/founder-*.png`.
- Modified: `core/founder.py` (new columns on work_tasks/kpis/experiments, new `blockers` entity, `decided_at` and `resolved_at` handling), `dashboard/app.py`, `dashboard/pages/index.html`, `dashboard/static/js/main.js`, `core.js`, `css/app.css`, `sw.js`, `docs/PHASE_HANDOFF.md`, `docs/FOUNDER_OS_ARCHITECTURE.md`.
- Removed: none (the first draft's migration/tests/API never existed on the target base).

### Changes by area
- **Database (008, additive):** `businesses.priority` (backfilled 1-4); `work_tasks.impact, effort_hours, depends_on, expected_outcome, next_step`; `kpis.baseline_value, is_primary, period`; `experiments.baseline_value, target_value, review_date, next_action`; new `blockers` table. Rollback file is manual.
- **API:** one new read route; Phase 1 CRUD extended with the new fields and `blockers` entity (same-business checks apply to `depends_on` and `work_task_id`).
- **UI:** see above. **AI:** none; the recommendation is deterministic. **Integrations:** none new. AI usage reads `llm_usage` (Scout) and `ai_usage` (Phase 1, currently inert).

### Recommendation logic (all constants in `core/founder_dashboard.py`)
Score per open task: business priority `(lowest_rank - rank) * 6`; urgency overdue +30, today +25, <=3 d +20, <=7 d +12, later +4; your task priority 1-5 `(3 - p) * 3` (3 = neutral default); impact `5 * (1..5)`; effort <=1h +6, <=4h +3, >8h -3; doing +8; unblocks others +4 each (cap 12); serves an open goal +3. Tasks marked blocked, waiting on an unfinished task or with an open blocker are shown but never recommended; if all are blocked the oldest recorded blocker is recommended; with no tasks it lists what is missing. Evidence quality (high/medium/low) comes from missing impact/effort/due data. Limitations: heuristic weights, not an optimum; revenue potential and risk of inaction only enter through the impact field; no time-available input; the override ("choose it yourself") is stored per device in browser localStorage.

### Tests
| Command | Result | Status |
|---|---|---|
| `python3 -m unittest discover -s tests -t .` (local Postgres 16, `TEST_DATABASE_URL`) before changes | 236 OK | PASS |
| Same after merging Phase 1 | 252 OK (Phase 1 reported 252) | PASS |
| Same at end | **278 OK** (26 new in `test_founder_dashboard.py`: ranking, KPI math, auth, isolation, validation via API, section failure, AI usage, no-login flag, early-draft repair) | PASS |
| Headless Chromium at 390/820/1366 px, empty and populated data, no-login mode | 0 px overflow, 0 console errors; task created through the form, task marked done | PASS |
| Production Neon, deployed site, Gmail/PayPal, lint/type/build | not run (none exist / not exercised) | NOT TESTED |

### Acceptance criteria
- Reachable in the real app: PASS (local; preview exists but not re-verified after the rebuild)
- Four business cards from stored records and priorities: PASS (priority is `businesses.priority`)
- Data from the supported layer: PASS
- Priorities grounded in tasks with reasons: PASS
- Documented recommendation logic: PASS
- Founder override: PARTIAL (per device only)
- Blockers recorded vs inferred: PASS
- Goals/KPIs incl. bad baselines: PASS
- Experiments/decisions: PASS
- AI usage real or unavailable: PASS (unit-tested; not seen with live data)
- Visible quick actions work: PARTIAL (task form and status in browser; other forms via API tests only)
- Business isolation: PASS for cross-references; single-owner app, no per-business permissions
- Loading/empty/error/partial states: PARTIAL (skeleton, empty, per-section error unit-tested; failed-mutation toast and session expiry not browser-tested)
- Mobile/tablet/desktop: PASS
- Tests/build checks: PARTIAL (tests yes; lint/type/build do not exist)
- Regressions addressed: PASS (all prior tests green)
- Docs/handoff: PASS

### Known issues and technical debt
- Default landing page is now Founder. Mobile tab bar has 6 tabs.
- Creates are not idempotent server-side (buttons disable while saving); business priority has no UI (UPDATE `businesses.priority`).
- Tasks, goals, KPIs, experiments, decisions cannot be edited or deleted from the UI (the Phase 1 API can update them); no business detail pages; AI usage cannot be split per business for Scout's ledger.
- `early_*` tables on production (from the repair) can be dropped by the founder once confirmed empty.
- Phase 1 limits still apply (seed timestamps fixed, legacy agents/pages remain, Fashion brand unconfirmed).

### Decisions and assumptions
- Reuse Phase 1 tables; add only what the dashboard needs (008). Task `priority` default 3 is treated as neutral. Cross-business decisions (`business_id` NULL) are shown as "All businesses".
- Assumption: preview shares production Neon (verified from env list, not by querying the DB directly).

### Unfinished work
Edit/close UI, business workspaces (Phase 3+), per-business AI cost, lint/build pipeline, owner-approved application of 007/008 on Neon.

### Next phase
Phase 3: BuildFlow Workspace. Prerequisites: founder approves and backs up before migrations 007_a/007/008 reach Neon; enter real BuildFlow tasks/KPIs; PR #1 reviewed/merged; confirm the Fashion brand if relevant.

### Ready-to-paste next-chat instruction
```
Read /docs/FOUNDER_OS_BUILD_PROTOCOL.md, then /docs/PHASE_HANDOFF.md (Phase 2 entry first), then /docs/FOUNDER_OS_ARCHITECTURE.md and /docs/PHASE_0_AUDIT.md.
Verify the repo before changing anything: run the test suite against a throwaway Postgres (expect 278 OK) and inspect core/founder.py, core/founder_dashboard.py, dashboard/founder_api.py, dashboard/static/js/founder.js, database/migrations/007*, 008.
NOTE: preview and production share one Neon database and migrations run on the first request of any deployment. Do not open or request a preview/production URL of this branch until I have approved and backed up Neon.
Implement only Phase 3: BuildFlow Workspace (businesses.slug = 'buildflow'), reusing the Phase 1 entities and the Phase 2 dashboard patterns. Update /docs/PHASE_HANDOFF.md at the end and stop. Do not start Phase 4.
```

---

## Phase 1: Foundation and Architecture. Completed 2026-10-29 (original entry, preserved verbatim from branch `ccr-61f6bbc1-7gtbiy`)

## Read this first: Phase 0 docs were missing
`docs/FOUNDER_OS_BUILD_PROTOCOL.md`, `docs/PHASE_HANDOFF.md` (Phase 0 version) and `docs/PHASE_0_AUDIT.md` did **not exist**
on either remote branch (`ccr-61f6bbc1-7gtbiy`, `ccr-a240a1bc-iekqji`) or anywhere in history. So the Phase 0 handoff could
not be verified, and the build protocol was not followed because it could not be read. Repo state was used instead, plus
`IMPLEMENTATION_AUDIT.md` and `docs/master/HANDOFF.md` (the closest existing equivalents). **If the protocol exists
elsewhere, add it and check this phase against it.** Verified from the repo: the "three-agent foundation" is Scout /
Operator / Treasury (`agents/`, `agents` table CHECK constraint).

## What changed
- New Founder OS core data model (12 entities + `kpi_readings`), four seeded businesses, authenticated CRUD API, tests, docs.
- Additive only. Legacy agents, tables, dashboard pages, cron and tests are untouched (hence "replace" = new foundation
  added and legacy marked deprecated; deletion deferred, see strategy in `docs/FOUNDER_OS_ARCHITECTURE.md`).

## Database migrations
- `database/migrations/007_founder_os_core.sql` (auto-applied on next cold start / `db.migrate`): creates `businesses, projects,
  goals, work_tasks, kpis, kpi_readings, experiments, research, knowledge, decisions, prompts, ai_usage, automations`; seeds
  BuildFlow, Agriloop, Fashion, Trading (`biz_*` ids).
- `database/rollback/007_founder_os_core_down.sql`: manual, not auto-run (runner is forward-only).
- Naming: Founder OS Task = `work_tasks` because legacy `tasks` (agent queue) still exists.
- Not yet applied to production Neon; it applies itself on the first request after deploy. Back up/branch Neon first if wanted
  (PITR settings remain unverified per the earlier audit).

## Files
Added: `core/founder.py`, `dashboard/founder_api.py`, `database/migrations/007_founder_os_core.sql`,
`database/rollback/007_founder_os_core_down.sql`, `tests/unit/test_founder_os.py`, `docs/FOUNDER_OS_ARCHITECTURE.md`, this file.
Modified: `dashboard/app.py` (import + 3-line mount after session verification).

## APIs
`/api/founder/...` - full table in `docs/FOUNDER_OS_ARCHITECTURE.md`. Owner bearer token required; 8 KiB body cap.

## Tests
`tests/unit/test_founder_os.py` (16 tests: schema, idempotent migrate, seeds, auth, CRUD for all entities, validation,
cross-business parent check, KPI history, immutability, audit, automations default off). Full suite: **252 pass** (236
existing + 16) against local Postgres 16 via `TEST_DATABASE_URL`. Ran once, at the end, per the token policy.

## Known issues / limits
- Phase 0 docs missing (above).
- No UI for any of this yet; API only. The existing dashboard still shows the legacy agent pages.
- `ai_usage` and `automations` are inert storage: no spend enforcement, no execution.
- Stages/descriptions of the four businesses come from `docs/master/HANDOFF.md` evidence; Fashion's brand is unconfirmed
  (open founder decision). Seeded `updated_at` is a fixed date, not deploy time.
- Single owner, no per-business permissions. Booleans are 0/1 integers to match the existing schema.
- `MCP` read-only connector (`dashboard/mcp.py`) does not expose Founder OS data yet.
- Pre-existing, unchanged: Gmail token expires ~2 Nov; MOCK label in status; dead `dashboard/static/app.js`.

## Next phase requirements (Phase 2 suggestion)
1. Supply/confirm the build protocol and Phase 0 audit; reconcile.
2. Founder OS dashboard: business switcher + per-business overview (tasks, goals, KPIs, decisions) using these endpoints.
3. Seed real first records per business (BuildFlow blockers as `work_tasks`, KPIs such as paying customers) once the owner
   confirms them; decide Fashion brand.
4. Legacy retirement migration (leads/payments -> BuildFlow records), then drop in a separate reversible migration.
5. Only after that: AI layer (needs `ANTHROPIC_API_KEY`, writes `ai_usage`, budget enforcement) and automation execution
   behind the existing approval gates.

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
