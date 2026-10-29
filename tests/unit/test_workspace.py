import json
import unittest
from datetime import date

from core import workspace
from dashboard.app import handle
from tests.authutil import session
from tests.dbutil import make_conn

TODAY = date(2026, 10, 29)


def item(status="posted", platform="tiktok", views=None, signups=None, posted_at="2026-10-29T10:00:00+00:00", **kw):
    return {"status": status, "platform": platform, "views": views, "signups": signups, "posted_at": posted_at, "format": None, "topic": None, **kw}


class ContentSummaryTest(unittest.TestCase):
    def test_empty(self):
        s = workspace.content_summary([], TODAY)
        self.assertEqual((s["posted_today"], s["posted_last_7_days"], s["by_platform"]), (0, 0, []))

    def test_averages_only_use_posts_with_recorded_views(self):
        s = workspace.content_summary([item(views=100), item(views=300), item(views=None)], TODAY)
        g = s["by_platform"][0]
        self.assertEqual((g["posts"], g["with_views"], g["avg_views"]), (3, 2, 200.0))
        self.assertEqual(s["posted_missing_metrics"], 1)

    def test_no_average_when_nothing_recorded_and_unposted_ignored(self):
        s = workspace.content_summary([item(), item(status="idea", views=999)], TODAY)
        self.assertIsNone(s["by_platform"][0]["avg_views"])
        self.assertEqual(s["by_status"]["idea"], 1)
        self.assertEqual(s["by_platform"][0]["posts"], 1)

    def test_cadence_windows(self):
        s = workspace.content_summary([item(posted_at="2026-10-29T01:00:00+00:00"), item(posted_at="2026-10-24T01:00:00+00:00"), item(posted_at="2026-10-22T01:00:00+00:00")], TODAY)
        self.assertEqual((s["posted_today"], s["posted_last_7_days"]), (1, 2))

    def test_groups_rank_by_average_views(self):
        s = workspace.content_summary([item(format="talking head", views=50), item(format="screen recording", views=500)], TODAY)
        self.assertEqual([g["name"] for g in s["by_format"]], ["screen recording", "talking head"])


class WorkspaceApiTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_conn()
        self.tok = session(self.conn)[0]

    def call(self, method, path, body=None, token="x"):
        token = self.tok if token == "x" else token
        c, _, out = handle(method, path, f"Bearer {token}" if token else None, self.conn, json.dumps(body).encode() if body is not None else b"")
        return c, json.loads(out)

    def make(self, biz, entity, **body):
        c, r = self.call("POST", f"/api/founder/businesses/{biz}/{entity}", body)
        self.assertEqual(c, 201, r)
        return r

    def test_requires_auth_and_unknown_business(self):
        self.assertEqual(self.call("GET", "/api/founder/workspace/buildflow", token=None)[0], 401)
        self.assertEqual(self.call("GET", "/api/founder/workspace/nope")[0], 404)
        self.assertEqual(self.call("POST", "/api/founder/workspace/agriloop/import-launch-plan")[0], 400)

    def test_empty_workspace_is_honest(self):
        c, w = self.call("GET", "/api/founder/workspace/buildflow")
        self.assertEqual(c, 200)
        self.assertEqual((w["tasks"], w["kpis"], w["feedback"], w["content"]["items"], w["pipeline"]["total"]), ([], [], [], [], 0))
        self.assertEqual(w["content"]["summary"]["posted_last_7_days"], 0)

    def test_business_isolation(self):
        self.make("buildflow", "work-tasks", title="BF task")
        self.make("agriloop", "work-tasks", title="AG task")
        self.make("agriloop", "feedback-items", body="farmer note")
        self.make("agriloop", "content-items", platform="tiktok")
        self.make("agriloop", "goals", title="AG goal")
        self.call("POST", "/api/founder/decisions", {"title": "cross-business"})
        w = self.call("GET", "/api/founder/workspace/buildflow")[1]
        self.assertEqual([t["title"] for t in w["tasks"]], ["BF task"])
        self.assertEqual((w["feedback"], w["content"]["items"], w["goals"], w["decisions"]), ([], [], [], []))
        self.assertNotIn("pipeline", self.call("GET", "/api/founder/workspace/agriloop")[1])

    def test_content_flow_and_metrics(self):
        c = self.make("buildflow", "content-items", platform="tiktok", topic="quotes", hook="Stop losing jobs", format="talking head")
        self.assertEqual(c["status"], "idea")
        self.assertIsNone(c["views"])
        self.assertEqual(self.call("POST", f"/api/founder/content-items/{c['id']}", {"status": "posted", "views": 120, "signups": 2})[0], 200)
        w = self.call("GET", "/api/founder/workspace/buildflow")[1]
        s = w["content"]["summary"]
        self.assertEqual((s["posted_today"], s["by_topic"][0]["avg_views"], s["by_topic"][0]["signups"]), (1, 120.0, 2))
        for bad in ({"platform": "myspace"}, {"platform": "tiktok", "views": -1}, {"platform": "tiktok", "views": "many"}):
            self.assertEqual(self.call("POST", "/api/founder/businesses/buildflow/content-items", bad)[0], 400, bad)

    def test_feedback_to_task_is_idempotent_and_scoped(self):
        f = self.make("buildflow", "feedback-items", source="WhatsApp", contact="Mr B", body="Cannot upload job photos", kind="bug")
        c, r = self.call("POST", f"/api/founder/feedback-items/{f['id']}/to-task")
        self.assertEqual((c, r["created"]), (200, True))
        r2 = self.call("POST", f"/api/founder/feedback-items/{f['id']}/to-task")[1]
        self.assertEqual((r2["created"], r2["task_id"]), (False, r["task_id"]))
        w = self.call("GET", "/api/founder/workspace/buildflow")[1]
        self.assertEqual(len(w["tasks"]), 1)
        self.assertTrue(w["tasks"][0]["title"].startswith("Feedback (bug): Cannot upload"))
        self.assertEqual(w["feedback"][0]["status"], "actioned")
        other = self.make("agriloop", "work-tasks", title="x")
        self.assertEqual(self.call("POST", f"/api/founder/feedback-items/{f['id']}", {"work_task_id": other["id"]})[0], 400)
        self.assertEqual(self.call("POST", "/api/founder/feedback-items/fb_nope/to-task")[0], 404)

    def test_launch_plan_import_is_idempotent_and_respects_ticks(self):
        plan = json.loads(workspace.PLAN.read_text())["buildflow"]
        self.call("POST", "/api/plan", {"id": plan[0]["id"], "done": True})
        r = self.call("POST", "/api/founder/workspace/buildflow/import-launch-plan")[1]
        self.assertEqual((r["created"], r["skipped"]), (len(plan), 0))
        self.assertEqual(self.call("POST", "/api/founder/workspace/buildflow/import-launch-plan")[1], {"created": 0, "skipped": len(plan)})
        w = self.call("GET", "/api/founder/workspace/buildflow")[1]
        self.assertEqual(len(w["tasks"]), len(plan) - 1)  # the ticked one is done, not open
        self.assertEqual(w["tasks"][0]["business_priority"], 1)

    def test_pipeline_counts_legacy_leads(self):
        self.conn.execute("INSERT INTO leads(id,name,business,email,status,created_at) VALUES ('l1','A','Co','a@x.com','NEW','2026-10-01'),('l2','B','Co2','b@x.com','SENT','2026-10-02')")
        p = self.call("GET", "/api/founder/workspace/buildflow")[1]["pipeline"]
        self.assertEqual((p["total"], p["counts"]["NEW"], p["counts"]["SENT"]), (2, 1, 1))

    def test_a_failing_section_does_not_break_the_workspace(self):
        self.conn.execute("ALTER TABLE content_items RENAME TO content_items_x")
        w = self.call("GET", "/api/founder/workspace/buildflow")[1]
        self.assertIn("error", w["content"])
        self.assertEqual(w["business"]["slug"], "buildflow")


if __name__ == "__main__":
    unittest.main()
