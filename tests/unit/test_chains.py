import unittest

from core.policy.chains import ChainNotAllowed, allowed_chain_ids, require_allowed


class ChainsTest(unittest.TestCase):
    def test_unconfigured_refuses(self):
        with self.assertRaises(ChainNotAllowed):
            allowed_chain_ids("")

    def test_unknown_chain_rejected(self):
        with self.assertRaises(ChainNotAllowed):
            allowed_chain_ids("56,999999")

    def test_wrong_chain_ignored(self):
        allowed = allowed_chain_ids("56, 8453")
        require_allowed(56, allowed)
        with self.assertRaises(ChainNotAllowed):
            require_allowed(1, allowed)


if __name__ == "__main__":
    unittest.main()
