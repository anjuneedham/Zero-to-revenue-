# Zero to Hero OS: session rules (auto-loaded every session)

**First action of every session:** read `docs/master/STATE.md` (about 1 page). It is the single source of truth for who the owner is, what the ventures are, what is decided, what is done, and what is next. Do not ask the owner for anything STATE.md already answers. If it is missing something the owner tells you, that is a bug: record it (see below).

The plan is `docs/master/MASTER_PLAN.md`: the first unchecked box is your task. STATE.md says which step is current.

## Capture rule (the fix for "it asked me again")
When the owner states a fact, decision, plan, name or preference, write it into `docs/master/STATE.md` in the SAME turn, before doing anything else. Chat is not memory; only committed files are. A new session sees nothing but the repo.

## End-of-task rule
Before ending any task, update STATE.md: move finished items to "Done" (one line + commit hash), set "Next" to exactly one concrete next step, list any open questions. Commit and push STATE.md together with the work. Never leave progress only in chat.

## Token rules
- One task per session. New session when the task is done, never across days.
- Read with offsets/limits or grep. Never dump whole files or tool results into chat.
- Write findings to files and refer to them. No sub-agents, no re-reading what STATE.md states.
- Docs first, code second. Run tests once at the end of a phase.

## Do not
Invent owner facts. If STATE.md has `UNKNOWN`, ask once, then write the answer in.
