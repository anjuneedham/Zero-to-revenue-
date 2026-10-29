import unittest

from core.policy import policy
from core.policy.policy import REQUIRED_PAYMENT_EVIDENCE, counts_as_verified_revenue


class SafetyFlagsTest(unittest.TestCase):
    def test_money_movement_is_hard_disabled(self):
        self.assertEqual(policy.WALLET_MODE, "READ_ONLY")
        for flag in ("TRADING_ENABLED", "AUTO_SPENDING_ENABLED", "TRANSACTION_SIGNING_ENABLED", "CONTRACT_INTERACTION_ENABLED",
                     "BRIDGE_ENABLED", "SWAPS_ENABLED", "STAKING_ENABLED"):
            self.assertIs(getattr(policy, flag), False, flag)


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
