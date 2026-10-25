import unittest

from core.policy.policy import (
    Action, Agent, FORBIDDEN_ACTIONS, OpportunityStatus, authorize,
    classify_opportunity, counts_as_verified_revenue, is_zero_capital,
    opportunity_score, REQUIRED_PAYMENT_EVIDENCE,
)


class AuthorizeTest(unittest.TestCase):
    def test_forbidden_actions_refused_even_with_approval(self):
        for agent in Agent:
            for action in FORBIDDEN_ACTIONS:
                d = authorize(agent, action, paused=False, owner_approved=True)
                self.assertFalse(d.allowed, (agent, action))

    def test_kill_switch_blocks_work_but_not_owner_notification(self):
        self.assertFalse(authorize(Agent.SCOUT, Action.RESEARCH, paused=True).allowed)
        self.assertTrue(authorize(Agent.SCOUT, Action.NOTIFY_OWNER, paused=True).allowed)

    def test_agent_isolation(self):
        self.assertFalse(authorize(Agent.SCOUT, Action.SUBMIT_WORK,
                                   paused=False, owner_approved=True).allowed)
        self.assertFalse(authorize(Agent.TREASURY, Action.READ_EXTERNAL, paused=False).allowed)
        self.assertFalse(authorize(Agent.OPERATOR, Action.READ_WALLET, paused=False).allowed)

    def test_submission_requires_approval(self):
        d = authorize(Agent.OPERATOR, Action.SUBMIT_WORK, paused=False)
        self.assertFalse(d.allowed)
        self.assertTrue(d.requires_approval)
        self.assertTrue(authorize(Agent.OPERATOR, Action.SUBMIT_WORK,
                                  paused=False, owner_approved=True).allowed)


class ScoringTest(unittest.TestCase):
    FULL = dict(legitimacy=1, zero_capital=1, payment_clarity=1, skill_fit=1,
                repeatability=1, automation=1, deadline=1)

    def test_weights_sum_to_100(self):
        self.assertEqual(opportunity_score(self.FULL), 100)

    def test_missing_or_out_of_range_factor_rejected(self):
        with self.assertRaises(ValueError):
            opportunity_score({"legitimacy": 1})
        with self.assertRaises(ValueError):
            opportunity_score({**self.FULL, "deadline": 2})

    def test_classification_thresholds(self):
        self.assertEqual(classify_opportunity(65, 35), OpportunityStatus.QUALIFIED)
        self.assertEqual(classify_opportunity(64, 10), OpportunityStatus.REVIEW_REQUIRED)
        self.assertEqual(classify_opportunity(90, 36), OpportunityStatus.REVIEW_REQUIRED)

    def test_capital_required_is_not_zero_capital(self):
        self.assertTrue(is_zero_capital(0))
        self.assertFalse(is_zero_capital(0.01))


class RevenueTest(unittest.TestCase):
    ALL = {k: True for k in REQUIRED_PAYMENT_EVIDENCE}

    def test_fully_verified_receipt_counts(self):
        self.assertTrue(counts_as_verified_revenue("receipt", self.ALL))

    def test_non_revenue_types_never_count(self):
        for t in ("self_transfer", "loan", "unrealized_gain", "promised_payment",
                  "pending_bounty", "estimated_earnings"):
            self.assertFalse(counts_as_verified_revenue(t, self.ALL))

    def test_any_missing_check_fails(self):
        for k in REQUIRED_PAYMENT_EVIDENCE:
            self.assertFalse(counts_as_verified_revenue("receipt", {**self.ALL, k: False}))
        # Truthy-but-not-True values (e.g. a claimed hash string) are not proof.
        self.assertFalse(counts_as_verified_revenue("receipt", {**self.ALL, "final": "yes"}))


if __name__ == "__main__":
    unittest.main()
