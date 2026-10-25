"""Read-only reference exchange rates for the payment calculator (spec section 18: this is display
only, never used to value a receipt as USD revenue - that still requires an owner-confirmed
stablecoin contract in Treasury). Two free public, no-key APIs; a short cache keeps this from
hammering them on every page view."""

import time

from integrations.web.fetch import FetchError, fetch_json

CRYPTO_IDS = {"BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin", "USDC": "usd-coin",
              "USDT": "tether", "DAI": "dai", "SOL": "solana"}
CRYPTO_HOST = {"api.coingecko.com"}
FIAT_HOST = {"open.er-api.com"}
TTL_SECONDS = 300

_cache: dict = {}


def _fetch(fetch=fetch_json) -> dict:
    ids = ",".join(CRYPTO_IDS.values())
    crypto_raw = fetch(f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd", CRYPTO_HOST)
    crypto = {}
    for sym, cg_id in CRYPTO_IDS.items():
        v = (crypto_raw or {}).get(cg_id, {}).get("usd") if isinstance(crypto_raw, dict) else None
        if isinstance(v, (int, float)):
            crypto[sym] = float(v)
    fiat_raw = fetch("https://open.er-api.com/v6/latest/USD", FIAT_HOST)
    fiat_rates = fiat_raw.get("rates") if isinstance(fiat_raw, dict) else None
    fiat = {k: float(v) for k, v in (fiat_rates or {}).items()
            if isinstance(v, (int, float)) and k in ("JMD", "EUR", "GBP", "CAD")}
    return {"crypto_usd": crypto, "fiat_per_usd": fiat}


def get_rates(fetch=fetch_json, force: bool = False) -> dict:
    """Returns {as_of, stale, crypto_usd, fiat_per_usd}. Serves a cached copy within TTL_SECONDS;
    on fetch failure, serves the last good copy marked stale rather than erroring the page."""
    now_ts = time.time()
    cached = _cache.get("data")
    if not force and cached and now_ts - _cache.get("at", 0) < TTL_SECONDS:
        return {**cached, "stale": False}
    try:
        data = _fetch(fetch)
        if not data["crypto_usd"] and not data["fiat_per_usd"]:
            raise FetchError("empty rates response")
        result = {**data, "as_of": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_ts))}
        _cache["data"], _cache["at"] = result, now_ts
        return {**result, "stale": False}
    except FetchError:
        if cached:
            return {**cached, "stale": True}
        return {"crypto_usd": {}, "fiat_per_usd": {}, "as_of": None, "stale": True}
