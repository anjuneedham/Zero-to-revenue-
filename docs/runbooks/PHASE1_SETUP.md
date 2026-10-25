# Phase 1 setup (owner actions)

## Owner-only login (Postgres, password + authenticator app)
1. In Vercel -> Settings -> Environment Variables add `OWNER_SETUP_TOKEN` = a random string of 20+
   characters (make one up; do not paste it in chat or commit it). Redeploy.
2. Open the app. It shows **First-time setup**: enter the setup token and choose a password (12+ chars).
3. In Google Authenticator (or similar) add an account by **entering a setup key manually** and type the
   key shown. Enter the 6-digit code to finish.
4. Save the 8 one-time **recovery codes** offline. They are shown once.
5. **Delete `OWNER_SETUP_TOKEN` from Vercel and redeploy.** Setup is also permanently closed in the
   database once finished, so the token can no longer be used.
Protections: scrypt-hashed password; each TOTP code works once; sessions are random tokens stored hashed,
expire after 24h and can be revoked ("Sign out everywhere"); 8 failed attempts per 15 min lock the login
(this also means someone could lock you out for 15 minutes, but never in); every failure is audited.
Lost phone: sign in with a recovery code. Lost both: reset by deleting the `owner_credentials` row in
the Neon console, which re-opens setup (requires `OWNER_SETUP_TOKEN` again).

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
- Recommended: dashboard on Vercel (decided) + a small always-on worker or scheduled jobs with
  Postgres. Decide before Phase 2/6.

## Claude connector (read-only MCP)
1. Vercel -> Environment Variables: add `MCP_CONNECTOR_TOKEN` (Secret, 32+ random characters). Redeploy.
2. claude.ai -> Settings -> Connectors -> Add custom connector. URL:
   `https://zero-to-revenue-neon.vercel.app/mcp/<your token>`
3. Ask any chat: "what needs my attention?" Tools: what_needs_my_attention, get_status, daily_report,
   list_opportunities, list_open_actions, list_payments. None can change anything; each call is audited.
4. If the URL ever leaks, change the token in Vercel and redeploy; the old URL stops working.
