"""Read-only JSON-RPC client. Only allowlisted read methods; endpoint chain id is checked."""

import json
import os
import urllib.request
from urllib.parse import urlsplit

from core.policy.chains import DEFAULT_RPC_URLS, check_rpc_method, verify_endpoint_chain


class RpcError(RuntimeError):
    pass


def endpoint(chain_id: int) -> str:
    url = os.environ.get(f"RPC_URL_{chain_id}") or DEFAULT_RPC_URLS.get(chain_id, "")
    if urlsplit(url).scheme != "https":
        raise RpcError(f"no https RPC endpoint for chain {chain_id}")
    return url


def _post(url: str, method: str, params: list):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json",
                                                          "User-Agent": "zero-to-revenue-treasury/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:  # nosec - https only, allowlisted method
            data = json.loads(r.read(2_000_000))
    except Exception as e:
        raise RpcError(f"{method} failed: {type(e).__name__}") from e
    if "error" in data:
        raise RpcError(f"{method} error: {str(data['error'])[:120]}")
    return data.get("result")


def make_rpc(post=_post):
    checked = set()

    def rpc(chain_id: int, method: str, params: list):
        check_rpc_method(method)
        url = endpoint(chain_id)
        if chain_id not in checked:
            verify_endpoint_chain(chain_id, post(url, "eth_chainId", []))
            checked.add(chain_id)
        return post(url, method, params)
    return rpc
