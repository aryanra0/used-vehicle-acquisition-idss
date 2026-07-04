"""Market-value benchmark lookup (real MMR medians from car_prices).

Builds a lookup table from the single-source training data so a user-entered
vehicle can be assigned a comparable market value. car_prices ships a real
Manheim MMR column, so that is the value used (Requirement 2, 12.3). The generic
`value_col` fallback (median `price`) is retained only for datasets without an
MMR column and is not exercised by the current single-source pipeline. Also
computes the price-vs-market delta for display.

Lookup falls back progressively when an exact match is missing:
    (make, model, year) -> (make, model) -> (make) -> global median
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class MmrLookup:
    def __init__(self, df: pd.DataFrame, value_col: str | None = None):
        # Prefer a real MMR column; else use retail price as the market-value proxy.
        if value_col is None:
            value_col = "mmr" if "mmr" in df.columns else "price"
        base = df
        # For the price proxy, prefer retail rows (closer to a buyer-facing value).
        if value_col == "price" and "source_channel" in df.columns:
            retail = df[df["source_channel"] == "retail"]
            if len(retail) > 1000:
                base = retail
        d = base[["make", "model", "year", value_col]].dropna()
        self._by_mmy = d.groupby(["make", "model", "year"])[value_col].median()
        self._by_mm = d.groupby(["make", "model"])[value_col].median()
        self._by_make = d.groupby("make")[value_col].median()
        self._global = float(d[value_col].median()) if len(d) else 0.0
        # Sample counts per group, used to score how reliable each match is.
        self._n_by_mmy = d.groupby(["make", "model", "year"])[value_col].size()
        self._n_by_mm = d.groupby(["make", "model"])[value_col].size()
        self._n_by_make = d.groupby("make")[value_col].size()
        self._n_global = int(len(d))

    @staticmethod
    def _norm(x) -> str:
        return str(x).strip().lower() if x is not None else ""

    def lookup(self, make: str, model: str, year: int) -> tuple[float | None, str]:
        """Return (mmr_estimate, match_level). mmr is None only if no data at all."""
        value, level, _ = self.lookup_detailed(make, model, year)
        return value, level

    def lookup_detailed(
        self, make: str, model: str, year: int
    ) -> tuple[float | None, str, int | None]:
        """Return (mmr_estimate, match_level, sample_size).

        sample_size is the number of comparable sales behind the matched median,
        or None when the artifact predates count tracking (backward compatible
        with model files trained before sample sizes were recorded).
        """
        make_n, model_n = self._norm(make), self._norm(model)
        n_mmy = getattr(self, "_n_by_mmy", None)
        n_mm = getattr(self, "_n_by_mm", None)
        n_make = getattr(self, "_n_by_make", None)

        try:
            value = float(self._by_mmy.loc[(make_n, model_n, int(year))])
            n = int(n_mmy.loc[(make_n, model_n, int(year))]) if n_mmy is not None else None
            return value, "make/model/year", n
        except (KeyError, ValueError, TypeError):
            pass
        try:
            value = float(self._by_mm.loc[(make_n, model_n)])
            n = int(n_mm.loc[(make_n, model_n)]) if n_mm is not None else None
            return value, "make/model", n
        except (KeyError, TypeError):
            pass
        try:
            value = float(self._by_make.loc[make_n])
            n = int(n_make.loc[make_n]) if n_make is not None else None
            return value, "make", n
        except (KeyError, TypeError):
            pass
        if self._global > 0:
            return self._global, "global", getattr(self, "_n_global", None)
        return None, "none", None


def price_vs_mmr_delta(price: float | None, mmr: float | None) -> float | None:
    """Fractional gap between a price and the market benchmark: (price-mmr)/mmr."""
    if price is None or mmr is None or mmr == 0:
        return None
    return (float(price) - float(mmr)) / float(mmr)
