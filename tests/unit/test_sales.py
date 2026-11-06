import json
import unittest

import psycopg

from core.sales import insights, pipeline, playbooks
from core.sales.events import NotFound
from dashboard import app as dash
from tests.authutil import session
from tests.dbutil import make_conn


class Api:
    def __init__(self, conn):
        self.conn = conn
        self.token = session(conn)[0]

    def call(self, method, path, data=None, token="__ok__"):
        authz = "Bearer " + (self.token if token == "__ok__" else token)
        code, _, body = dash.handle(method, "/api/sales/" + path, authz, self.conn, json.dumps(data).encode() if data is not None else b"")
        return code, json.loads(body)

    def post(self, path, data=None):
        return self.call("POST", path, data or {})

    def get(self, path):
        return self.call("GET", path)


class JourneyTest(unittest.TestCase):
    """The 15-step user journey from the brief, through the real HTTP handler with real auth."""

    def setUp(self):
        self.conn = make_conn()
        self.api = Api(self.conn)

    def test_full_journey(self):
        a = self.api
        # 1. create (only a business name required)
        code, v = a.post("prospects", {"business": "Smith Roofing"})
        self.assertEqual(code, 200, v)
        lid = v["prospect"]["id"]
        self.assertEqual(v["prospect"]["stage"], "identified")
        # 2. edit
        code, v = a.post(f"prospects/{lid}/update", {"industry": "roofing", "location": "Kingston", "source_channel": "referral",
                                                     "email": "Smith@Example.com", "deal_value": 750})
        self.assertEqual(v["prospect"]["industry"], "roofing")
        self.assertEqual(v["prospect"]["email"], "smith@example.com")
        # research + 3. qualify
        code, v = a.post(f"prospects/{lid}/research", {"notes": "Posts job photos, no quote form"})
        self.assertEqual(v["prospect"]["stage"], "researched")
        code, v = a.post(f"prospects/{lid}/qualify", {"decision": "qualified", "reasons": "fits target"})
        self.assertEqual(v["prospect"]["stage"], "qualified")
        self.assertEqual(v["prospect"]["qualification"], "qualified")
        # 4. assign a playbook, 5. execute steps
        pbs = a.get("playbooks")[1]["playbooks"]
        self.assertEqual(len([p for p in pbs if p["builtin_slug"]]), 12)
        init = next(p for p in pbs if p["builtin_slug"] == "initial-outreach")
        code, v = a.post(f"prospects/{lid}/playbook", {"playbook_id": init["id"]})
        run = v["active_run"]
        self.assertEqual(run["done_count"], 0)
        self.assertEqual(len(v["tasks"]), 1)
        self.assertEqual(v["tasks"][0]["kind"], "playbook")
        code, v = a.post(f"runs/{run['id']}/step", {"step_id": run["steps"][0]["id"], "done": True, "note": "email"})
        self.assertEqual(v["run"]["done_count"], 1)
        # 6. record outreach + 7. schedule follow-up in one go
        code, v = a.post(f"prospects/{lid}/outreach", {"channel": "email", "angle": "quote-page idea", "text": "Hi", "followup_in_days": 3})
        self.assertEqual(v["prospect"]["stage"], "contacted")
        self.assertIsNotNone(v["prospect"]["next_followup_at"])
        fu = next(t for t in v["tasks"] if t["kind"] == "follow_up")
        # 8. complete the follow-up
        code, r = a.post(f"tasks/{fu['id']}/complete", {"outcome": "sent nudge"})
        self.assertEqual(r["task"]["status"], "done")
        self.assertIsNone(a.get(f"prospects/{lid}")[1]["prospect"]["next_followup_at"])
        # 9. response + 10. pipeline moves
        code, v = a.post(f"prospects/{lid}/response", {"text": "Interested", "sentiment": "positive", "channel": "email"})
        self.assertEqual(v["prospect"]["stage"], "responded")
        code, v = a.post(f"prospects/{lid}/stage", {"to": "conversation"})
        self.assertEqual(v["prospect"]["stage"], "conversation")
        # 11. meeting, 12. proposal
        code, v = a.post(f"prospects/{lid}/meeting", {"when": "2099-01-05", "notes": "intro call"})
        self.assertEqual(v["prospect"]["stage"], "meeting_booked")
        code, v = a.post(f"prospects/{lid}/proposal", {"value": 900, "notes": "one page"})
        self.assertEqual(v["prospect"]["stage"], "proposal")
        self.assertEqual(v["prospect"]["deal_value"], 900)
        # 13. won
        code, v = a.post(f"prospects/{lid}/close", {"outcome": "won", "revenue": 900})
        self.assertEqual(v["prospect"]["stage"], "won")
        self.assertEqual(v["prospect"]["revenue_won"], 900)
        # closing skips leftover open tasks (the unfinished playbook step and the meeting)
        self.assertEqual(v["tasks"], [])
        # 14. timeline: complete, ordered, with the stage at each point
        kinds = [e["kind"] for e in v["timeline"]]
        for k in ("prospect_created", "research_completed", "qualification_decision", "playbook_started", "step_completed", "message_sent",
                  "followup_scheduled", "followup_completed", "response_received", "meeting_booked", "proposal_delivered", "deal_won"):
            self.assertIn(k, kinds)
        self.assertEqual([e["id"] for e in v["timeline"]], sorted(e["id"] for e in v["timeline"]))
        self.assertEqual(v["timeline"][0]["detail"]["stage_after"], "identified")
        self.assertEqual(v["timeline"][-1]["detail"]["stage_after"], "won")
        # 15. performance
        code, perf = a.get("insights/performance")
        c = perf["counts"]
        self.assertEqual((c["prospects_discovered"], c["initial_messages_sent"], c["responses_received"], c["positive_responses"],
                          c["meetings_booked"], c["proposals_sent"], c["customers_won"]), (1, 1, 1, 1, 1, 1, 1))
        self.assertEqual(perf["revenue_recorded"], {"USD": 900.0})
        self.assertIn("not verified", perf["revenue_note"].lower())
        self.assertTrue(all(r["pct"] is None for r in perf["conversion"]))  # tiny sample: counts only, no percentages
        code, learn = a.get("insights/learning")
        self.assertTrue(any("quote-page idea" in f["text"] for f in learn["facts"]))
        self.assertEqual(learn["hypotheses"], [])  # nothing speculative from one prospect

    def test_requires_auth_and_bounds(self):
        self.assertEqual(self.api.call("GET", "today", token="bad")[0], 401)
        self.assertEqual(dash.handle("GET", "/api/sales/today", None, self.conn, b"")[0], 401)
        big = {"business": "x", "notes": "y" * 70_000}
        self.assertEqual(self.api.post("prospects", big)[0], 400)
        self.assertEqual(self.api.get("nope")[0], 404)
        self.assertEqual(self.api.get("prospects/ld_missing")[0], 404)

    def test_validation_errors_are_clear(self):
        a = self.api
        self.assertEqual(a.post("prospects", {})[0], 400)
        self.assertEqual(a.post("prospects", {"business": "A", "email": "nope"})[0], 400)
        self.assertEqual(a.post("prospects", {"business": "A", "deal_value": -5})[0], 400)
        lid = a.post("prospects", {"business": "A", "email": "a@example.com"})[1]["prospect"]["id"]
        code, r = a.post("prospects", {"business": "B", "email": "A@example.com"})
        self.assertEqual(code, 400)
        self.assertIn("already exists", r["error"])
        self.assertEqual(a.post(f"prospects/{lid}/stage", {"to": "bogus"})[0], 400)
        self.assertEqual(a.post(f"prospects/{lid}/stage", {"to": "won"})[0], 400)  # outcomes go through 'close'
        self.assertEqual(a.post(f"prospects/{lid}/outreach", {"channel": "pigeon"})[0], 400)
        self.assertEqual(a.post(f"prospects/{lid}/followup", {"due_date": "31/12/2026"})[0], 400)
        self.assertEqual(a.post(f"prospects/{lid}/followup", {"due_date": "2026-02-31"})[0], 400)
        self.assertEqual(a.post(f"prospects/{lid}/research", {"notes": "  "})[0], 400)
        self.assertEqual(a.post(f"prospects/{lid}/close", {"outcome": "follow_up_later"})[0], 400)  # needs a date
        self.assertEqual(a.post(f"prospects/{lid}/outreach", {"channel": "email", "occurred_at": "2999-01-01"})[0], 400)
        self.assertEqual(a.post(f"prospects/{lid}/bogus", {})[0], 404)

    def test_closing_outcomes_and_reopen(self):
        a = self.api
        lid = a.post("prospects", {"name": "Jo"})[1]["prospect"]["id"]
        code, v = a.post(f"prospects/{lid}/close", {"outcome": "follow_up_later", "resume_date": "2099-03-01", "reason": "busy season"})
        self.assertEqual(v["prospect"]["stage"], "follow_up_later")
        self.assertEqual(v["prospect"]["next_followup_at"], "2099-03-01")
        code, v = a.post(f"prospects/{lid}/stage", {"to": "contacted", "note": "they came back"})
        self.assertEqual(v["prospect"]["stage"], "contacted")
        self.assertIsNone(v["prospect"]["outcome"])
        self.assertTrue(v["timeline"][-1]["detail"]["reopened"])
        code, v = a.post(f"prospects/{lid}/close", {"outcome": "lost", "reason": "chose a competitor"})
        self.assertEqual(v["prospect"]["stage"], "lost")
        _, learn = a.get("insights/learning")
        self.assertTrue(any("chose a competitor" in f["text"] for f in learn["facts"]))
        # a message to a closed prospect does not silently reopen it
        a.post(f"prospects/{lid}/outreach", {"channel": "email"})
        self.assertEqual(a.get(f"prospects/{lid}")[1]["prospect"]["stage"], "lost")

    def test_not_qualified_closes_and_cleans_up(self):
        a = self.api
        lid = a.post("prospects", {"business": "Z"})[1]["prospect"]["id"]
        a.post(f"prospects/{lid}/followup", {"due_date": "2099-01-01"})
        v = a.post(f"prospects/{lid}/qualify", {"decision": "not_qualified", "reasons": "no budget"})[1]
        self.assertEqual(v["prospect"]["stage"], "not_qualified")
        self.assertEqual(v["tasks"], [])
        self.assertIsNone(v["prospect"]["next_followup_at"])


class IntegrityTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()

    def test_history_cannot_be_rewritten(self):
        lead = pipeline.create_prospect(self.conn, {"business": "Acme"})
        for sql in ("UPDATE activity_events SET summary='x'", "DELETE FROM activity_events", "TRUNCATE activity_events"):
            with self.assertRaises(psycopg.errors.RaiseException):
                self.conn.execute(sql)
        self.assertEqual(self.conn.execute("SELECT count(*) n FROM activity_events").fetchone()["n"], 1)
        self.assertEqual(lead["business"], "Acme")

    def test_editing_a_prospect_adds_events_and_never_edits_old_ones(self):
        lead = pipeline.create_prospect(self.conn, {"business": "Acme", "industry": "roofing"})
        pipeline.update_prospect(self.conn, lead["id"], {"industry": "plumbing", "email": "a@b.co", "phone": "+18765550123"})
        tl = pipeline.timeline(self.conn, lead["id"])
        self.assertEqual(tl[0]["detail"]["industry"], "roofing")  # the original record still says roofing
        ch = tl[1]["detail"]["changes"]
        self.assertEqual(ch["industry"], {"from": "roofing", "to": "plumbing"})
        self.assertEqual(ch["email"], {"changed": True})  # personal data is not copied into the log
        self.assertNotIn("a@b.co", json.dumps(tl))
        self.assertNotIn("8765550123", json.dumps(tl))

    def test_backfill_keeps_recorded_and_occurred_times_separate(self):
        lead = pipeline.create_prospect(self.conn, {"business": "Old"}, occurred_at="2026-10-20")
        e = pipeline.timeline(self.conn, lead["id"])[0]
        self.assertTrue(e["occurred_at"].startswith("2026-10-20"))
        self.assertGreater(e["at"], e["occurred_at"])

    def test_logging_earlier_work_never_moves_a_prospect_backwards(self):
        lead = pipeline.create_prospect(self.conn, {"business": "Acme"})
        pipeline.record_outreach(self.conn, lead["id"], "email")
        pipeline.record_research(self.conn, lead["id"], "late research")
        pipeline.prepare_message(self.conn, lead["id"], "email", "x", "draft")
        self.assertEqual(pipeline.get_lead(self.conn, lead["id"])["stage"], "contacted")

    def test_recording_a_meeting_as_held_finishes_its_booked_task(self):
        lead = pipeline.create_prospect(self.conn, {"business": "Acme"})
        pipeline.record_meeting(self.conn, lead["id"], "2099-01-05")
        self.assertEqual([t["kind"] for t in pipeline.list_tasks(self.conn, "open")], ["meeting"])
        pipeline.record_meeting(self.conn, lead["id"], "2099-01-05", held=True)
        self.assertEqual(pipeline.list_tasks(self.conn, "open"), [])
        kinds = [e["kind"] for e in pipeline.timeline(self.conn, lead["id"])]
        self.assertEqual(kinds[-2:], ["meeting_booked", "meeting_held"])

    def test_deleting_a_prospect_keeps_its_history(self):
        lead = pipeline.create_prospect(self.conn, {"business": "Gone"})
        pipeline.delete_prospect(self.conn, lead["id"])
        kinds = [e["kind"] for e in pipeline.timeline(self.conn, lead["id"])]
        self.assertEqual(kinds, ["prospect_created", "prospect_deleted"])
        with self.assertRaises(NotFound):
            pipeline.get_lead(self.conn, lead["id"])


class PlaybookTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        playbooks.ensure_seed(self.conn)

    def test_seed_is_idempotent_and_never_overwrites_edits(self):
        pid = "pb_initial_outreach"
        playbooks.update(self.conn, pid, {"objective": "my words"})
        playbooks.ensure_seed(self.conn)
        self.assertEqual(playbooks.get(self.conn, pid)["objective"], "my words")
        self.assertEqual(self.conn.execute("SELECT count(*) n FROM playbooks").fetchone()["n"], 12)

    def test_every_builtin_has_the_required_content(self):
        for p in playbooks.list_all(self.conn):
            for f in ("name", "objective", "intended_user", "when_to_use", "expected_outcome", "completion_criteria", "next_recommended"):
                self.assertTrue(p[f], f"{p['name']} missing {f}")
            self.assertTrue(p["steps"] and p["prerequisites"] and p["recommended_actions"] and p["common_mistakes"], p["name"])
        self.assertTrue(all(p["example_messages"] for p in playbooks.list_all(self.conn) if p["builtin_slug"] in
                            ("initial-outreach", "follow-up", "proposal-preparation", "closing")))

    def test_duplicate_edit_reorder_add_remove_steps_and_archive(self):
        dup = playbooks.duplicate(self.conn, "pb_follow_up", "Follow-up for roofers")
        self.assertEqual(dup["parent_id"], "pb_follow_up")
        steps = dup["steps"]
        new = [steps[2], steps[0], {"title": "Call instead", "instruction": "Phone them"}]  # reorder, remove 2, add 1
        upd = playbooks.update(self.conn, dup["id"], {"steps": new, "when_to_use": "roofers only"})
        self.assertEqual([s["title"] for s in upd["steps"]], [steps[2]["title"], steps[0]["title"], "Call instead"])
        self.assertEqual(upd["steps"][0]["id"], steps[2]["id"])  # ids survive a reorder
        self.assertEqual(upd["version"], 2)
        self.assertEqual(playbooks.get(self.conn, "pb_follow_up")["version"], 1)  # the original is untouched
        self.assertEqual(playbooks.create(self.conn, {"name": "Mine"})["steps"][0]["title"], "First step")
        playbooks.set_archived(self.conn, dup["id"], True)
        self.assertNotIn(dup["id"], [p["id"] for p in playbooks.list_all(self.conn)])
        with self.assertRaises(ValueError):
            playbooks.start_run(self.conn, dup["id"])
        for bad in ({"steps": []}, {"steps": [{"title": ""}]}, {"name": " "}, {"prerequisites": "x"}):
            with self.assertRaises(ValueError):
                playbooks.update(self.conn, "pb_follow_up", bad)

    def test_run_snapshot_survives_playbook_edits_and_progress_persists(self):
        lead = pipeline.create_prospect(self.conn, {"business": "A"})
        run = playbooks.start_run(self.conn, "pb_prospect_research", lead["id"])
        n = len(run["steps"])
        playbooks.update(self.conn, "pb_prospect_research", {"steps": [{"title": "Only step"}]})
        s1 = run["steps"][0]["id"]
        run = playbooks.set_step(self.conn, run["id"], s1, True, "done it")
        self.assertEqual((len(run["steps"]), run["done_count"]), (n, 1))  # still the steps it started with
        self.assertEqual(playbooks.get_run(self.conn, run["id"])["progress"][s1]["note"], "done it")
        run = playbooks.set_step(self.conn, run["id"], s1, False)
        self.assertEqual(run["done_count"], 0)
        with self.assertRaises(ValueError):  # one live playbook per prospect
            playbooks.start_run(self.conn, "pb_follow_up", lead["id"])

    def test_completing_all_steps_completes_the_run_and_suggests_next(self):
        lead = pipeline.create_prospect(self.conn, {"business": "A"})
        run = playbooks.start_run(self.conn, "pb_qualification", lead["id"])
        for s in run["steps"]:
            run = playbooks.set_step(self.conn, run["id"], s["id"], True)
        self.assertEqual(run["status"], "completed")
        self.assertIsNone(pipeline.get_lead(self.conn, lead["id"])["playbook_run_id"])
        self.assertEqual(pipeline.list_tasks(self.conn, "open"), [])
        done = [e for e in pipeline.timeline(self.conn, lead["id"]) if e["kind"] == "playbook_completed"][0]
        self.assertIn("Initial outreach", done["detail"]["next_recommended"])
        with self.assertRaises(ValueError):
            playbooks.set_step(self.conn, run["id"], run["steps"][0]["id"], False)  # finished runs are history

    def test_completing_the_task_completes_the_step_and_next_task_appears(self):
        lead = pipeline.create_prospect(self.conn, {"business": "A"})
        run = playbooks.start_run(self.conn, "pb_prospect_research", lead["id"])
        t = pipeline.list_tasks(self.conn, "open")[0]
        pipeline.complete_task(self.conn, t["id"], "found site")
        run = playbooks.get_run(self.conn, run["id"])
        self.assertEqual(run["done_count"], 1)
        open_t = pipeline.list_tasks(self.conn, "open")
        self.assertEqual(len(open_t), 1)
        self.assertEqual(open_t[0]["step_id"], run["steps"][1]["id"])

    def test_abandon_records_how_far_it_got(self):
        lead = pipeline.create_prospect(self.conn, {"business": "A"})
        run = playbooks.start_run(self.conn, "pb_negotiation", lead["id"])
        playbooks.set_step(self.conn, run["id"], run["steps"][0]["id"], True)
        run = playbooks.abandon_run(self.conn, run["id"], "went cold")
        self.assertEqual(run["status"], "abandoned")
        self.assertEqual(pipeline.list_tasks(self.conn, "open"), [])
        self.assertIn("1/4", [e for e in pipeline.timeline(self.conn, lead["id"]) if e["kind"] == "playbook_abandoned"][0]["summary"])


class TodayAndInsightsTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()

    def test_empty_state_guides_the_first_step(self):
        t = insights.today_view(self.conn)
        self.assertEqual(t["pipeline"]["total"], 0)
        self.assertIn("Add your first prospect", [r["text"] for r in t["recommendations"]])
        perf = insights.performance(self.conn)
        self.assertEqual(perf["counts"]["customers_won"], 0)
        self.assertEqual(insights.learning(self.conn)["hypotheses"], [])

    def test_today_lists_due_overdue_and_progress_and_targets_are_configurable(self):
        a = pipeline.create_prospect(self.conn, {"business": "A"})
        pipeline.record_research(self.conn, a["id"], "notes")
        pipeline.schedule_followup(self.conn, a["id"], "2000-01-01")  # overdue
        pipeline.schedule_followup(self.conn, a["id"], "2999-01-01")  # not due
        t = insights.today_view(self.conn)
        self.assertEqual(len(t["followups_due"]), 1)
        self.assertGreater(t["followups_due"][0]["overdue_days"], 1000)
        self.assertTrue(any("overdue" in r["text"] for r in t["recommendations"]))
        research = next(x for x in t["targets"] if x["id"] == "research")
        self.assertEqual((research["done"], research["target"], research["met"]), (1, 5, False))
        insights.set_targets(self.conn, {"targets": {"research": 1, "touched": 0}})
        t = insights.today_view(self.conn)
        self.assertTrue(next(x for x in t["targets"] if x["id"] == "research")["met"])
        self.assertNotIn("touched", [x["id"] for x in t["targets"]])  # 0 = switched off
        for bad in ({"targets": {"nope": 1}}, {"targets": {"research": -1}}, {"targets": {"research": "5"}}, {"timezone": "Mars/Base"}):
            with self.assertRaises(ValueError):
                insights.set_targets(self.conn, bad)

    def test_backfilled_work_does_not_count_toward_today(self):
        a = pipeline.create_prospect(self.conn, {"business": "A"})
        pipeline.record_research(self.conn, a["id"], "old notes", occurred_at="2026-10-01")
        done = next(x for x in insights.today_view(self.conn)["targets"] if x["id"] == "research")
        self.assertEqual(done["done"], 0)

    def test_review_is_a_recorded_event(self):
        self.assertFalse(insights.today_view(self.conn)["review_done"])
        insights.record_review(self.conn, "good day")
        self.assertTrue(insights.today_view(self.conn)["review_done"])

    def test_percentages_only_with_a_real_sample_and_hypotheses_need_five(self):
        for i in range(6):
            lead = pipeline.create_prospect(self.conn, {"business": f"B{i}", "industry": "roofing"})
            pipeline.record_outreach(self.conn, lead["id"], "instagram", "cold dm")
        perf = insights.performance(self.conn)
        c = next(x for x in perf["conversion"] if x["step"].startswith("Responded"))
        self.assertEqual((c["n"], c["of"], c["pct"]), (0, 6, None))
        self.assertIn("too few", c["note"])
        hyp = insights.learning(self.conn)["hypotheses"]
        self.assertTrue(any("cold dm" in h["text"] and "0 responses from 6" in h["text"] for h in hyp))
        self.assertTrue(all(h["text"].startswith("Hypothesis") for h in hyp))

    def test_timezone_defines_today(self):
        insights.set_targets(self.conn, {"timezone": "Pacific/Kiritimati"})  # UTC+14
        self.assertEqual(insights.today_view(self.conn)["timezone"], "Pacific/Kiritimati")

    def test_attention_rules_use_recorded_facts(self):
        a = pipeline.create_prospect(self.conn, {"business": "Needs reply"})
        pipeline.record_outreach(self.conn, a["id"], "email")
        pipeline.record_response(self.conn, a["id"], "hi", "neutral")
        t = insights.today_view(self.conn)
        self.assertTrue(any(x["business"] == "Needs reply" and "responded" in x["reason"] for x in t["attention"]))
        self.assertTrue(any("Reply to 1" in r["text"] for r in t["recommendations"]))
        self.assertEqual([o["business"] for o in t["active_opportunities"]], ["Needs reply"])


if __name__ == "__main__":
    unittest.main()
