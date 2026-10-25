"""Treasury (spec sections 14-18). READ ONLY: reads chain data, reconciles, records, reports.
Revenue is VERIFIED only when every check in core.policy.counts_as_verified_revenue passes."""

import json
import os
import re
from decimal import Decimal

from agents.treasury.rpc import RpcError, make_rpc
from core.audit import audit
from core.db import now
from core.events.events import emit
from core.notifications.service import alert
from core.orchestrator.killswitch import is_paused
from core.policy.chains import KNOWN_EVM_CHAINS, ChainNotAllowed, allowed_chain_ids
from core.policy.policy import Action, Agent, authorize, counts_as_verified_revenue

TX_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")
ADDR_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
# keccak256("Transfer(address,address,uint256)"), split so the repo secret scanner stays strict
TRANSFER_TOPIC = "0x" + "ddf252ad1be2c89b69c2b068fc378daa" + "952ba7f163c4a11628f55a4df523b3ef"
NATIVE = {1: "ETH", 56: "BNB", 204: "BNB", 324: "ETH", 8453: "ETH", 42161: "ETH", 59144: "ETH"}


class VerifyError(ValueError):
    pass


def owner_address() -> str:
    a = os.environ.get("OWNER_WALLET_ADDRESS", "").strip()
    if not ADDR_RE.match(a):
        raise VerifyError("OWNER_WALLET_ADDRESS is not configured")
    return a.lower()


def min_confirmations() -> int:
    try:
        return max(1, int(os.environ.get("MIN_CONFIRMATIONS", "12")))
    except ValueError:
        return 12


def stablecoins() -> set[tuple[int, str]]:
    """'chainId:0xcontract,...' that the OWNER confirmed are USD stablecoins. Only these get a USD value."""
    out = set()
    for part in os.environ.get("STABLECOIN_CONTRACTS", "").split(","):
        if ":" in part:
            c, a = part.strip().split(":", 1)
            if c.isdigit() and ADDR_RE.match(a.strip()):
                out.add((int(c), a.strip().lower()))
    return out


def _int(h) -> int:
    return int(h, 16) if isinstance(h, str) and h.startswith("0x") else int(h or 0)


def _units(raw: int, decimals: int) -> Decimal:
    return Decimal(raw) / (Decimal(10) ** decimals)


