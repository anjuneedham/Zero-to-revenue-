# EPISODE 002 PLAN: next story (framework only; status PLANNING)

The next story must come from what **actually** happens after Episode 001. As of 6 Nov 2026 the repositories show: the sales system is built and tested on made-up data; no real outreach is recorded in it; verified revenue was $0 at the last record (26 Oct); the real experiment (warm outreach to 10-15 real contacts) is described but its results are not available to me.

## Decision rule (pick the first that is true when you are ready to film)
| If this is true | Episode 002 story | Evidence to show |
|---|---|---|
| You have logged **10 or more real first messages** in the app | **"I contacted N real people. Here's what the pipeline says."** | Insights counts (responses, approach table), the activity timeline of one anonymised prospect, your honest read of what to change |
| You have logged real messages but **fewer than 10** | **"My first week of real outreach"**: the habit, the discomfort, what the follow-ups showed | Today screen across days, follow-ups cleared, the first replies (or silence) |
| You have **not yet sent real messages** | **"Why I haven't sent the first message yet"**: an honest blocker episode, then send one on camera (B02) | The real reason, the playbook you used, the send |
| Someone **replied or agreed to talk** | Lead with it: **"My first reply"** / **"My first call"** (C01/C02, with consent) | The log-response screen, what you learned |

Not a story yet: a payment. Only when Treasury verifies one (C03).

## Software story that can sit inside it
Pick one that is true by then: back-filling earlier outreach (supported by `occurred_at`), the sales tools in the connector, bulk CSV import, outreach drafting inside a prospect (see `project-documentation/IMPLEMENTATION_PLAN.md`).

## Open facts to collect (so the script has no invented parts)
- The offer and customer as actually pitched (OUTREACH_STATUS.md assumptions).
- Numbers straight from the app: Insights page export or screenshot.
- Your own reason for any change of plan.

## Next steps
1. Scaffold exists: `editing-project/{episode_002,shorts_002,shots}.json` are skeletons.
2. When the decision rule resolves, write the story in `templates/STORY_DEVELOPMENT_TEMPLATE.md`, then the script in `episode_002.json`.
3. Reuse the style config as is; run `tools/suggest_content.py` over the filming period for the Shorts.
