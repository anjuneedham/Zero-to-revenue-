# Vercel hosting + installable app / APK

## Target architecture
| Piece | Where | Cost |
|---|---|---|
| Dashboard + API | Vercel (Python functions, `api/index.py`) | Hobby free tier |
| Database | **Postgres** (Neon via Vercel Marketplace, or Supabase) | Free tier |
| Scheduler for agents | GitHub Actions cron calling a protected endpoint (Vercel Hobby cron is once/day only) | Free |
| Login | Firebase Auth, owner email only | Free |
| Phone app | PWA first, then APK wrapper | Free (sideload) |

## Why not SQLite on Vercel
Vercel's filesystem is ephemeral. SQLite there would lose the kill-switch state, queue
and audit log on any cold start. `api/index.py` therefore refuses every `/api` route
(HTTP 503) until a Postgres backend exists. **Do not point production at it before then.**

## Remaining work before a real deploy (next steps)
1. Port `core/db.py`, queue and reports to Postgres (replace `BEGIN IMMEDIATE` with
   `SELECT ... FOR UPDATE SKIP LOCKED`; keep the same tests running against both).
2. Create the Postgres database; set `DATABASE_URL` as a Vercel env var (never in git).
3. Set `OWNER_EMAIL`, `FIREBASE_PROJECT_ID`, `FIREBASE_WEB_API_KEY`, `FIREBASE_AUTH_DOMAIN`
   in Vercel project settings. Add the Vercel domain to Firebase "Authorized domains".
4. Connect this repo to a Vercel project (owner action) and deploy a preview first.

## Phone app
- **PWA (works now once deployed):** open the Vercel URL in Chrome -> menu -> Install app.
  Manifest, icons and a service worker (shell only, never `/api`) are in `dashboard/`.
- **APK:** wrap the deployed URL as a Trusted Web Activity with PWABuilder or Bubblewrap.
  Needs: HTTPS URL, `/.well-known/assetlinks.json` (public SHA-256 fingerprint only).
  Sideloading an APK is free; Play Store needs a one-time $25 developer fee.
- The Android **signing keystore is a secret**: keep it out of git (`*.jks`, `*.keystore`
  are ignored) and back it up yourself; losing it means you can't update the app.
- Google sign-in popups can misbehave inside a TWA; if so switch to redirect sign-in.
