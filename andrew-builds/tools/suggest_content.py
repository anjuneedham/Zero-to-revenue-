#!/usr/bin/env python3
"""Suggests short-form content ideas FROM WORK THAT ACTUALLY HAPPENED. It reads the app's append-only activity log (needs DATABASE_URL)
and, optionally, git commit subjects. Each suggestion lists its evidence. If nothing happened, it says so and suggests nothing:
the schedule never justifies inventing activity.
  DATABASE_URL=postgresql://... python3 suggest_content.py [--days 1] [--repo /path/to/repo ...]"""
import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone


def activity(days):
    import psycopg
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as c:
        rows = c.execute("SELECT kind, detail FROM activity_events WHERE occurred_at >= %s AND kind NOT IN ('legacy_import','prospect_deleted') ORDER BY id", (since,)).fetchall()
    return [(k, json.loads(d or "{}")) for k, d in rows]


def commits(repos, days):
    out = []
    for r in repos:
        res = subprocess.run(["git", "-C", r, "log", f"--since={days} days ago", "--pretty=%s", "--no-merges"], capture_output=True, text=True)
        out += [x for x in res.stdout.splitlines() if x.strip()]
    return out


def suggest(events, commit_subjects, days):
    k = Counter(e[0] for e in events)
    sent = [d for kind, d in events if kind == "message_sent"]
    resp = [d for kind, d in events if kind == "response_received"]
    lost = [d for kind, d in events if kind in ("deal_lost", "outcome_recorded") and d.get("reason")]
    out = []  # (priority, title, angle, evidence)
    if resp:
        s = Counter(d.get("sentiment") for d in resp)
        out.append((1, "A reply came in", "Show the Log-response screen (names hidden) and say what you learned from how they answered.", f"{len(resp)} response(s) recorded ({dict(s)})"))
    if sent:
        ang = Counter(d.get("angle") or "(no label)" for d in sent)
        ch = Counter(d.get("channel") for d in sent)
        out.append((2, f"I sent {len(sent)} real message(s)", "Explain the approach you tested and why. Never show who it went to.", f"{len(sent)} message(s) sent; approaches {dict(ang)}; channels {dict(ch)}"))
    if lost:
        out.append((3, "Why I lost one", "Tell the reason in your own words and what you'd change.", "reasons recorded: " + "; ".join(sorted({d['reason'][:60] for d in lost}))))
    if k["followup_completed"]:
        out.append((4, "The follow-up habit", "Show the Today screen and the follow-ups cleared; say what a follow-up adds.", f"{k['followup_completed']} follow-up(s) completed"))
    if k["proposal_delivered"] or k["meeting_held"] or k["meeting_booked"]:
        out.append((2, "A step closer to a conversation", "A meeting or proposal happened: say what led to it.", f"meetings booked {k['meeting_booked']}, held {k['meeting_held']}, proposals {k['proposal_delivered']}"))
    if commit_subjects:
        out.append((5, "What I changed in the tool", "Screen-record the changed feature working. Say the problem it fixes.", "commits: " + "; ".join(commit_subjects[:3])))
    if k["step_completed"] or k["playbook_completed"]:
        out.append((6, "Running a playbook", "Show one playbook step being completed and what it asks you to do.", f"{k['step_completed']} step(s), {k['playbook_completed']} playbook(s) completed"))
    out.sort()
    return out[:3]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=1)
    ap.add_argument("--repo", action="append", default=[])
    a = ap.parse_args()
    if not os.environ.get("DATABASE_URL"):
        sys.exit("DATABASE_URL is not set: no data source, so no suggestions (nothing is made up)")
    ev, cm = activity(a.days), commits(a.repo, a.days)
    print(f"Window: last {a.days} day(s). Recorded events: {len(ev)}. Commits: {len(cm)}.")
    s = suggest(ev, cm, a.days)
    if not s:
        print("\nNo recorded activity worth a video. Suggested shorts today: none. Do not publish filler.")
        return
    for i, (_, title, angle, ev_) in enumerate(s, 1):
        print(f"\n{i}. {title}\n   Angle: {angle}\n   Evidence: {ev_}")


if __name__ == "__main__":
    main()
