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


class RpcTest(unittest.TestCase):
    def test_signing_and_sending_methods_blocked(self):
        from core.policy.chains import check_rpc_method
        for m in ("eth_sendRawTransaction", "eth_sendTransaction", "eth_sign", "personal_sign"):
            with self.assertRaises(ChainNotAllowed):
                check_rpc_method(m)
        check_rpc_method("eth_getBalance")

    def test_endpoint_chain_mismatch_rejected(self):
        from core.policy.chains import verify_endpoint_chain, DEFAULT_RPC_URLS, KNOWN_EVM_CHAINS
        verify_endpoint_chain(56, "0x38")
        with self.assertRaises(ChainNotAllowed):
            verify_endpoint_chain(56, "0x1")
        self.assertEqual(set(DEFAULT_RPC_URLS), set(KNOWN_EVM_CHAINS))
