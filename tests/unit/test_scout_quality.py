import os
import unittest
from unittest import mock

from agents.scout.evaluate import evaluate
from core.policy.policy import OpportunityStatus
from tests.unit.test_scout import good

SKILLS = {"python"}


class MinPaymentTest(unittest.TestCase):
    def test_default_bar_is_500(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            cheap = evaluate(good(expected_payment=100, title="Fix the broken date picker"), skills=SKILLS)
            self.assertEqual(cheap.status, OpportunityStatus.REVIEW_REQUIRED)
            self.assertTrue(any(f.startswith("under_$500") for f in cheap.flags))
            big = evaluate(good(expected_payment=600), skills=SKILLS)
            self.assertEqual(big.status, OpportunityStatus.QUALIFIED)

    def test_easy_job_still_needs_the_full_500_floor(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            cheap_easy = evaluate(good(expected_payment=150, title="Fix a small typo in the README", required_skills=["python"]), skills=SKILLS)
            self.assertEqual(cheap_easy.status, OpportunityStatus.REVIEW_REQUIRED)
            self.assertFalse(any("harder_work" in f for f in cheap_easy.flags))

    def test_hard_job_needs_double_the_floor(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            hard_mid = evaluate(good(expected_payment=700, title="Build a full platform migration end to end", required_skills=["python", "go", "rust"]), skills=SKILLS)
            self.assertEqual(hard_mid.status, OpportunityStatus.REVIEW_REQUIRED)  # 700 < 2x500
            self.assertTrue(any("harder_work" in f for f in hard_mid.flags))
            hard_paid = evaluate(good(expected_payment=1200, title="Build a full platform migration end to end", required_skills=["python", "go", "rust"]), skills=SKILLS)
            self.assertEqual(hard_paid.status, OpportunityStatus.QUALIFIED)

    def test_bar_is_configurable(self):
        with mock.patch.dict(os.environ, {"MIN_EXPECTED_PAYMENT_USD": "100"}, clear=True):
            self.assertEqual(evaluate(good(expected_payment=150, title="Fix a parser bug"), skills=SKILLS).status, OpportunityStatus.QUALIFIED)
        with mock.patch.dict(os.environ, {"MIN_EXPECTED_PAYMENT_USD": "not-a-number"}, clear=True):
            cheap = evaluate(good(expected_payment=100, title="Fix the broken date picker"), skills=SKILLS)
            self.assertEqual(cheap.status, OpportunityStatus.REVIEW_REQUIRED)  # falls back to 500


class FreelancerComTest(unittest.TestCase):
    SAMPLE = {"status": "success", "result": {"total_count": 3, "projects": [
        {"id": 1, "title": "Rebuild checkout flow", "type": "fixed", "preview_description": "Full rebuild of the checkout flow with Stripe.",
         "budget": {"minimum": 500, "maximum": 1200}, "currency": {"code": "USD"}, "jobs": [{"name": "PHP"}, {"name": "React"}],
         "bid_stats": {"bid_count": 3, "bid_avg": 610.0}},
        {"id": 2, "title": "Below bar", "type": "fixed", "budget": {"minimum": 50, "maximum": 100}, "currency": {"code": "USD"}, "jobs": []},
        {"id": 3, "title": "Hourly not fixed", "type": "hourly", "budget": {"minimum": 20, "maximum": 40}, "currency": {"code": "USD"}, "jobs": []},
        "garbage", {"title": "no id"},
    ]}}

    def items(self, data=None):
        from agents.scout.sources import FreelancerCom
        seen = {}

        def fake(url, hosts, headers=None):
            seen["url"], seen["hosts"] = url, hosts
            return self.SAMPLE if data is None else data
        out = FreelancerCom(fetch=fake).items()
        self.assertTrue(seen["url"].startswith("https://www.freelancer.com/api/projects/"))
        self.assertEqual(seen["hosts"], {"www.freelancer.com"})
        return out

    def test_maps_only_fixed_projects_at_or_above_the_bar(self):
        items = self.items()
        self.assertEqual(len(items), 1)
        i = items[0]
        self.assertEqual((i.expected_payment, i.payment_asset, i.required_skills), (1200.0, "USD", ["PHP", "React"]))
        self.assertTrue(i.source_url.endswith("/projects/1"))
        self.assertTrue(any("bid(s) already placed" in c for c in i.caveats))
        self.assertIsNone(i.required_capital)

    def test_malformed_rows_never_crash(self):
        self.assertEqual(self.items({"result": {"projects": ["x", {}, None]}}), [])
        self.assertEqual(self.items({}), [])

    def test_feeds_into_evaluate_without_crashing_and_scores_reasonably(self):
        # Freelancer.com's compact API exposes no client name, so this never auto-qualifies on
        # legitimacy grounds alone; it still must not be mis-scored as a scam.
        with mock.patch.dict(os.environ, {}, clear=True):
            raw = self.items()[0]
            ev = evaluate(raw, skills={"php", "react"})
            self.assertEqual(ev.risk, 10)  # only unknown_organization, nothing scam-like
            self.assertLessEqual(ev.risk, 35)
            self.assertIn("missing_information", ev.row)
            self.assertIn("bid(s) already placed", ev.row["missing_information"])


class DailyReportTest(unittest.TestCase):
    def test_pin_movers_section_present(self):
        from core.reports import daily_report
        from tests.dbutil import make_conn
        conn = make_conn()
        report = daily_report(conn)
        self.assertTrue(report.startswith("PIN MOVERS"))
        self.assertIn("Nothing moved today", report)


if __name__ == "__main__":
    unittest.main()
