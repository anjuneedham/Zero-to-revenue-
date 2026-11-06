# Current State Audit

Audit date: 6 Nov 2026. Method: read the code and docs, ran the existing test suite against a throwaway local
Postgres 16, read git history. Nothing was run against production. No credentials were read or are reproduced here.

## 0. Which software is "the software"?

Four repositories were attached to this session. Only one is the outreach/revenue system:

| Repo | What it is | Used for Episode 001? |
|---|---|---|
| `Zero-to-revenue-` | Python + Postgres (Neon) + vanilla-JS PWA, deployed on Vercel. Called "Zero to Hero OS" / "Zero-to-Revenue" in docs. Has owner auth, a `leads` table, outreach drafting/sending (approval-gated), Treasury (payment verification), a daily-cron scheduler. | **Yes. This is the platform being improved.** |
| `YardScale-Digital` | Static marketing site ("Automation & creative agency") with a booking-link placeholder. | Possibly the operating business's storefront. **Needs owner confirmation.** |
| `agriloopmain`, `agriloop` | Agriloop marketplace (Next.js 16, Supabase, Capacitor). | **No.** The brief says to keep Agriloop separate. (`agriloopmain/video-production` is an Agriloop-specific video pipeline; not reused, see EPISODE_001_EDITING_PLAN.md.) |

The "operating business" offer is not stated in the brief. The repo evidence points at **BuildFlow** (contractor SaaS, $50/month,
Jamaica, per `docs/strategy/OWNER_PROFILE.md` and `BUILDFLOW_LAUNCH_PLAN.md`) and service tiers (done-for-you setup, retainer).
This is recorded as an **assumption needing confirmation** and every script placeholder that depends on it is marked.

## 1. What exists (answers to the 17 audit questions)

1. **Software:** an owner-only agent dashboard. Three agents: Scout (finds paid opportunities), Operator (drafts work/outreach,
   never submits without approval), Treasury (read-only payment verification). 236 tests at baseline.
2. **Purpose / users:** single owner (founder). Single-tenant. Originally "find freelance/bounty work at $0 capital"; reoriented on
   26 Oct toward selling BuildFlow.
3. **Frontend:** vanilla JS, one file per page (`overview, scout, operator, treasury, plan`), no build step, strict CSP
   (`script-src 'self'`), all DOM via `createElement/textContent` (no `innerHTML`), PWA with service worker.
4. **Backend / DB:** stdlib `http.server` handler shared by local runner and Vercel (`api/index.py`); Postgres via `psycopg`,
   forward-only SQL migrations (`database/migrations/001-006`), advisory-locked migrate on cold start.
5. **Auth:** scrypt password + TOTP + recovery codes, hashed bearer sessions, lockout, no cookies (no CSRF surface). Owner is the only role.
6. **CRM capability:** `leads` table with `name, business, email, phone, source, status (NEW/DRAFTED/QUEUED/SENT/SKIPPED), notes`.
   That is the whole CRM. No stage, value, follow-up date, industry, website, outcome, or history.
7. **Outreach:** CSV import (dedupe by email), template draft (`agents/operator/outreach.py`, one generic template with `[OWNER TO FILL]`),
   approve -> edit -> send via Gmail (approval-gated by policy `Action.SEND_OUTREACH`), batch send.
8. **Playbooks:** none in code. There is a static "Game plan" page (`dashboard/static/data/plan.json`, ticks stored in `settings`)
   which is a BuildFlow launch checklist, not an executable playbook system.
9. **Workflow automation:** a daily Vercel cron (`/api/cron`) runs Scout/Operator/Treasury. No sales workflow automation.
10. **Reporting:** `core/reports.status_snapshot` (agent health, verified revenue). Nothing about outreach performance.
11. **Activity history:** append-only `audit_events` (trigger-enforced) for system actions and `task_events` for agent tasks.
    No per-prospect timeline.
12. **Integrations:** Gmail send (OAuth refresh token; per the 26 Oct audit it expires after ~7 days while the OAuth app is in Testing),
    PayPal (sandbox verified end-to-end; live credentials checked, no real-money order recorded), EVM read-only RPC, Twilio
    WhatsApp as record-only, a read-only MCP connector.
13. **Bugs / incomplete:** see section 3.
14. **Deployment:** live at `zero-to-revenue-neon.vercel.app` per prior session notes (not re-verified in this session: no network
    check was made). Deploys are manual API triggers per the 26 Oct audit.
15. **Outreach progress / records:** see `OUTREACH_STATUS.md`. **No prospect records are available to this session.**
16. **Branding:** the app uses a football "matchday" theme (navy `#034694`, gold, "Z2R" crest, "Walking out of the tunnel" splash).
    The **Andrew Builds** brand is separate and has no assets in any attached repo.
17. **Tooling available here:** FFmpeg 6.1.1 (libx264, aac, libass `subtitles`/`ass`, `drawtext`, `zoompan`, `loudnorm`), `ffprobe`,
    Python 3.13 + Pillow + NumPy, Node 22, Chromium + Playwright (pre-installed), Inter / DejaVu / JetBrains Mono fonts,
    Postgres 16 server binaries. **Not available:** a TTS engine, a speech-to-text/forced-alignment tool, a DAW/NLE GUI,
    any music library. Connectors exist for Descript (not used: it needs uploaded media and a project, and nothing to upload yet).

## 2. Baseline test result (executed 6 Nov 2026)

`python3 -m unittest discover -s tests -t .` against local Postgres 16: **236 run, 235 pass, 1 fail.**
Failing: `tests.unit.test_scout.SuperteamTest.test_verified_sponsor_with_ai_allowed_qualifies_but_token_promo_and_unverified_do_not`
(expected QUALIFIED, got REVIEW_REQUIRED). It is in Scout's marketplace scoring, which this work does not touch. Likely cause is a
fixture that has aged relative to today's date, but this was **not investigated**. It pre-dates all changes in this session.

## 3. Known gaps and risks (verified from code/docs)

- Data model is opportunity-centric; `leads` has no pipeline (carried over from the 26 Oct audit and re-confirmed in `006_leads.sql`).
- Request bodies are capped at 4,096 bytes (`MAX_BODY`), which blocks editing a playbook with a dozen steps.
- `status.mode` / `README` still describe the earlier crypto/zero-capital framing. `dashboard/static/app.js` is dead code.
- No AI model is configured (`ANTHROPIC_API_KEY` unset per the earlier audit). Everything "smart" is rules/templates. Any
  recommendation this work adds must therefore be a labelled rule, not an AI claim.
- Secrets were pasted into chat in earlier sessions (per `IMPLEMENTATION_AUDIT.md` section 9). Rotating them is still open. Not re-checked.
- Tablet: layout switches to a 5-tab bottom bar under a width breakpoint; with more pages the bar needs to scroll or reduce.
