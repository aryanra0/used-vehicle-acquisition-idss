"""Tests for feature engineering (single-source schema): correctness and no leakage."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from idss.features import engineering as fe


def _frame():
    return pd.DataFrame(
        {
            "year": [2016, 2015],
            "make": ["Kia", "BMW"],
            "model": ["Sorento", "3 Series"],
            "body": ["SUV", "Sedan"],
            "transmission": ["automatic", "automatic"],
            "state": ["ca", "tx"],
            "color": ["white", "black"],
            "mileage": [0, 100000],
            "condition": [40, 30],
            "price": [21000, 14000],          # target — must NOT become a feature
            "market_value": [20000, 15000],   # real MMR — a legitimate feature
        }
    )


def test_feature_columns_present_and_no_leakage():
    feats = fe.build_features(_frame())
    assert list(feats.columns) == fe.FEATURE_COLUMNS
    assert not fe.LEAKAGE_COLUMNS.intersection(feats.columns)
    assert "price" not in feats.columns
    # MMR is now an intentional, non-leaking feature (external pre-sale benchmark).
    assert "market_value" in feats.columns


def test_vehicle_age_and_mileage_per_year():
    feats = fe.build_features(_frame())
    assert feats.loc[0, "vehicle_age"] == 0     # 2016 - 2016
    assert feats.loc[1, "vehicle_age"] == 1     # 2016 - 2015
    assert feats.loc[1, "mileage_per_year"] == 100000  # 100000 / 1


def test_missing_categorical_defaults_to_unknown():
    df = _frame().drop(columns=["color"])
    feats = fe.build_features(df)
    assert (feats["color"] == "unknown").all()


def test_no_missing_values_in_core_numeric():
    feats = fe.build_features(_frame())
    cols = ["vehicle_age", "mileage", "mileage_per_year", "market_value"]
    assert feats[cols].isna().sum().sum() == 0
