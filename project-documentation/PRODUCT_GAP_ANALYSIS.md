# Product Gap Analysis

Status column reflects the state **after** this session's work. "Built" means implemented and covered by the tests in `PRODUCT_TEST_REPORT.md`.

| Brief requirement | Before | Now | Remaining |
|---|---|---|---|
| Prospect record with all listed fields | name/business/email/phone/notes only | Built: all fields except a separate "assigned playbook" column (it is `playbook_run_id`) and "current task" (derived: next open task) | Duplicate detection beyond email |
| Pipeline stages + outcomes | 5 send-status values | Built: 11 active stages, 6 closed, 2 parked outcomes | Kanban drag-and-drop (list + stage chips today) |
| Playbook engine (12 playbooks, editable) | none (static checklist) | Built: 12 built-ins; create, edit, add/remove/reorder steps, duplicate, archive, run, progress saved, past runs | Per-offer variants are done by duplicating; no sharing/import-export |
| Outreach recording | CSV + Gmail send | Built: prepare, record sent (channel, approach label, text), follow-up scheduling, response, meeting, proposal, close | One-click "send" from this screen for non-email channels (intentionally manual) |
| Daily command centre | Overview of agent/payment state | Built: objectives/targets, follow-ups, tasks, attention list, opportunities, meetings, recent activity, rule-based next actions, review | Calendar sync for meetings |
| Activity playback + business timeline | audit log + task events only | Built: per-prospect timeline, playback stepper with stage at each event, business-wide feed; append-only, `at` vs `occurred_at` | Playback is a stepper over records, **not** a video replay (by design, stated in the UI) |
| Reporting | agent health only | Built: all listed counts, conversion (counts-first), time between stages, recorded revenue, outstanding/overdue follow-ups | Cohorts, per-week trend charts |
| Learning | none | Built: facts vs hypotheses vs suggestions by channel/approach/industry/source, losses, consistency, playbook usage | Needs real data volume to say anything; no AI by design |
| Back-fill of existing outreach | n/a | `occurred_at` supported on every record | **No bulk import yet.** Needed once you share the real list |
| Authentication/permissions | owner-only | Unchanged; all new routes behind it | Team roles (brief says "expandable") |
| Deploy | manual | **Not deployed by this session** (needs your explicit go-ahead; migration 007 will run on first cold start) | Deploy, then smoke-test on Neon |

## Product risks (honest)
1. The system is only as good as the discipline of logging. The design pushes this (follow-up prompt on every send, daily review event), but a missed log is a missing fact.
2. Small samples: with a solo founder's first 20-50 prospects the learning section will mostly say "not enough data". That is intended.
3. The first real-data test is still ahead: everything verified so far used clearly labelled test records.
