import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from core import scheduler, weekly
from core.db import now
from tests.unit.test_challenge import ChallengeBase


def ago(days):
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


class WeeklyTest(ChallengeBase):
    def touch(self, lid, channel, outcome, direction="out", days=1):
        self.conn.execute("INSERT INTO lead_touches(id,lead_id,channel,direction,body,outcome,created_at) VALUES (?,?,?,?,?,?,?)",
                          (f"t_{lid}_{channel}_{outcome}_{days}", lid, channel, direction, "", outcome, ago(days)))

    def test_funnel_by_channel_and_plan_counts_only_the_window(self):
        a, b = self.lead(name="A", phone="1", channel="whatsapp"), self.lead(name="B", phone="2", channel="instagram")
        for i in range(6):
            self.touch(self.lead(name=f"W{i}", phone=f"9{i}", channel="whatsapp"), "whatsapp", "sent")
        self.touch(a, "whatsapp", "sent"); self.touch(a, "whatsapp", "replied", "in"); self.touch(a, "whatsapp", "booked")
        self.touch(b, "instagram", "sent"); self.touch(b, "instagram", "sent", days=20)  # old touch is outside the week
        d = self.call("POST", "/api/challenge/deal", {"lead_id": a})[1]
        self.verify(d["payment_id"], 500, when=ago(1))
        self.call("GET", "/api/challenge")  # sync paid status
        self.conn.execute("UPDATE deals SET paid_at=? WHERE id=?", (ago(1), d["deal_id"]))
        r = self.call("GET", "/api/challenge/weekly")[1]
        wa = next(c for c in r["by_channel"] if c["channel"] == "whatsapp")
        ig = next(c for c in r["by_channel"] if c["channel"] == "instagram")
        self.assertEqual((wa["sent"], wa["replies"], wa["booked"], wa["paid"], wa["paid_usd"]), (7, 1, 1, 1, 500.0))
        self.assertEqual((ig["sent"], ig["replies"], ig["paid"]), (1, 0, 0))
        self.assertEqual(r["funnel"], {"sent": 8, "replies": 1, "booked": 1, "paid": 1})
        std = next(p for p in r["by_plan"] if p["plan"] == "standard")
        self.assertEqual((std["deals_created"], std["paid"], std["paid_usd"]), (1, 1, 500.0))
        self.assertEqual({p["plan"] for p in r["by_plan"]}, {"standard", "buyer_basic", "farmer_premium"})

    def test_next_actions_are_rule_based(self):
        self.assertEqual(weekly.report(self.conn)["next_week"][0].startswith("No messages were logged"), True)
        lid = self.lead()
        self.call("POST", "/api/challenge/touch", {"lead_id": lid, "channel": "whatsapp", "direction": "in", "outcome": "replied"})
        acts = " ".join(weekly.report(self.conn)["next_week"])
        self.assertIn("Answer the 1 lead(s) who replied", acts)
        for i in range(10):
            self.touch(self.lead(name=f"Q{i}", phone=f"8{i}"), "facebook", "sent")
        acts = " ".join(weekly.report(self.conn)["next_week"])
        self.assertIn("Change or drop facebook", acts)

    def test_text_report_has_the_three_sections(self):
        t = weekly.render_text(weekly.report(self.conn))
        for h in ("WEEKLY REPORT", "BY CHANNEL", "BY PLAN", "NEXT WEEK"):
            self.assertIn(h, t)

    def test_requires_login(self):
        import dashboard.app as dash
        self.assertEqual(dash.handle("GET", "/api/challenge/weekly", "", self.conn, b"")[0], 401)


class SundayTickTest(ChallengeBase):
    def tick_at(self, when):
        real = scheduler.datetime

        class Fake(real):
            @classmethod
            def now(cls, tz=None):
                return when
        with mock.patch.object(scheduler, "datetime", Fake):
            return scheduler.tick(self.conn)

    def test_weekly_report_goes_out_once_on_sunday_only(self):
        sunday = datetime(2026, 11, 1, 7, 0, tzinfo=timezone.utc)
        self.assertEqual(sunday.weekday(), 6)
        monday = sunday + timedelta(days=1)
        self.tick_at(monday)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM notifications WHERE title LIKE 'Weekly report%'").fetchone()[0], 0)
        self.assertEqual(self.tick_at(sunday).get("weekly_report"), True)
        self.tick_at(sunday)  # retried cron the same day: no second report
        self.assertEqual(self.conn.execute("SELECT count(*) FROM notifications WHERE title LIKE 'Weekly report%'").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
