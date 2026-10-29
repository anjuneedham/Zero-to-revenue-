"""Hard safety rules for Founder OS.

Deliberately code, not configuration: financial and signing capabilities are hard-disabled and cannot be switched on
through environment variables or database settings, and money counts as revenue only when every verification check passes.
"""

# Hard-coded financial safety flags.
STARTING_CAPITAL = 0
WALLET_MODE = "READ_ONLY"
TRADING_ENABLED = False
AUTO_SPENDING_ENABLED = False
TRANSACTION_SIGNING_ENABLED = False
CONTRACT_INTERACTION_ENABLED = False
BRIDGE_ENABLED = False
SWAPS_ENABLED = False
STAKING_ENABLED = False


# --- Revenue verification ------------------------------------------------------

NON_REVENUE_TYPES = frozenset({
    "self_transfer", "loan", "unrealized_gain", "promised_payment",
    "pending_bounty", "estimated_earnings",
})

REQUIRED_PAYMENT_EVIDENCE = (
    "occurred", "chain_confirmed", "final", "transaction_hash",
    "asset_amount_verified", "source_associated", "ledger_recorded",
)


def counts_as_verified_revenue(entry_type: str, evidence: dict) -> bool:
    """Only a receipt with every verification check satisfied counts."""
    if entry_type in NON_REVENUE_TYPES or entry_type != "receipt":
        return False
    return all(evidence.get(check) is True for check in REQUIRED_PAYMENT_EVIDENCE)
