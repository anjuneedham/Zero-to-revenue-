> **Done 29 Oct 2026** (steps 1, 2, 4, 5, 6, 7; step 3 skipped by the owner). Outcome and what is unverified: HANDOFF.md, section "FINISH_PROMPT outcome".

# Prompt: finish the Zero to Hero OS (paste into a NEW chat)

Read docs/master/HANDOFF.md, docs/runbooks/CHALLENGE.md and IMPLEMENTATION_AUDIT.md in anjuneedham/Zero-to-revenue- (branch claude/founder-os-phase-10-qetxx8), then continue. Follow the token rules in HANDOFF.md: one phase per chat, read with offsets/greps, no sub-agents, run the test suite once at the end.

**Context.** The OS is a Python/Neon/Vercel app (3 agents + owner auth + approval gates). Phase 10 added the 60-day challenge (1 Nov - 31 Dec 2026, $10k verified cash): migration 007, core/challenge.py, agents/operator/pitches.py, /api/challenge/*, Challenge page. Pricing is fixed: annual = 12 months for the price of 10 (2 free). BuildFlow $50/mo -> $500/yr. AgriLoop Buyer Basic $10/mo -> $100/yr, Farmer Premium $20/mo -> $200/yr. Only Treasury-verified payments count as cash. Nothing is sent without owner approval. AgriLoop's database is being finished the weekend of 31 Oct; take no AgriLoop payment until it is confirmed live.

**Do, in this order (stop and report after each):**
1. Deploy the branch to Vercel production, confirm migration 007 applied (GET /api/challenge returns config), and smoke-test the Challenge page with the owner login. Report what is live.
2. Make PayPal collection one tap: from a deal card, request the PayPal link and copy a ready-to-send message containing it; verify the live (not sandbox) flow with a real $1 order the owner approves.
3. Gmail: the OAuth refresh token expires ~2 Nov. Publish the OAuth app or document the exact re-issue steps; confirm email send still works.
4. Add owner-supplied screenshot/paste ingestion for leads (needs ANTHROPIC_API_KEY and the existing $80/month cap in core/budget.py; extracted text is untrusted data, fixed JSON schema, never triggers a send). If the key is not set, build the review UI and say extraction cannot run.
5. Weekly report: replies -> onboarding booked -> paid by channel and by plan, plus what to do next week. Add it to the Sunday scheduler tick.
6. Ventures/tasks/decisions/experiments tables from HANDOFF step 3 (reversible migration 008), keeping the Python/Neon/Vercel stack.
7. Update HANDOFF.md and CHALLENGE.md with exactly what changed. Commit and push to the branch above; do not open a PR unless asked.

**Rules.** Never invent claims, testimonials, user counts or prices. Never remove an approval gate. Keep each step's tests passing (python3 -m unittest discover -s tests -t . with TEST_DATABASE_URL set to a throwaway Postgres). Say plainly what is verified and what is not.