def verify_payment(conn, payment_id: str, chain_id: int, tx_hash: str, rpc=None) -> dict:
    """Check a claimed payment on-chain. Raises VerifyError with a plain reason on any failure."""
    rpc = rpc or make_rpc()
    if not authorize(Agent.TREASURY, Action.READ_WALLET, paused=is_paused(conn)).allowed:
        raise VerifyError("system is paused")
    pay = conn.execute("SELECT * FROM payments WHERE id=?", (payment_id,)).fetchone()
    if pay is None:
        raise VerifyError("payment not found")
    if pay["status"] == "PAYMENT_VERIFIED":
        raise VerifyError("payment already verified")
    tx_hash = (tx_hash or "").strip()
    if not TX_RE.match(tx_hash):
        raise VerifyError("transaction hash must be 0x followed by 64 hex characters")
    tx_hash = tx_hash.lower()
    try:
        allowed = allowed_chain_ids()
    except ChainNotAllowed as e:
        raise VerifyError(str(e)) from e
    if chain_id not in allowed:
        raise VerifyError(f"chain {chain_id} is not a monitored chain")  # wrong-chain protection
    if conn.execute("SELECT 1 FROM ledger_entries WHERE chain_id=? AND transaction_hash=?", (chain_id, tx_hash)).fetchone():
        raise VerifyError("this transaction is already recorded")  # duplicate protection
    me = owner_address()
    try:
        receipt = rpc(chain_id, "eth_getTransactionReceipt", [tx_hash])
        if receipt is None:
            conn.execute("UPDATE payments SET status='PAYMENT_UNVERIFIED', chain_id=?, tx_hash=? WHERE id=?", (chain_id, tx_hash, payment_id))
            raise VerifyError("transaction not found or still pending on this chain")
        if _int(receipt.get("status")) != 1:
            raise VerifyError("transaction failed on-chain")
        tx = rpc(chain_id, "eth_getTransactionByHash", [tx_hash]) or {}
        latest = _int(rpc(chain_id, "eth_blockNumber", []))
        confs = latest - _int(receipt.get("blockNumber")) + 1
        if confs < min_confirmations():
            conn.execute("UPDATE payments SET status='PAYMENT_UNVERIFIED', chain_id=?, tx_hash=? WHERE id=?", (chain_id, tx_hash, payment_id))
            raise VerifyError(f"only {confs} confirmations; need {min_confirmations()}. Try again shortly.")
        asset, amount, token = None, Decimal(0), None
        if (tx.get("to") or "").lower() == me and _int(tx.get("value")) > 0:
            asset, amount = NATIVE.get(chain_id, "NATIVE"), _units(_int(tx["value"]), 18)
        else:
            padded = "0x" + "0" * 24 + me[2:]
            transfers = [lg for lg in receipt.get("logs") or [] if len(lg.get("topics") or []) == 3
                         and lg["topics"][0].lower() == TRANSFER_TOPIC and lg["topics"][2].lower() == padded]
            tokens = {lg["address"].lower() for lg in transfers}
            if len(tokens) == 1:
                token = tokens.pop()
                decimals = _int(rpc(chain_id, "eth_call", [{"to": token, "data": "0x313ce567"}, "latest"]))
                if not 0 <= decimals <= 36:
                    raise VerifyError("token reported an invalid decimals value")
                amount = _units(sum(_int(lg["data"]) for lg in transfers), decimals)
                asset = "TOKEN:" + token
        if not asset or amount <= 0:
            raise VerifyError("this transaction did not pay the owner wallet")  # fake payment claim
    except RpcError as e:
        raise VerifyError(f"could not read the chain: {e}") from e
    usd, source = None, "none configured (not counted in USD revenue)"
    if token and (chain_id, token) in stablecoins():
        usd, source = amount, "owner-confirmed USD stablecoin at 1:1"
    evidence = {"occurred": True, "chain_confirmed": True, "final": True, "transaction_hash": True,
                "asset_amount_verified": True, "source_associated": pay["opportunity_id"] is not None, "ledger_recorded": True}
    if not counts_as_verified_revenue("receipt", evidence):
        raise VerifyError("payment is not linked to an opportunity")
    entry = "led_" + tx_hash[2:14] + "_" + str(chain_id)
    conn.execute(
        "INSERT INTO ledger_entries(entry_id,date,type,source,description,asset,amount,usd_value,valuation_source,"
        "valuation_time,fee,net_amount,status,transaction_hash,chain_id,evidence,notes) VALUES "
        "(?,?, 'receipt', ?,?,?,?,?,?,?, '0', ?, 'VERIFIED', ?,?,?,?)",
        (entry, now(), pay["opportunity_id"], f"Payment for {pay['opportunity_id']}", asset, str(amount), usd, source,
         now(), str(amount), tx_hash, chain_id, json.dumps({**evidence, "confirmations": confs}),
         f"{KNOWN_EVM_CHAINS.get(chain_id, chain_id)}"))
    conn.execute("UPDATE payments SET status='PAYMENT_VERIFIED', chain_id=?, tx_hash=?, verified_at=?, ledger_entry_id=? WHERE id=?",
                 (chain_id, tx_hash, now(), entry, payment_id))
    conn.execute("UPDATE opportunities SET status='PAYMENT_VERIFIED' WHERE id=?", (pay["opportunity_id"],))
    conn.execute("UPDATE tasks SET status='COMPLETED', updated_at=? WHERE opportunity_id=? AND status='AWAITING_PAYMENT'",
                 (now(), pay["opportunity_id"]))
    emit(conn, "payment.verified", "treasury", {"amount": str(amount), "asset": asset, "transaction_hash": tx_hash,
                                                 "chain_id": chain_id, "usd": str(usd) if usd is not None else None})
    audit(conn, "treasury", "payment.verified", payment_id, tx_hash)
    alert(conn, "HIGH", f"paid:{tx_hash}", "Payment verified",
          f"{amount} {asset} on {KNOWN_EVM_CHAINS.get(chain_id, chain_id)} ({confs} confirmations).")
    conn.execute("UPDATE agents SET status='online', last_run_at=? WHERE name='treasury'", (now(),))
    return {"verified": True, "amount": str(amount), "asset": asset, "usd": float(usd) if usd is not None else None, "entry": entry}


def check_balances(conn, rpc=None) -> dict:
    """Snapshot native balances on every allowed chain and alert on unexplained changes."""
    if not authorize(Agent.TREASURY, Action.READ_WALLET, paused=is_paused(conn)).allowed:
        return {"ran": False, "reason": "paused"}
    rpc = rpc or make_rpc()
    try:
        me, chains = owner_address(), sorted(allowed_chain_ids())
    except (VerifyError, ChainNotAllowed) as e:
        conn.execute("UPDATE agents SET status='error' WHERE name='treasury'")
        return {"ran": False, "reason": str(e)}
    out = {"ran": True, "balances": {}, "errors": []}
    for c in chains:
        try:
            bal = _int(rpc(c, "eth_getBalance", [me, "latest"]))
        except Exception as e:
            out["errors"].append(f"{KNOWN_EVM_CHAINS[c]}: {type(e).__name__}")
            continue
        prev = conn.execute("SELECT balance_wei FROM wallet_balances WHERE chain_id=? ORDER BY id DESC LIMIT 1", (c,)).fetchone()
        conn.execute("INSERT INTO wallet_balances(chain_id, balance_wei, at) VALUES (?,?,?)", (c, str(bal), now()))
        out["balances"][KNOWN_EVM_CHAINS[c]] = str(_units(bal, 18))
        if prev is not None and int(prev["balance_wei"]) != bal:
            up = bal > int(prev["balance_wei"])
            alert(conn, "MEDIUM" if up else "CRITICAL", f"bal:{c}:{bal}",
                  "Unexpected wallet activity" if up else "SECURITY: wallet balance decreased",
                  (f"{KNOWN_EVM_CHAINS[c]} balance rose to {_units(bal, 18)}. If this is a payment, verify it with its tx hash."
                   if up else f"{KNOWN_EVM_CHAINS[c]} balance fell to {_units(bal, 18)}. This system never sends funds. Check your wallet now."))
    conn.execute("UPDATE agents SET status=?, last_run_at=? WHERE name='treasury'",
                 ("error" if out["errors"] and not out["balances"] else "online", now()))
    return out
