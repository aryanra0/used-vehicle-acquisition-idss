"""Single-source dataset: car_prices.csv (wholesale auction data).

We use one coherent source rather than blending three. car_prices is the only
source with a real Manheim Market Report (MMR) benchmark and a condition grade,
it uses consistent model naming (so lookups don't miss and fall back to a useless
make-level median), and every row is a wholesale sale, so the resale target and
the MMR benchmark are the same kind of number.

Schema produced:
    price (sellingprice), mmr, year, mileage, condition,
    make, model, body, transmission, state, color
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from .. import config

# Sanity bounds to drop impossible / outlier rows.
PRICE_MIN, PRICE_MAX = 500.0, 250_000.0
MILEAGE_MIN, MILEAGE_MAX = 1.0, 400_000.0
YEAR_MIN, YEAR_MAX = 1990, 2015

VALID_TRANSMISSIONS = {"automatic", "manual"}


def _num(series: pd.Series) -> pd.Series:
    """Strip non-numeric characters ($, commas, ' mi') and coerce to float."""
    return pd.to_numeric(
        series.astype("string").str.replace(r"[^0-9.]", "", regex=True),
        errors="coerce",
    )


def _txt(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().str.lower()


def load_car_prices(path: Optional[Path] = None, nrows: Optional[int] = None) -> pd.DataFrame:
    """Load and clean the car_prices auction dataset into the model schema."""
    path = Path(path) if path else config.PRIMARY_DATASET
    raw = pd.read_csv(path, nrows=nrows, on_bad_lines="skip", low_memory=False)
    raw.columns = [c.strip().lower() for c in raw.columns]

    df = pd.DataFrame(
        {
            "price": _num(raw["sellingprice"]),
            "mmr": _num(raw["mmr"]),
            "year": pd.to_numeric(raw["year"], errors="coerce"),
            "mileage": _num(raw["odometer"]),
            "condition": pd.to_numeric(raw["condition"], errors="coerce"),
            "make": _txt(raw["make"]),
            "model": _txt(raw["model"]),
            "body": _txt(raw["body"]),
            "transmission": _txt(raw["transmission"]),
            "state": _txt(raw["state"]),
            "color": _txt(raw["color"]),
        }
    )
    return _clean(df)


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=["price", "mmr", "year", "mileage", "make", "model"]).copy()
    df = df[
        df["price"].between(PRICE_MIN, PRICE_MAX)
        & df["mmr"].between(PRICE_MIN, PRICE_MAX)
        & df["mileage"].between(MILEAGE_MIN, MILEAGE_MAX)
        & df["year"].between(YEAR_MIN, YEAR_MAX)
    ]
    df["year"] = df["year"].astype(int)
    # The raw `transmission` column has contaminated values (e.g. "sedan" leaks
    # in from column misalignment); keep only the two valid categories.
    df.loc[~df["transmission"].isin(VALID_TRANSMISSIONS), "transmission"] = np.nan
    for col in ("body", "transmission", "state", "color"):
        df[col] = df[col].fillna("unknown").replace("", "unknown")
    df = df.drop_duplicates(
        subset=["price", "mmr", "year", "mileage", "make", "model", "state"]
    )
    return df.reset_index(drop=True)


def train_val_test_split(
    df: pd.DataFrame, test_frac: float = 0.20, val_frac: float = 0.15, seed: int = 42
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Random split into (train, val, test). val is carved out of the non-test rows.

    test  : held out for final metrics (never seen in training/tuning)
    val   : used to tune the M3 decision threshold
    train : everything else
    """
    test = df.sample(frac=test_frac, random_state=seed)
    rest = df.drop(test.index)
    val = rest.sample(frac=val_frac, random_state=seed)
    train = rest.drop(val.index)
    return (
        train.reset_index(drop=True),
        val.reset_index(drop=True),
        test.reset_index(drop=True),
    )


def persist_splits(train: pd.DataFrame, val: pd.DataFrame, test: pd.DataFrame) -> Path:
    """Write the splits to data/processed/ for transparency/reproducibility."""
    out_dir = config.DATA_DIR / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    train.to_csv(out_dir / "train.csv", index=False)
    val.to_csv(out_dir / "val.csv", index=False)
    test.to_csv(out_dir / "test.csv", index=False)
    return out_dir
