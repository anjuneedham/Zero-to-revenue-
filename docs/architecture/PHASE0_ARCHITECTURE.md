# Phase 0 — Architecture Inspection

Status: **ARCHITECTURE ONLY.** No agent performs any external action yet.

## 1. Repository inspection (2026-10-25)
- Repository was empty (no commits, no code, no specs besides the master prompt).
- No existing code to conflict with. `MASTER_SYSTEM.md` now records the spec.

## 2. Stack decision
| Concern | Choice | Why |
|---|---|---|
| Language | Python 3.12+ | Stdlib covers SQLite, HTTP, scheduling; good for agents |
| Database | SQLite (Phase 1), Postgres-ready schema | $0 cost, single file, backup = file copy |
| Queue | DB-backed table with leases + idempotency keys | Durable, no extra service |
| Events | `task_events`/`audit_events` tables, append-only | DB is source of truth |
| Dashboard | Server-rendered HTML (stdlib/FastAPI TBD) | Minimal deps |
| Tests | stdlib `unittest` | No dependency needed for Phase 0 |
| LLM calls | Behind an adapter in `integrations/` | Paid service → needs owner approval (spec §39) |

## 3. Implemented in Phase 0
- `core/policy/policy.py`: state enums, per-agent least-privilege permissions,
  permanently forbidden financial actions, approval-gated external writes,
  kill-switch check, Scout scoring (§6–7), verified-revenue rule (§16, §18).
  Financial flags are hard-coded constants, not configuration.
- `tests/unit/test_policy.py`, `tests/security/test_no_secrets.py`.
- Directory scaffold from spec §20, `.env.example`, `.gitignore`.

## 4. Conflicts / ambiguities found in the spec
1. **Repo name**: spec says `zero-to-revenue-agent-system`; actual repo is
   `zero-to-revenue-`. Kept the actual repo; layout follows spec §20.
2. **REVIEW_REQUIRED** (§7) is not in the opportunity state list (§3).
   Added it as an explicit state.
3. **Wallet chain is not configured** (§2 forbids assuming Ethereum).
   Treasury must refuse to run until `OWNER_WALLET_CHAIN_ID` is set → USER_ACTION.
4. **"Autonomous discovery" vs. cost control**: real web research and LLM
   reasoning need paid APIs. Per §39 these require owner approval first.
5. **Authentication** (§30 resume requires authenticated owner): the method
   (local password+TOTP, OAuth, etc.) is an owner decision.

## 5. Missing dependencies (all need owner decision)
- Chain for the receiving address + a read-only RPC/indexer endpoint.
- LLM provider/API key and monthly budget cap.
- Notification channel (email, Telegram, ntfy, …).
- Hosting target for the scheduler/dashboard.
- Opportunity sources the owner is allowed to use (account ToS).

## 6. Implementation order
| Phase | Scope | Mode label |
|---|---|---|
| 1 | Schema + migrations (all §21 tables), owner auth, task queue w/ leases & idempotency, kill switch, audit log, minimal dashboard | MOCK |
| 2 | Scout: source adapters (read-only), scoring, scam heuristics, prompt-injection quarantine | READ_ONLY |
| 3 | Operator: plan/execute/test loop in sandbox, USER_ACTION blocker system, approval gate | HUMAN_APPROVED |
| 4 | Treasury: chain-verified read-only monitor, ledger, reconciliation | READ_ONLY |
| 5 | Notifications with priority + dedupe | — |
| 6 | Scheduler respecting kill switch | — |
| 7–9 | Real opportunities, revenue verification, optimization | HUMAN_APPROVED |
