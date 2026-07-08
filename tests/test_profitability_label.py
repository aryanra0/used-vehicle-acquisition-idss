"""Tests for the M3 wholesale-acquisition profitability label."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from idss.models.profitability import make_profit_labels


def test_wholesale_label_logic():
    # Buy at 20% below market value, need 15% margin.
    #   market_value=10,000 -> buy=8,000 -> need price >= 8,000 * 1.15 = 9,200
    df = pd.DataFrame(
        {
            "market_value": [10000, 10000, 10000],
            "price": [9500, 9200, 9000],  # above, exactly at, below
        }
    )
    labels = make_profit_labels(df, acquisition_discount=0.20, target_margin=0.15)
    assert list(labels) == [1, 1, 0]


def test_bigger_discount_makes_more_deals_profitable():
    df = pd.DataFrame({"market_value": [10000] * 5, "price": [8500, 9000, 9500, 10000, 10500]})
    few = make_profit_labels(df, acquisition_discount=0.10, target_margin=0.15).sum()
    many = make_profit_labels(df, acquisition_discount=0.30, target_margin=0.15).sum()
    assert many >= few
