# Scout (Phase 2) — mode: READ_ONLY (reads public sources, writes only to the database)

## Flow
`run_scout` -> authorize (kill switch, least privilege) -> sources -> sanitize -> scam checks ->
deterministic score -> optional bounded Claude help -> store (idempotent) -> event -> Operator task.

## Safety properties (each has tests)
- **Untrusted data:** all fetched text is stripped of hidden/bidi characters, length-capped, scanned
  for prompt-injection phrases. Injection raises risk by 40 and can never reach QUALIFIED.
- **Fetching:** https only, host allowlist, no redirects, 1 MB cap, 10 s timeout.
- **Unknown is not zero:** unknown required capital is stored as NULL and earns only partial credit.
  Capital > 0 earns no zero-capital credit and adds risk.
- **Claimed payment is not revenue:** stored as a claim, labelled "(unverified)".
- **Claude is optional and boxed in:** disabled unless budget, prices and key are set. Reserved
  worst-case cost under a lock, so concurrent calls cannot overshoot `LLM_MONTHLY_BUDGET_USD`.
  The model sees text only inside `<untrusted>` tags and may return three 0-1 ratings, <=3 risk
  flags and a short note. Anything else is discarded. It can add caution, never remove it.
- **Idempotent:** opportunity id = hash of source URL; reruns create no duplicates, events or tasks.
- **Failures are recorded:** per-source errors land in `agent_runs.error`; the agent shows `error`.

## Known limits
- Only one source so far (public GitHub issues labelled `bounty`); `GITHUB_TOKEN` is optional.
- Skill fit is neutral until `OWNER_SKILLS` (comma-separated) is set.
- The live GitHub call and the live Claude call were NOT exercised in the build sandbox
  (sandbox blocks GitHub search; no API key). Use "Run Scout now" on the deployed site to verify.
- Scoring weights are the spec's; the heuristics are first-pass and will need tuning on real data.
