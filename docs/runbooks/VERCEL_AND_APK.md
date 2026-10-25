# Vercel hosting + installable app / APK

## Target architecture
| Piece | Where | Cost |
|---|---|---|
| Dashboard + API | Vercel (Python functions, `api/index.py`) | Hobby free tier |
| Database | **Postgres** (Neon via Vercel Marketplace, or Supabase) | Free tier |
| Scheduler for agents | GitHub Actions cron calling a protected endpoint (Vercel Hobby cron is once/day only) | Free |
| Login | Firebase Auth, owner email only | Free |
| Phone app | PWA first, then APK wrapper | Free (sideload) |

## Database (done): Neon Postgres, one database
- Neon (Free) is connected to the Vercel project; `DATABASE_URL` is a hidden "sensitive" variable.
- Created **without** per-deployment database branches: there is exactly one database, so the
  kill switch, audit log and ledger never fork between deploys.
- `api/index.py` applies migrations once per cold start under a Postgres advisory lock, and
  answers 503 (never fake data) if the database is missing or unreachable.
- Preview deployments currently share the production `DATABASE_URL`. Acceptable while only the
  owner can sign in; remove the variable from **Preview** before inviting anyone else.

## Tests
`TEST_DATABASE_URL=postgresql://... python3 -m unittest discover -s tests -t .` against a
throwaway Postgres (each test gets its own schema). Without it Postgres tests are SKIPPED.

## Remaining before real use
1. Set `OWNER_EMAIL`, `FIREBASE_PROJECT_ID`, `FIREBASE_WEB_API_KEY`, `FIREBASE_AUTH_DOMAIN` in Vercel
   (Settings -> Environment Variables); add the Vercel domain to Firebase "Authorized domains".
2. Turn off Vercel Deployment Protection for production so the PWA/APK can load the manifest
   (our own owner-only login protects the data).
3. Move to Vercel Pro (or other hosting) before earning real revenue: Hobby is non-commercial.

## Phone app
- **PWA (works now once deployed):** open the Vercel URL in Chrome -> menu -> Install app.
  Manifest, icons and a service worker (shell only, never `/api`) are in `dashboard/`.
- **APK:** wrap the deployed URL as a Trusted Web Activity with PWABuilder or Bubblewrap.
  Needs: HTTPS URL, `/.well-known/assetlinks.json` (public SHA-256 fingerprint only).
  Sideloading an APK is free; Play Store needs a one-time $25 developer fee.
- The Android **signing keystore is a secret**: keep it out of git (`*.jks`, `*.keystore`
  are ignored) and back it up yourself; losing it means you can't update the app.
- Google sign-in popups can misbehave inside a TWA; if so switch to redirect sign-in.
