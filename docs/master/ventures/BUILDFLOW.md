# BuildFlow (repo: `buildflow`)

Evidence source: docs/master/HANDOFF.md (verified 28 Oct 2026). Claims not re-verified this chat are marked UNVERIFIED.

## Report
- Next.js 16, Firebase project `build-6fa95`, live 200 at buildflow-app-beta.vercel.app, Capacitor Android shell.
- Its own report (25 Oct): verdict **NOT READY**.
- Suites exist: 32 unit, Firestore rules, e2e, QA. UNVERIFIED: not re-run by the OS chat.

## Audit (launch blockers, from the 25 Oct report)
1. Firebase Storage not provisioned: uploads fail.
2. Legal pages are placeholders.
3. Never run against the real Firebase prod project.
4. No billing: Stripe-ready seam only; manual mode.
5. No push or email notifications.

## Risks
- Shipping to users with failing uploads (core feature) destroys trust at first use.
- Placeholder legal pages block taking payment or collecting user data lawfully.
- Test suites passing on emulators may not reflect prod (blocker 3).
- Billing absent: no revenue path until Stripe is wired.
- Solo-founder bandwidth shared with three other ventures.

## MVP scope
In: working uploads on prod Firebase, real Terms/Privacy pages, e2e green on prod project, manual billing (invoice/payment outside the app) for first customers, transactional email for key events.
Out (post-MVP): Stripe self-serve billing, push notifications, sidekick/AI features (Phase 4, needs ANTHROPIC_API_KEY), Android store release.

## Roadmap
| Step | Work | Day |
|---|---|---|
| 1 | Provision Firebase Storage on prod, verify upload end to end | Mon |
| 2 | Real legal pages (founder/legal sign-off on text) | Mon |
| 3 | Run unit + rules + e2e against prod project; fix failures | Mon |
| 4 | Email notifications (minimum: signup, key workflow events) | Mon |
| 5 | Stripe billing on the existing seam | after first paying users |
| 6 | Push notifications, Android release | later |

## Growth plan (Fri)
Onboard first users by hand, from founder's own network; collect feedback per user; manual billing until 5 paying users justify Stripe. Add simple funnel tracking (visit, signup, first upload, return in 7 days) before any paid acquisition.

## Metrics
Signups/week, activation (first successful upload within 24h), 7-day retention, paying accounts, MRR, upload failure rate, support requests/week. Log in the OS `metrics` table once Phase 1 lands.

## Acceptance criteria (gate "ready", from MASTER_PLAN)
- [ ] Storage works on prod Firebase (upload + download verified)
- [ ] Legal pages real, linked from signup and footer
- [ ] e2e green against the prod Firebase project
- [ ] At least one notification channel (email) working
- [ ] Manual billing process documented
