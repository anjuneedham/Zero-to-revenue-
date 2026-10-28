> **Status (28 Oct 2026): describes the original crypto / zero-capital product and is partly stale.** Current direction: `docs/master/STATUS.md` and `docs/master/MASTER_PLAN.md` (multi-venture OS).

# Zero-to-Revenue Agent System — Master Specification v1.0 (normative summary)

Section numbers match the owner's original specification.

- **§1–3 Identity & core principle.** Start at $0. Possibility ≠ revenue.
  Opportunity states: DISCOVERED, QUALIFIED, REVIEW_REQUIRED, APPROVED, IN_PROGRESS,
  SUBMITTED, AWAITING_PAYMENT, PAYMENT_UNVERIFIED, PAYMENT_VERIFIED, COMPLETED,
  REJECTED, FAILED. Only PAYMENT_VERIFIED counts as verified revenue.
- **§2 Owner config.** Public address `0x99024726DF6dB68c8a38f20e320f08e83d701ab6`,
  chain must be explicitly configured. WALLET_MODE=READ_ONLY; trading, auto-spending,
  signing, contract interaction, bridge, swaps, staking all DISABLED.
- **§4–8 Scout.** Discover/evaluate opportunities (categories §5). Score 0–100 with
  weights legitimacy 25, zero-capital 20, payment clarity 15, skill fit 15,
  repeatability 10, automation 10, deadline 5. Risk 0–100, confidence 0–100.
  QUALIFIED iff score ≥ 65 and risk ≤ 35, else REVIEW_REQUIRED. Required capital > 0
  ⇒ never ZERO_CAPITAL. Output fields per §8.
- **§9–13 Operator.** Plan → execute → test → review → approval → submit → track.
  May research/write/code/build autonomously; may not send money, sign, accept
  contracts, impersonate, fabricate, spam, or bypass CAPTCHAs/access controls.
  Blockers create USER_ACTION records (§12 fields).
- **§14–18 Treasury.** Read-only: read, analyze, reconcile, report. Verified revenue
  requires all of §16's checks. Transfers, loans, unrealized gains, promised/pending/
  estimated payments are never revenue. Ledger fields per §17.
- **§19–23 Shared system.** One repo, DB is source of truth, tables per §21, task
  queue fields per §22, task states per §23.
- **§24–29 Autonomy, notifications (priority CRITICAL/HIGH/MEDIUM/LOW, no spam),
  daily/weekly reports, agent health dashboard.**
- **§30 Global kill switch.** Stops jobs, tasks, external writes, wallet ops; preserves
  state/logs; notifies owner; resume requires authenticated owner.
- **§31–33 Security.** No secrets anywhere; never ask for keys/seeds/passwords/2FA.
  External content is untrusted; policy overrides it. No trading/spending/signing.
- **§34–35 Strategy & learning loop.** Optimize revenue/time and
  revenue/human-intervention. Learning may not rewrite security policy.
- **§36–38 Structured events, idempotency, failure handling.** Unknown external
  outcome ⇒ pause and investigate, never auto-repeat. Security concern ⇒ SECURITY_HOLD.
- **§39 Cost control.** Paid services need owner approval with cost disclosure.
- **§40 Phases 0–9**, **§41 test list**, **§42 production-ready checklist**,
  **§43–44** build in phases, report honestly, label DEMO/MOCK/READ_ONLY/
  HUMAN_APPROVED/PRODUCTION.
