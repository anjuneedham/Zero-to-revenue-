# Implementation Audit - BuildFlow AI Revenue OS

Written 26 Oct 2026 against commit `b5aeffe`, before any code for the reconfiguration. Based on reading
the repo and on what we actually observed running it live over the last two days, not on the docs.

## 1. Current architecture

- Python 3.13, stdlib HTTP handler (`dashboard/app.py`), one `handle()` shared by the local runner and
  Vercel (`api/index.py`, every path rewritten through `/api/index?p=`). ~3.7k lines of app code, 236 tests.
- Postgres (Neon) via a thin wrapper (`core/db.py`, `?` -> `%s`). Migrations 001-006 in `database/migrations`.
- Frontend: vanilla JS, one file per page (`overview, scout, operator, treasury, plan`), strict CSP
  (`script-src 'self'`), PWA with service worker. No build step.
- Three agents sharing one task queue (`core/queue`), one policy gate (`core/policy/policy.py`), one
  audit log (append-only, trigger-enforced), one kill switch, one notification service.
- Scheduling: Vercel Cron hits `/api/cron` once a day (07:00 UTC). `scheduler.tick` runs Scout (gated to every
  6h), Operator, Treasury. The extra 6-hourly loop I created from chat was deleted; it cannot run unattended
  (credential decryption is blocked in background sessions).

## 2. What exists and works (production-connected)

| Area | State |
|---|---|
| Owner auth | scrypt + TOTP + recovery codes, hashed sessions, lockout. Solid. |
| Database / hosting | Neon + Vercel, live at zero-to-revenue-neon.vercel.app. Deploys are manual API triggers; push alone did not auto-deploy. |
| Scout sources | Superteam, GitHub bounties, Freelancer.com, Remotive, Himalayas. Public APIs, no login. |
| Scoring / filtering | Deterministic. `off_skill` (title-only), `commission_only_role`, scam flags, rescore-by-version, auto-cleanup. |
| Operator | Template drafts, approval-gated. Gmail send for outreach and for email job submissions (verified with a real send). |
| Treasury | Read-only EVM verification on 7 chains. PayPal order create / link / verify (sandbox verified end to end; **live credentials verified against PayPal's token endpoint but no real-money order has been run**). |
| Leads | Owner-supplied CSV import, dedupe by email, draft -> approve -> edit -> send, batch send. |
| Dashboard | Overview as one-stop page (run agents, decisions, payments), Scout list with select/remove/send-to-Operator, sort, Treasury PayPal controls, Game plan with persisted checklists. |
| MCP connector | Read-only status/opportunities/payments for Claude chats. |

## 3. What is mocked or not actually connected

- **No AI is running.** `SCOUT_CLIENT = None` in `dashboard/app.py`; `ClaudeClient` exists but `ANTHROPIC_API_KEY`
  has never been set (only `LLM_MONTHLY_BUDGET_USD=80` is). Everything "intelligent" today is regex and templates.
  This is the single biggest gap versus the new brief: screenshot reading, research, fit scoring with reasons, and
  personalization all need a model.
- Twilio WhatsApp is `RecordOnly` (messages are stored, never delivered).
- `status.mode` is a hardcoded `"MOCK"` label. Misleading: PayPal and Gmail are live.
- Clay and Supermetrics are connected to *my chat*, not to the deployed app, and neither fits the target market
  (Clay does not index small Jamaican trades businesses; Supermetrics has no license on the team).

## 4. Broken, fragile, or misaligned

1. **Data model is job-centric, not prospect-centric.** `opportunities` carries bounty fields (payment_asset,
   deadline, required_capital). A BuildFlow prospect has none of those. `leads` is the closest thing and has only
   name/business/email/phone/notes and a 5-value status CHECK. No stage pipeline, no fit score, no channel, no
   touch history, so nothing can be learned about what acquisition method works (objective 6).
2. **Revenue verification assumes an opportunity.** `counts_as_verified_revenue` needs `source_associated`. Today a
   BuildFlow subscriber has to be anchored by a synthetic `opp_manual_*` row (`create_manual_payment`). Works, but
   it is a workaround; a customer record should be the anchor.
3. **Scout's default sources are crypto/gig-era** (Superteam, GitHub bounties, Freelancer.com). Useful as a side feed,
   wrong as the primary engine for this brief. The $500 floor / easy-words / human-only logic is job-specific.
4. **Operator drafts are job-proposal templates.** Only `draft_outreach` is prospect-oriented, and it is a single
   generic template with `[OWNER TO FILL]` holes.
5. **Gmail refresh token expires in 7 days** (OAuth app is in Testing). Sending silently stops around 2 Nov unless
   the app is published or the token is reissued.
6. **MAX_BODY = 4096 bytes** on every JSON route (CSV import is the one 200 KB exception). Screenshot upload needs
   its own route and limit; Vercel's request cap is ~4.5 MB, so images must be downscaled client-side.
7. **Stale docs.** `MASTER_SYSTEM.md`, `docs/architecture/*` and `README` describe the crypto/zero-capital product.
   `dashboard/static/app.js` (212 lines, last touched in the Phases 3-6 commit) is dead code: not referenced by `index.html`, `app.py` or `sw.js`, and not in the served static paths. Safe to delete.
8. **Auto-send escalation list is job-flavoured** (`autodraft.py` benign flags). Needs its own rules for prospects.
9. **Automation limits:** no unattended 6-hour loop is possible from chat; only Vercel Cron (daily) runs by itself.

## 5. Reusable components (do not rebuild)

`core/policy` (extend `Action` set rather than bypass), `core/actions` (approve/reject/mark_*), `core/queue`,
`core/audit`, `core/notifications`, `agents/operator/outreach.py` + `integrations/gmail.py` (send path),
`integrations/paypal.py` + Treasury verify (revenue), `agents/scout/sanitize.py` (untrusted-text handling),
`agents/scout/enrich.py` + `core/budget.py` (capped, output-validated Claude calls: the right pattern to reuse for
vision and research), the leads import/draft/approve/send flow, `Z.decisionCard`, Overview quick actions.

## 6. Recommended modifications

**Principle: extend `leads` into the prospect pipeline instead of adding a competing table; keep Scout's marketplace
sources as a secondary feed behind a setting; keep the three-agent shape, change what each one is for.**

- **Scout -> sales sidekick:** inputs are screenshots, pasted text, CSV. Outputs are structured prospect records,
  BuildFlow fit score with stated reasons, likely decision-maker, pain points, recommended angle, "who to contact next".
- **Operator -> outreach + follow-up executor:** drafts per prospect and per channel; email send stays
  approval-gated; non-email channels (Instagram, WhatsApp, LinkedIn) produce copy-ready drafts the owner sends.
- **Treasury -> unchanged**, plus customer/subscription anchoring.
- **New learning loop:** every touch and outcome is logged; a weekly report ranks channels and angles by reply -> demo
  -> paid conversion.

## 7. Database changes (migration 007, additive only)

- `leads`: add `trade`, `location`, `website`, `instagram`, `facebook`, `linkedin`, `decision_maker`, `fit_score`,
  `fit_reasons`, `pain_points`, `outreach_angle`, `stage` (new / researched / contacted / replied / demo / trial /
  paying / lost), `source_channel`, `last_contacted_at`, `next_action_at`; relax the status CHECK or map it to `stage`.
- `lead_screenshots`: id, lead_id, sha256, mime, size, extracted_json, extraction_model, created_at. **Store the
  extraction, not necessarily the image** (decision needed, see section 10).
- `lead_touches`: id, lead_id, channel, direction, draft/final text, sent_at, outcome (no_reply / replied / demo /
  declined / paid), notes. This is the learning loop's raw data.
- `customers`: id, lead_id, plan, price, started_at, status; payments anchor to a customer, not a synthetic opportunity.

## 8. Integration changes

- **Anthropic API (required for screenshots/research/personalization):** reuse `ClaudeClient` + `core/budget`
  (monthly hard cap already enforced). New prompt versions under `prompts/`. Vision input for screenshots.
- Gmail: publish the OAuth app or document the 7-day reissue; add unsubscribe/opt-out handling and a daily send cap.
- Twilio: optional, later; the owner-facing notifications can stay RecordOnly.
- Enrichment: only sources that are licensed or the owner's own data. No scraping of social platforms (their terms
  and our policy both forbid it); screenshots the owner supplies are the compliant substitute.

