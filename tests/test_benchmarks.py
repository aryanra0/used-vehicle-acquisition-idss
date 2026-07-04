"""Tests for the DTT days-to-sell benchmark and the MMR lookup."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from idss import config
from idss.data import dtt_benchmark, mmr_lookup


def test_dtt_benchmark_parses_and_bands():
    b = dtt_benchmark.load_benchmark()
    d = b.as_dict()
    assert len(d) >= 20                      # ~30 makes expected
    assert 40 <= b.overall_median <= 105     # matches observed distribution
    # Known makes fall into expected bands.
    assert b.band_for("subaru") == "Fast"
    assert b.band_for("ram") == "Very slow"


def test_dtt_unknown_make_falls_back_to_median():
    b = dtt_benchmark.load_benchmark()
    assert b.days_for("not_a_real_make") == b.overall_median


def _mmr_frame():
    return pd.DataFrame(
        {
            "make": ["kia", "kia", "bmw", "bmw", "ford"],
            "model": ["sorento", "sorento", "3 series", "3 series", "f-150"],
            "year": [2015, 2015, 2014, 2014, 2013],
            "mmr": [20000, 21000, 31000, 33000, 15000],
        }
    )


def test_mmr_exact_match_uses_median():
    ml = mmr_lookup.MmrLookup(_mmr_frame())
    val, level = ml.lookup("Kia", "Sorento", 2015)
    assert val == 20500.0          # median of 20000, 21000
    assert level == "make/model/year"


def test_mmr_fallback_to_make():
    ml = mmr_lookup.MmrLookup(_mmr_frame())
    val, level = ml.lookup("Ford", "Unknown Model", 1999)
    assert val == 15000.0
    assert level == "make"


def test_price_vs_mmr_delta():
    assert mmr_lookup.price_vs_mmr_delta(21000, 20000) == 0.05
    assert mmr_lookup.price_vs_mmr_delta(None, 20000) is None
    assert mmr_lookup.price_vs_mmr_delta(21000, 0) is None
