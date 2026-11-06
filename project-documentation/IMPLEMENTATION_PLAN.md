# Implementation Plan

## Done in this session (verified, see PRODUCT_TEST_REPORT.md)
1. Audit and documentation (this folder).
2. Migration 007 (including honest carry-over of legacy lead statuses), `core/sales`, `/api/sales/*`, five new pages.
3. 24 unit/API tests, a browser journey (25 checks), migration test on a populated database.

## Next, in priority order (needs your input where noted)
1. **Back-fill real outreach** (needs your list: business, channel, date, outcome). Then re-check Insights for what the real data says.
2. **Deploy to Vercel/Neon** (needs your go-ahead). Steps: merge the branch, trigger deploy, open the app, check `/api/auth/state`, create one prospect, delete it.
3. **Set your timezone and daily targets** on the Today page.
4. Bulk CSV import into the pipeline (stage, channel, dates) so earlier work lands as backdated records.
5. Outreach drafting inside a prospect (reuse `agents/operator/outreach.py` templates, still approval-gated).
6. Calendar link for meetings (Calendly connector exists in the harness but is not wired to the app).
7. Add sales read-only tools to the MCP connector so any Claude chat can answer "what's due today".
8. Fix the aged Scout test fixture (listing deadline 2026-11-05 expired) so the suite is green.

## Not planned (deliberate)
Automated sending, scraping social platforms, AI scoring without a key and budget, percentages on tiny samples.
