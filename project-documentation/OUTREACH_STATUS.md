# Outreach Status

**Bottom line: this session cannot verify any outreach activity.** The prospect records live in the production Neon database
(`leads`, `user_actions`, `audit_events`). This session has no `DATABASE_URL`, and no export of those tables exists in any attached repo.
Nothing below is invented. Items are classified so you can see what is known and what is not.

## A. Confirmed activity (evidence in the repos)

| Fact | Evidence |
|---|---|
| The outreach tooling exists and a real Gmail send was performed to test it. | `docs/FOUNDERS_LOG.md` (26 Oct): "Operator can now send an approved draft itself, by email"; `IMPLEMENTATION_AUDIT.md`: "Gmail send ... verified with a real send". This was a **system test, not evidence of prospect outreach**. |
| A lead-database approach (Clay) was tried and rejected for the target market. | `docs/FOUNDERS_LOG.md` 26 Oct: Clay "doesn't reach small Jamaican trades businesses at all". |
| A conclusion was drawn that warm outreach must start with businesses already known to you. | Same entry. |
| Marketplace sourcing (Scout) produced 78 -> 121 "qualified" opportunities and **$0 verified revenue** as of 25-26 Oct. | `docs/FOUNDERS_LOG.md`. |
| No warm contractor contacts to interview as of 25 Oct. | `docs/strategy/OWNER_PROFILE.md`. |

## B. Existing recorded information

- Strategy documents: `BUILDFLOW_LAUNCH_PLAN.md` (sign 10 founding contractors; free 60 days for feedback + photos + testimonial;
  pitch: "your leads are yours, one flat monthly price, WhatsApp-first"), `OWNER_PROFILE.md`, `SOURCES_AND_WHAT_TO_DO.md`.
- A pricing hypothesis, **not validated**: $50/month incl. 1 user, +$20/extra user; service tiers $750-1,500 setup, $300-1,000/month retainer.
- Code for an outreach pipeline (CSV import, draft, approve, send), with unit tests using fixture data only.

## C. Missing information (cannot be determined from the repos)

1. How many businesses have been contacted, on which channel, on which dates.
2. Any replies, calls, meetings, trials, or paying customers.
3. Which offer is being sold in the outreach you describe as "already started" (BuildFlow? a YardScale service? something else?).
4. The message wording you used and any variants (needed for "which approach got responses").
5. Whether the BuildFlow Firebase Storage blocker and billing decision from the launch plan were resolved.
6. Current state of the Gmail token (7-day expiry per earlier audit).

## D. Assumptions requiring your confirmation

| # | Assumption used in drafts | If wrong |
|---|---|---|
| 1 | The operating business is selling **BuildFlow / related services to small trades businesses in Jamaica**. | Scene 3 of the script and the shot list change. Placeholders are marked `[CONFIRM OFFER]`. |
| 2 | The outreach "already started" happened mostly outside the app (DMs, WhatsApp, email, in person). | Then a one-time back-fill into the new pipeline is needed (the app supports a backdated `occurred_at`; see below). |
| 3 | No customer has paid yet. Script avoids revenue claims. | Add the verified figure only after Treasury verifies it. |
| 4 | Episode 001 starts the pipeline from today, with earlier activity entered as clearly-labelled back-filled records. | Alternatively mark earlier work as "before tracking began". |

## E. How the new platform keeps this honest

- Activity events carry both `at` (when it was recorded, immutable) and `occurred_at` (when it happened, owner-supplied). A back-filled
  prospect therefore shows *recorded today, happened on the 2nd*, never silently rewriting the past.
- Revenue entered when marking a prospect won is labelled **owner-recorded**; it does not become *verified revenue* until Treasury verifies a payment.
- Nothing in the new code sends a message. Recording "message sent" logs what you did. Sending stays on the existing approval-gated Gmail path.

## F. What I need from you to close the gaps

Either (a) paste or export your current prospect list (name, channel, date contacted, outcome) so it can be back-filled, or (b) tell me to
treat tracking as starting today. Optionally, tell me to search your Gmail *sent* folder for outreach so the status can be verified; I did not
read your mailbox without being asked.