## 9. Security and compliance concerns

1. **Secrets were pasted into chat** (PayPal live secret, Gmail client secret and refresh token, PayPal sandbox keys).
   They work and are stored encrypted in Vercel, but should be rotated once setup is stable.
2. **Prompt injection via images/text.** Text extracted from a screenshot is untrusted data. Reuse the `enrich.py`
   discipline: delimited as data, fixed JSON schema, anything else discarded, model output can never trigger an action
   or change status. Never let extracted text reach a send path unreviewed.
3. **PII.** Prospects' names, handles and emails are personal data. Minimize retention, no logging of raw extractions
   in audit detail, owner-only access (already enforced), deletion path per lead.
4. **Outbound email.** CAN-SPAM-style requirements: honest sender, a working opt-out, honor it (suppression list),
   volume cap, warm-up from a Gmail account. Cold email at scale from a personal Gmail also risks the account.
5. **Upload surface.** New large-body route needs its own size cap, MIME allow-list, auth, rate limit, and no
   server-side image execution/parsing beyond passing bytes to the model.
6. **Approval gates stay.** `SEND_OUTREACH` / `SUBMIT_APPLICATION` remain in `APPROVAL_REQUIRED_ACTIONS`. The new
   brief's "reduce manual work" is met by better drafting and batching, not by removing the gate.

## 10. Decisions and information I need before coding sections 4+

- **The brief was cut off at section 4** (ends at "email"). Sections 4-end (screenshot flow details, Operator,
  Treasury, dashboard, learning loop, success metrics) are missing. Please resend from "# 4. SCREENSHOT LEAD INGESTION".
- **`ANTHROPIC_API_KEY`:** needed for any screenshot reading. Without it I can build the pipeline and the review UI
  but extraction cannot run. The existing $80/month cap applies.
- **Screenshot storage:** keep images (Vercel Blob or Postgres bytea; more risk, easier re-review) or keep only the
  extracted data and discard the image (less PII, recommended default).

## 11. Testing requirements

Unit tests for every new module (same style as the 236 existing). Specifically: vision extraction against fixture
responses (valid JSON, malformed JSON, injected instructions inside extracted text, oversized/low-confidence output);
upload route (auth, size cap, MIME, rate limit); migration 007 applies cleanly on a populated DB and is idempotent;
stage transitions and touch logging; fit scoring is deterministic given a fixed model response; suppression list blocks
sends; learning-loop report math; plus a live smoke of each new endpoint before reporting done.

## 12. Proposed order of work (after sections 4+ are confirmed)

1. Migration 007 + prospect model on top of `leads`, with tests.
2. Screenshot upload route + Claude vision extraction behind the budget cap + review/confirm UI.
3. Scout sidekick: fit score with reasons, angle, next-best-lead ranking (model-assisted, rules as the floor).
4. Operator: per-channel drafts, follow-up cadence, send-cap and suppression.
5. Touch logging + weekly channel/angle report (the learning loop).
6. Dashboard reshaped around the pipeline (Overview = "who to contact today"); marketplace Scout demoted to a side feed.
7. Customers table + PayPal anchoring.
