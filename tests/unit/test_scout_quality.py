import os
import unittest
from unittest import mock

from agents.scout.evaluate import evaluate
from core.policy.policy import OpportunityStatus
from tests.unit.test_scout import good

SKILLS = {"python"}


class MinPaymentTest(unittest.TestCase):
    def test_default_bar_is_500_for_ordinary_work(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            cheap = evaluate(good(expected_payment=100, title="Redesign the onboarding flow", required_skills=["python", "design"]), skills=SKILLS)
            self.assertEqual(cheap.status, OpportunityStatus.REVIEW_REQUIRED)
            self.assertTrue(any(f.startswith("under_$500") for f in cheap.flags))
            big = evaluate(good(expected_payment=600), skills=SKILLS)
            self.assertEqual(big.status, OpportunityStatus.QUALIFIED)

    def test_cheap_but_clearly_easy_work_qualifies_below_the_floor(self):
        # The owner's rule: a small, quick job is worth doing even under $500, because it costs
        # almost no time. Only work that looks hard or unclear must clear the full bar.
        with mock.patch.dict(os.environ, {}, clear=True):
            cheap_easy = evaluate(good(expected_payment=75, title="Fix a small typo in the README", required_skills=["python"]), skills=SKILLS)
            self.assertEqual(cheap_easy.status, OpportunityStatus.QUALIFIED)
            self.assertFalse(any(f.startswith("under_$") for f in cheap_easy.flags))

    def test_cheap_and_hard_stays_under_review(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            hard = evaluate(good(expected_payment=300, title="Build a full platform migration end to end", required_skills=["python", "go", "rust"]), skills=SKILLS)
            self.assertEqual(hard.status, OpportunityStatus.REVIEW_REQUIRED)
            self.assertTrue(any(f.startswith("under_$500") for f in hard.flags))
            paid_enough = evaluate(good(expected_payment=600, title="Build a full platform migration end to end", required_skills=["python", "go", "rust"]), skills=SKILLS)
            self.assertEqual(paid_enough.status, OpportunityStatus.QUALIFIED)

    def test_bar_is_configurable(self):
        with mock.patch.dict(os.environ, {"MIN_EXPECTED_PAYMENT_USD": "100"}, clear=True):
            self.assertEqual(evaluate(good(expected_payment=150, title="Redesign the onboarding flow", required_skills=["python", "design"]), skills=SKILLS).status, OpportunityStatus.QUALIFIED)
        with mock.patch.dict(os.environ, {"MIN_EXPECTED_PAYMENT_USD": "not-a-number"}, clear=True):
            cheap = evaluate(good(expected_payment=100, title="Redesign the onboarding flow", required_skills=["python", "design"]), skills=SKILLS)
            self.assertEqual(cheap.status, OpportunityStatus.REVIEW_REQUIRED)  # falls back to 500


class SkillFitTest(unittest.TestCase):
    """A listing that is nothing like any configured skill gets flagged for removal, even if it is
    well-documented and risk-free - "fit" is about relevance, not legitimacy."""
    OWNER = {"sales", "customer service", "business operations", "websites", "funnels", "marketing",
             "growth planning", "app development"}

    def test_unrelated_physical_or_creative_work_is_flagged_off_skill(self):
        for title in ("Mobile Deep Tissue Massage", "R-22 Refill for Mitsubishi AC", "Sweet Romantic Poem Needed"):
            item = good(title=title, body="", required_skills=[], source="freelancer-com")
            e = evaluate(item, skills=self.OWNER)
            self.assertIn("off_skill", e.flags, title)
            self.assertEqual(e.status, OpportunityStatus.REVIEW_REQUIRED)

    def test_real_fit_is_never_flagged(self):
        for title in ("Modernize Existing Website Design", "Deploy Secure Node.js App to VPS", "B2B Appointment Setters"):
            item = good(title=title, body="", required_skills=[], source="freelancer-com")
            e = evaluate(item, skills=self.OWNER)
            self.assertNotIn("off_skill", e.flags, title)

    def test_no_configured_skills_means_neutral_fit(self):
        item = good(title="Mobile Deep Tissue Massage", body="", required_skills=[], source="freelancer-com")
        e = evaluate(item, skills=set())
        self.assertNotIn("off_skill", e.flags)

    def test_human_only_listing_is_never_flagged_off_skill_even_if_unrelated(self):
        item = good(title="Mobile Deep Tissue Massage", body="", required_skills=[], human_only=True, source="freelancer-com")
        e = evaluate(item, skills=self.OWNER)
        self.assertNotIn("off_skill", e.flags)

    def test_gate_does_not_apply_to_github_or_superteam_sources(self):
        # Those sources are software/crypto work by construction; an unmapped skill tag should
        # never get treated as "off skill" there the way a generic marketplace listing would.
        item = good(title="Mobile Deep Tissue Massage", body="", required_skills=[], source="github-bounty-label")
        e = evaluate(item, skills=self.OWNER)
        self.assertNotIn("off_skill", e.flags)


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


class RemotiveFreelanceTest(unittest.TestCase):
    SAMPLE = {"jobs": [
        {"title": "Software Engineer, AI Coding Tasks", "job_type": "contract", "salary": "$1000 per task",
         "url": "https://remotive.com/remote-jobs/software-development/x-1", "company_name": "Askable", "description": "Contract AI coding tasks."},
        {"title": "AI Trainer - Video Annotation", "job_type": "freelance", "salary": "70K-80K",
         "url": "https://remotive.com/remote-jobs/ai/x-2", "company_name": "iMerit", "description": "Annotate video."},
        {"title": "Tech Lead Full-Stack Rails Engineer", "job_type": "full_time", "salary": "$170k - $200k",
         "url": "https://remotive.com/remote-jobs/x-3", "company_name": "Acme"},
        "garbage", {"title": "no url", "job_type": "contract"},
    ]}

    def items(self, data=None):
        from agents.scout.sources import RemotiveFreelance
        seen = {}

        def fake(url, hosts, headers=None):
            seen["url"], seen["hosts"] = url, hosts
            return self.SAMPLE if data is None else data
        out = RemotiveFreelance(fetch=fake).items()
        self.assertTrue(seen["url"].startswith("https://remotive.com/api/remote-jobs"))
        self.assertEqual(seen["hosts"], {"remotive.com"})
        return out

    def test_keeps_only_contract_and_freelance_with_valid_url(self):
        items = self.items()
        self.assertEqual(len(items), 2)  # full_time dropped, garbage rows dropped, no-url row dropped
        self.assertEqual({i.title for i in items}, {"Software Engineer, AI Coding Tasks", "AI Trainer - Video Annotation"})

    def test_parses_a_dollar_amount_and_flags_unparseable_pay(self):
        items = self.items()
        parsed = next(i for i in items if "AI Coding Tasks" in i.title)
        self.assertEqual((parsed.expected_payment, parsed.payment_asset), (1000.0, "USD"))
        unparsed = next(i for i in items if "Video Annotation" in i.title)
        self.assertIsNone(unparsed.expected_payment)
        self.assertTrue(any("could not be parsed" in c for c in unparsed.caveats))

    def test_malformed_response_never_crashes(self):
        self.assertEqual(self.items({"jobs": "not a list"}), [])
        self.assertEqual(self.items({}), [])


class HimalayasContractTest(unittest.TestCase):
    PAGE1 = {"jobs": [
        {"title": "Senior UX Designer", "applicationLink": "https://himalayas.app/companies/acme/jobs/ux-1?utm_source=api",
         "companyName": "Acme", "excerpt": "Design work.", "categories": ["UI-UX-Designer"],
         "minSalary": None, "maxSalary": None, "salaryPeriod": "annual", "currency": "USD"},
        {"title": "AI Coding Contractor", "applicationLink": "https://himalayas.app/companies/askable/jobs/x?utm_source=api",
         "companyName": "Askable", "excerpt": "Contract coding.", "categories": ["Software-Engineer"],
         "minSalary": 100, "maxSalary": 100, "salaryPeriod": "hourly", "currency": "USD"},
        "garbage", {"title": "no link"}, {"applicationLink": "https://x/no-title"},
    ]}

    def items(self, pages=None):
        from agents.scout.sources import HimalayasContract
        seen = []

        def fake(url, hosts, headers=None):
            seen.append(url)
            if pages is not None:
                return pages.pop(0) if pages else {"jobs": []}
            return self.PAGE1 if len(seen) == 1 else {"jobs": []}
        out = HimalayasContract(fetch=fake).items()
        self.assertTrue(seen[0].startswith("https://himalayas.app/jobs/api/search?employment_type=Contractor"))
        return out

    def test_keeps_valid_rows_and_drops_malformed_ones(self):
        items = self.items()
        self.assertEqual({i.title for i in items}, {"Senior UX Designer", "AI Coding Contractor"})

    def test_never_treats_a_rate_as_a_fixed_project_price(self):
        items = self.items()
        for i in items:
            self.assertIsNone(i.expected_payment)
        hourly = next(i for i in items if "Coding" in i.title)
        self.assertTrue(any("100" in c and "hourly" in c and "not a fixed project price" in c for c in hourly.caveats), hourly.caveats)

    def test_stops_paging_on_an_empty_page(self):
        self.items()  # PAGE1 then one empty page from fake(); only 2 fetches should happen
        from agents.scout.sources import HimalayasContract
        calls = []

        def fake(url, hosts, headers=None):
            calls.append(url)
            return self.PAGE1 if len(calls) == 1 else {"jobs": []}
        HimalayasContract(fetch=fake, pages=5).items()
        self.assertEqual(len(calls), 2)

    def test_malformed_response_never_crashes(self):
        from agents.scout.sources import HimalayasContract
        self.assertEqual(HimalayasContract(fetch=lambda *a, **k: {"jobs": "nope"}).items(), [])
        self.assertEqual(HimalayasContract(fetch=lambda *a, **k: {}).items(), [])
