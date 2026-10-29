"""PayPal REST API client (sandbox or live). Scope is deliberately narrow: request a payment
(create an order the payer approves and pays by card or bank transfer) and confirm when it's
actually been paid. Nothing here ever sends, refunds, or pays anyone - the same hard rule as every
other wallet/payment integration in this system. PAYPAL_MODE controls sandbox vs live; defaults to
sandbox so a missing/misconfigured env var can never accidentally hit a real account."""

import base64
import json
import os
import urllib.error
import urllib.request

TIMEOUT = 15
MAX_BYTES = 1_000_000
HOSTS = {"sandbox": "https://api-m.sandbox.paypal.com", "live": "https://api-m.paypal.com"}


class PayPalError(RuntimeError):
    pass


def mode() -> str:
    return "live" if os.environ.get("PAYPAL_MODE", "sandbox").strip().lower() == "live" else "sandbox"


def _credentials() -> tuple[str, str]:
    cid, secret = os.environ.get("PAYPAL_CLIENT_ID", "").strip(), os.environ.get("PAYPAL_CLIENT_SECRET", "").strip()
    if not cid or not secret:
        raise PayPalError("PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET are not configured")
    return cid, secret


def _request(method: str, path: str, *, token: str | None = None, data: bytes | None = None,
             basic: tuple[str, str] | None = None) -> dict:
    url = HOSTS[mode()] + path
    headers = {"Content-Type": "application/x-www-form-urlencoded" if basic else "application/json",
               "Accept": "application/json", "User-Agent": "founder-os/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if basic:
        headers["Authorization"] = "Basic " + base64.b64encode(f"{basic[0]}:{basic[1]}".encode()).decode()
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # nosec - https only, fixed PayPal hosts
            raw = r.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as e:
        raise PayPalError(f"PayPal {method} {path} failed: HTTP {e.code} {e.read(500).decode(errors='replace')}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise PayPalError(f"PayPal {method} {path} failed: {type(e).__name__}") from e
    if len(raw) > MAX_BYTES:
        raise PayPalError("PayPal response too large")
    try:
        return json.loads(raw) if raw else {}
    except ValueError as e:
        raise PayPalError("PayPal response was not JSON") from e


def get_access_token(request=_request) -> str:
    cid, secret = _credentials()
    data = request("POST", "/v1/oauth2/token", basic=(cid, secret), data=b"grant_type=client_credentials")
    token = data.get("access_token")
    if not token:
        raise PayPalError("PayPal did not return an access token")
    return token


def create_payment_request(amount: str, currency: str, description: str, custom_id: str,
                            return_url: str = "", cancel_url: str = "", request=_request) -> dict:
    """Creates a PayPal Order the payer approves and pays by card, bank transfer, or PayPal
    balance - standard PayPal Checkout. Returns {order_id, approval_link}. This never moves money
    by itself: nothing is charged until the payer approves and it is captured."""
    token = get_access_token(request)
    body = {
        "intent": "CAPTURE",
        "purchase_units": [{"amount": {"currency_code": currency, "value": str(amount)},
                            "description": description[:127], "custom_id": custom_id[:127]}],
        "application_context": {"shipping_preference": "NO_SHIPPING", "user_action": "PAY_NOW",
                                **({"return_url": return_url, "cancel_url": cancel_url} if return_url else {})},
    }
    data = request("POST", "/v2/checkout/orders", token=token, data=json.dumps(body).encode())
    order_id = data.get("id")
    if not order_id:
        raise PayPalError(f"PayPal did not return an order id: {str(data)[:200]}")
    approval_link = next((l["href"] for l in data.get("links") or [] if l.get("rel") == "approve"), None)
    return {"order_id": order_id, "approval_link": approval_link, "status": data.get("status")}


def get_order(order_id: str, request=_request) -> dict:
    """Read-only: current state of an order (CREATED, APPROVED, COMPLETED, VOIDED, ...)."""
    token = get_access_token(request)
    return request("GET", f"/v2/checkout/orders/{order_id}", token=token)


def capture_order(order_id: str, request=_request) -> dict:
    """Collects funds the payer has already approved - the final step of RECEIVING a payment
    they agreed to, not an action that sends money anywhere. A no-op (PayPal returns the existing
    capture) if already captured."""
    token = get_access_token(request)
    return request("POST", f"/v2/checkout/orders/{order_id}/capture", token=token, data=b"{}")
