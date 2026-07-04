"""Days-to-Sell benchmark from the Edmunds "Days To Turn" report.

Parses 2016-10-dtt.xls into a make -> average-days lookup and maps each make to
a sale-time band (Fast / Moderate / Slow / Very slow). This is a make-level
BENCHMARK, not a per-car duration (see PRD Section 6.7 / Requirement 11).

The DTT sheet layout (0-indexed rows):
  row  7  : "Manufacturer" header (13 monthly columns 1..13)
  rows 8-24: manufacturers
  row 27 : "Days To Turn (DTT) by Make" header
  row 28 : "Make" header
  rows 29-58: makes  (column 13 = latest month, Oct 2016)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from .. import config

# Column 13 is the most recent month (Oct 2016) in the report.
_LATEST_COL = 13
_MAKE_ROWS = range(29, 59)


class DtsBenchmark:
    """Make-level days-to-sell benchmark with band mapping."""

    def __init__(self, make_to_days: dict[str, float], overall_median: float):
        self._map = make_to_days
        self._overall_median = overall_median

    @property
    def overall_median(self) -> float:
        return self._overall_median

    def days_for(self, make: str) -> float:
        """Average days-to-sell for a make; falls back to the overall median."""
        if not make:
            return self._overall_median
        return self._map.get(make.strip().lower(), self._overall_median)

    def band_for(self, make: str) -> str:
        return config.days_to_band(self.days_for(make))

    def as_dict(self) -> dict[str, float]:
        return dict(self._map)


def load_benchmark(path: Optional[Path] = None) -> DtsBenchmark:
    """Parse the Edmunds DTT .xls into a DtsBenchmark."""
    path = Path(path) if path else config.DTT_BENCHMARK_XLS
    if not path.exists():
        raise FileNotFoundError(f"DTT benchmark not found at {path}")

    raw = pd.read_excel(path, sheet_name="DTT", engine="xlrd", header=None)

    make_to_days: dict[str, float] = {}
    for r in _MAKE_ROWS:
        label = raw.iat[r, 0]
        value = raw.iat[r, _LATEST_COL]
        if pd.isna(label) or pd.isna(value):
            continue
        label = str(label).strip().lower()
        if label in ("make", "industry", ""):
            continue
        try:
            make_to_days[label] = float(value)
        except (ValueError, TypeError):
            continue

    if not make_to_days:
        raise ValueError("No make-level DTT values parsed; check sheet layout.")

    overall_median = float(np.median(list(make_to_days.values())))
    return DtsBenchmark(make_to_days, overall_median)
