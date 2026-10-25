# Phase 1 setup (owner actions)

## Owner-only Firebase login
1. Firebase console -> Authentication -> enable the **Google** provider.
2. Authentication -> Settings -> User actions: **disable "Enable create (sign-up)"** after
   your own account exists, so nobody else can register.
3. Enable multi-factor auth on your Google account.
4. Set `OWNER_EMAIL` and `FIREBASE_PROJECT_ID` in `.env` (or the host's secret store).
The server verifies the Firebase ID token's signature, issuer, audience, expiry and
`email_verified`, then requires the email to equal `OWNER_EMAIL`. Unconfigured = nobody gets in.

## Claude as the AI (spec section 39 disclosure)
- Service: Anthropic API (Claude). Purpose: Scout research/scoring, Operator drafting.
- Cost: pay-per-token; no unlimited free tier. **Set `LLM_MONTHLY_BUDGET_USD`** - the system
  must refuse calls past it. Alternative: no-LLM mode (rules/scoring only).
- Key lives only in `.env` / host secrets. Never in the repo.

## WhatsApp
- Option A: Meta WhatsApp Business Cloud API (needs a business account + approved template;
  owner-initiated messages must use a template). Option B: Twilio WhatsApp.
- Costs: Meta charges per conversation/template category; Twilio adds a per-message fee.
  Needs your approval before enabling. Until then the backend is MOCK.

## Hosting (Vercel?)
- Vercel is fine for the **dashboard** (serverless, free tier).
- It is a poor fit for the **agents/scheduler/DB**: functions are short-lived and the
  filesystem is ephemeral, so SQLite will not persist. Cron on the free tier is limited.
- Recommended: dashboard on Vercel (or Firebase Hosting) + a small always-on worker with
  Postgres. Decide before Phase 2/6.
