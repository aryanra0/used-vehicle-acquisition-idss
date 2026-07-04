"""Pluggable live current-market pricing.

Provides a *current* market value for a vehicle from a live listings API, so the
system is not limited to the 2014-2015 training data. MarketCheck is implemented
(free tier: ~500 calls/month); set the API key via the MARKETCHECK_API_KEY
environment variable. Without a key, get_provider() returns None and the caller
falls back to the ML model.

Uses only the standard library (urllib) so no extra dependency is required.
"""

from __future__ import annotations

import json
import os
import statistics
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class LivePrice:
    market_value: float          # current market value (median listing price)
    sample_size: int             # number of comparable live listings
    days_on_market: Optional[float]  # median DOM if available
    source: str                  # provider name


class MarketValueProvider(Protocol):
    name: str

    def market_value(
        self, make: str, model: str, year: int,
        mileage: Optional[float] = None, state: Optional[str] = None,
    ) -> Optional[LivePrice]:
        ...


class MarketCheckProvider:
    """MarketCheck active-listings provider. Computes current market value as the
    median price of comparable live listings."""

    name = "MarketCheck"

    def __init__(self, api_key: str, base_url: Optional[str] = None, timeout: float = 8.0):
        self.api_key = api_key
        self.base_url = (base_url or os.environ.get(
            "MARKETCHECK_BASE_URL", "https://mc-api.marketcheck.com/v2")).rstrip("/")
        self.timeout = timeout

    def market_value(
        self, make: str, model: str, year: int,
        mileage: Optional[float] = None, state: Optional[str] = None,
    ) -> Optional[LivePrice]:
        params = {
            "api_key": self.api_key,
            "make": make,
            "model": model,
            "year": str(year),
            "rows": "50",
            "stats": "price,dom",
        }
        if state:
            params["state"] = state
        url = f"{self.base_url}/search/car/active?" + urllib.parse.urlencode(params)
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None  # network/quota/schema error -> caller falls back

        listings = data.get("listings") or []
        prices = [float(x["price"]) for x in listings
                  if isinstance(x.get("price"), (int, float)) and x["price"] > 0]
        doms = [float(x["dom"]) for x in listings
                if isinstance(x.get("dom"), (int, float)) and x["dom"] >= 0]

        # Prefer server-side stats if present, else compute from listings.
        stats = data.get("stats", {}).get("price", {}) if isinstance(data.get("stats"), dict) else {}
        median_price = stats.get("median") or (statistics.median(prices) if prices else None)
        if not median_price:
            return None

        return LivePrice(
            market_value=float(median_price),
            sample_size=int(data.get("num_found", len(prices)) or len(prices)),
            days_on_market=(statistics.median(doms) if doms else None),
            source=self.name,
        )


def get_provider() -> Optional[MarketValueProvider]:
    """Return a live provider if configured (API key present), else None."""
    key = os.environ.get("MARKETCHECK_API_KEY", "").strip()
    if key:
        return MarketCheckProvider(key)
    return None
