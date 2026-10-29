# Prompt for the Agriloop launch-fix session (paste as the first message of a NEW session)

```
Goal: make Agriloop work live and durably before a creator starts Tue 3 Nov 2026. Read
docs/strategy/AGRILOOP_LAUNCH_PLAN.md and docs/master/HANDOFF.md in anjuneedham/Zero-to-revenue-
first (do not re-research what they state), then work in anjuneedham/agriloopmain (add_repo with push access).

Facts already verified (29 Oct): no Firebase in Agriloop; auth is Supabase. Production uses MemoryDataSource
(listings/posts lost on cold start). Live Vercel project `agriloopmain` (team Yardscale Digital) has only
NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY, ALLOW_SEED_IN_PRODUCTION=true. The only
Supabase project (YardScale-Digital, ref rocawrsurnfikzreajwo, free plan) showed status INACTIVE = PAUSED.

Do in this order, stopping to report after each step:
1. DIAGNOSE. Supabase MCP list_projects. If paused, tell me and ask before restore_project. Confirm the project
   is the one agriloopmain points at (compare ref to the URL host from `vercel env pull`-free means: ask me if
   it cannot be confirmed without decrypting secrets). Then list_migrations, list_tables, get_advisors
   (security + performance). Report what exists vs prisma/schema.prisma. Test live: /, /market, /signin,
   sign up with a throwaway address, post a listing, reload. Say what actually fails and why.
2. PRISMA DATA SOURCE. Implement PrismaDataSource behind the existing repository interfaces in
   src/lib/db. Reconcile prisma/schema.prisma with the Supabase tables already created by supabase/migrations
   (do not duplicate auth/profile tables). Use the pooled connection string (DATABASE_URL, pgbouncer) for the
   app and DIRECT_URL for migrations. Note Prisma connects as a role that bypasses RLS, so enforce
   ownership/authorization in the repository layer and add tests for it. Schema changes go through reversible
   SQL migrations applied with Supabase apply_migration on a Supabase branch or after showing me the SQL; run
   get_advisors after every DDL change.
3. STORAGE + EMAIL. Supabase Storage bucket for listing photos (public read, owner-only write policies,
   size/type limits), replace LocalStorageService. Custom SMTP (Resend) for auth emails; document the dashboard
   steps I must do myself.
4. GO LIVE SAFELY. I add DATABASE_URL/DIRECT_URL as Vercel secrets myself (never ask me to paste secrets
   into chat; never print or decrypt env values). You may set non-secret vars via Vercel MCP
   (AGRILOOP_DATA_SOURCE=prisma, STORAGE_PROVIDER, EMAIL_PROVIDER) after I confirm. Deploy a preview first,
   run the live checks from step 1 on the preview, then ask before promoting to production.
   Then set ALLOW_SEED_IN_PRODUCTION=false only after real listings exist.
5. KEEP IT ALIVE. Free Supabase projects pause after 7 days of inactivity. Propose a keep-alive (scheduled ping
   hitting the database) or recommend Pro (about $25/month) and let me decide.

Rules: one task per step; no sub-agents; run lint/typecheck/tests once at the end of each step; never skip or
disable a test; commit to a feature branch, no PR unless I ask; report honestly (what is verified live vs only
in code). Update docs/strategy/AGRILOOP_LAUNCH_PLAN.md and the Founders Log in Zero-to-revenue- at the end.
```
