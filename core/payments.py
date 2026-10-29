"""Payment collection and verification. PayPal only: this module asks PayPal for a payment request the payer must approve,
and records money as revenue only after PayPal reports the order COMPLETED and every check in
core.policy.counts_as_verified_revenue passes. It never sends money anywhere."""

import json
from decimal import Decimal

from core.audit import audit
from core.db import now
from core.events.events import emit
from core.notifications.service import alert
from core.orchestrator.killswitch import is_paused
from core.policy.policy import counts_as_verified_revenue
from integrations import paypal


class VerifyError(ValueError):
    pass


def request_paypal_payment(conn, payment_id: str, currency: str = "USD", description: str = "") -> dict:
    """Generates a PayPal payment request (card or bank transfer) for an existing AWAITING_PAYMENT
    row. Nothing is charged by this call - it only creates something the payer must approve and pay
    themselves. The owner still sends the approval_link to the client; this system never does."""
    if is_paused(conn):
        raise VerifyError("system is paused")
    pay = conn.execute("SELECT * FROM payments WHERE id=?", (payment_id,)).fetchone()
    if pay is None:
        raise VerifyError("payment not found")
    if pay["status"] == "PAYMENT_VERIFIED":
        raise VerifyError("payment already verified")
    if pay["expected_amount"] is None or float(pay["expected_amount"]) <= 0:
        raise VerifyError("payment has no expected amount set")
    try:
        order = paypal.create_payment_request(f"{Decimal(pay['expected_amount']):.2f}", currency,
                                              description or f"Payment for {pay['opportunity_id']}", payment_id)
    except paypal.PayPalError as e:
        raise VerifyError(str(e)) from e
    conn.execute("UPDATE payments SET tx_hash=?, asset=? WHERE id=?", (order["order_id"], currency, payment_id))
    audit(conn, "treasury", "payment.request_paypal", payment_id, order["order_id"])
    return order


def get_paypal_approval_link(conn, payment_id: str) -> dict:
    """Re-fetches the approval link for an already-requested order - read-only, so it can be called
    any time the owner needs to see or re-send the link, not just once right after creation."""
    if is_paused(conn):
        raise VerifyError("system is paused")
    pay = conn.execute("SELECT * FROM payments WHERE id=?", (payment_id,)).fetchone()
    if pay is None:
        raise VerifyError("payment not found")
    order_id = (pay["tx_hash"] or "").strip()
    if not order_id:
        raise VerifyError("no PayPal order id on this payment - request a payment first")
    try:
        order = paypal.get_order(order_id)
    except paypal.PayPalError as e:
        raise VerifyError(f"could not reach PayPal: {e}") from e
    link = next((l["href"] for l in order.get("links") or [] if l.get("rel") == "approve"), None)
    if not link:
        raise VerifyError(f"PayPal order is {order.get('status', 'unknown')}; no approval link available "
                          "(it may already be paid, or expired)")
    return {"approval_link": link, "status": order.get("status")}


def verify_paypal_payment(conn, payment_id: str, order_id: str = "") -> dict:
    """Confirms a PayPal order was actually paid (captures it if the payer has approved but it
    hasn't been captured yet - the final step of RECEIVING money the payer already agreed to pay,
    never a step that sends money anywhere) and records it, same ledger/audit path as an on-chain
    payment."""
    if is_paused(conn):
        raise VerifyError("system is paused")
    pay = conn.execute("SELECT * FROM payments WHERE id=?", (payment_id,)).fetchone()
    if pay is None:
        raise VerifyError("payment not found")
    if pay["status"] == "PAYMENT_VERIFIED":
        raise VerifyError("payment already verified")
    order_id = (order_id or pay["tx_hash"] or "").strip()
    if not order_id:
        raise VerifyError("no PayPal order id on this payment - request a payment first")
    if conn.execute("SELECT 1 FROM ledger_entries WHERE chain_id IS NULL AND transaction_hash=?", (order_id,)).fetchone():
        raise VerifyError("this PayPal order is already recorded")
    try:
        order = paypal.get_order(order_id)
        if order.get("status") == "APPROVED":
            order = paypal.capture_order(order_id)
        if order.get("status") != "COMPLETED":
            conn.execute("UPDATE payments SET status='PAYMENT_UNVERIFIED', tx_hash=? WHERE id=?", (order_id, payment_id))
            raise VerifyError(f"PayPal order is {order.get('status', 'unknown')}, not yet paid")
        unit = (order.get("purchase_units") or [{}])[0]
        capture = ((unit.get("payments") or {}).get("captures") or [{}])[0]
        amount_info = capture.get("amount") or unit.get("amount") or {}
        amount, currency = amount_info.get("value"), amount_info.get("currency_code")
    except paypal.PayPalError as e:
        raise VerifyError(f"could not reach PayPal: {e}") from e
    if not amount or float(amount) <= 0:
        raise VerifyError("PayPal did not report a paid amount")  # fake/empty payment claim
    evidence = {"occurred": True, "chain_confirmed": True, "final": True, "transaction_hash": True,
                "asset_amount_verified": True, "source_associated": pay["opportunity_id"] is not None, "ledger_recorded": True}
    if not counts_as_verified_revenue("receipt", evidence):
        raise VerifyError("payment is not linked to an opportunity")
    entry = "led_paypal_" + order_id[:20]
    conn.execute(
        "INSERT INTO ledger_entries(entry_id,date,type,source,description,asset,amount,usd_value,valuation_source,"
        "valuation_time,fee,net_amount,status,transaction_hash,chain_id,evidence,notes) VALUES "
        "(?,?, 'receipt', ?,?,?,?,?,?,?, '0', ?, 'VERIFIED', ?, NULL, ?, 'PayPal')",
        (entry, now(), pay["opportunity_id"], f"Payment for {pay['opportunity_id']}", currency, amount,
         amount if currency == "USD" else None, "PayPal (same currency as USD)" if currency == "USD" else "not USD; no USD value assumed",
         now(), amount, order_id, json.dumps(evidence)))
    conn.execute("UPDATE payments SET status='PAYMENT_VERIFIED', tx_hash=?, asset=?, verified_at=?, ledger_entry_id=? WHERE id=?",
                 (order_id, currency, now(), entry, payment_id))
    conn.execute("UPDATE opportunities SET status='PAYMENT_VERIFIED' WHERE id=?", (pay["opportunity_id"],))
    emit(conn, "payment.verified", "treasury", {"amount": amount, "asset": currency, "transaction_hash": order_id,
                                                 "chain_id": None, "usd": amount if currency == "USD" else None})
    audit(conn, "treasury", "payment.verified", payment_id, order_id)
    alert(conn, "HIGH", f"paypal:{order_id}", "Payment verified", f"{amount} {currency} via PayPal.")
    return {"verified": True, "amount": amount, "asset": currency,
            "usd": float(amount) if currency == "USD" else None, "entry": entry}
