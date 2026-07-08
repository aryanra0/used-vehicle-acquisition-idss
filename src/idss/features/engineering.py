"""Feature engineering shared by training and serving (single-source schema).

Every feature is knowable before acquisition (no target leakage). The sale
`price` is the target and is never a feature. The Manheim MMR benchmark is used
as a feature: it is an external market value published before the sale (not
derived from this row's sale price), and it is the single strongest predictor of
resale, so excluding it makes the estimate much weaker.

Only features the UI collects are used, so every input the user changes moves
the prediction (and its confidence).
"""

from __future__ import annotations

import pandas as pd

# car_prices is 2014-2015 auction data; measure age relative to the sale era so
# a 2015 car reads as ~1 year old (not ~10), keeping mileage/year realistic.
REFERENCE_YEAR = 2016

NUMERIC_FEATURES = [
    "vehicle_age",
    "mileage",
    "mileage_per_year",
    "condition",     # NaN handled natively by the tree models
    "market_value",  # real MMR benchmark (external, pre-sale); key predictor
]
CATEGORICAL_FEATURES = [
    "make",
    "model",
    "body",
    "transmission",
    "state",
    "color",
]
FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES

# The sale price is the only true leakage column; MMR is a legitimate feature.
LEAKAGE_COLUMNS = {"price"}


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer the model feature matrix from the cleaned input dataframe."""
    out = pd.DataFrame(index=df.index)

    year = pd.to_numeric(df.get("year"), errors="coerce")
    out["vehicle_age"] = (REFERENCE_YEAR - year).clip(lower=0)

    mileage = pd.to_numeric(df.get("mileage"), errors="coerce")
    out["mileage"] = mileage
    out["mileage_per_year"] = mileage / out["vehicle_age"].replace(0, 1)

    out["condition"] = pd.to_numeric(df.get("condition"), errors="coerce")
    out["market_value"] = pd.to_numeric(df.get("market_value"), errors="coerce")

    for col in CATEGORICAL_FEATURES:
        if col in df:
            series = df[col]
        else:
            series = pd.Series("unknown", index=df.index)
        out[col] = (
            series.astype("string").fillna("unknown").str.strip().str.lower()
        )

    # Impute residual numeric NaNs (except condition, left NaN for native handling).
    for col in ("vehicle_age", "mileage", "mileage_per_year", "market_value"):
        if out[col].isna().any():
            out[col] = out[col].fillna(out[col].median())

    assert_no_leakage(out)
    return out[FEATURE_COLUMNS]


def assert_no_leakage(features: pd.DataFrame) -> None:
    leaked = LEAKAGE_COLUMNS.intersection(features.columns)
    if leaked:
        raise ValueError(f"Leakage columns present in features: {sorted(leaked)}")
