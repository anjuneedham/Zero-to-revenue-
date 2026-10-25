"""Chains Treasury may monitor for the owner's EVM address (read-only).

A chain must be in this table AND listed in OWNER_WALLET_CHAIN_IDS. Anything
else is ignored, never counted as revenue. Only IDs verified by the owner/docs
belong here; add others deliberately.
"""

import os

KNOWN_EVM_CHAINS = {
    1: "Ethereum",
    56: "BNB Chain",
    204: "opBNB",
    324: "ZKsync Era",
    8453: "Base",
    42161: "Arbitrum One",
    59144: "Linea",
}
# In PancakeSwap's selector but not enabled until the chain ID is confirmed:
# Monad, Robinhood Chain, Arc. Solana/Aptos need their own (non-EVM) addresses.


class ChainNotAllowed(ValueError):
    pass


def allowed_chain_ids(raw: str | None = None) -> frozenset[int]:
    raw = os.environ.get("OWNER_WALLET_CHAIN_IDS", "") if raw is None else raw
    ids = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        cid = int(part)
        if cid not in KNOWN_EVM_CHAINS:
            raise ChainNotAllowed(f"unknown chain id {cid}")
        ids.add(cid)
    if not ids:
        raise ChainNotAllowed("OWNER_WALLET_CHAIN_IDS is not configured; Treasury refuses to run")
    return frozenset(ids)


def require_allowed(chain_id: int, allowed: frozenset[int]) -> None:
    if chain_id not in allowed:
        raise ChainNotAllowed(f"chain {chain_id} is not monitored; ignoring")


# Free public read-only RPC endpoints (no key, no account). Replace with a
# dedicated provider later if rate limits bite. Verified 2026-10-25 via eth_chainId.
DEFAULT_RPC_URLS = {
    1: "https://ethereum-rpc.publicnode.com",
    56: "https://bsc-dataseed.binance.org",
    204: "https://opbnb-mainnet-rpc.bnbchain.org",
    324: "https://mainnet.era.zksync.io",
    8453: "https://mainnet.base.org",
    42161: "https://arb1.arbitrum.io/rpc",
    59144: "https://rpc.linea.build",
}

# Only these JSON-RPC methods may ever be sent. No signing or sending methods.
READ_ONLY_RPC_METHODS = frozenset({
    "eth_chainId", "eth_blockNumber", "eth_getBalance", "eth_call",
    "eth_getTransactionByHash", "eth_getTransactionReceipt", "eth_getLogs",
    "eth_getBlockByNumber",
})


def check_rpc_method(method: str) -> None:
    if method not in READ_ONLY_RPC_METHODS:
        raise ChainNotAllowed(f"RPC method {method} is not read-only")


def verify_endpoint_chain(expected_chain_id: int, reported_hex: str) -> None:
    if int(reported_hex, 16) != expected_chain_id:
        raise ChainNotAllowed(f"endpoint reports chain {int(reported_hex, 16)}, expected {expected_chain_id}")
