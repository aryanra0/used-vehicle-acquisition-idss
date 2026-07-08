"""M3: profitability / buy-pass classifier (calibrated, threshold-tuned).

Training label reflects how a dealership actually buys: it acquires a car at a
wholesale discount below market value (MMR) and resells it. A car is a "good
buy" if, purchased at that discount, its resale still clears the target margin:

    buy_price  = (1 - acquisition_discount) * mmr
    good_buy   = (sellingprice - buy_price) / buy_price >= target_margin

Features are pre-acquisition vehicle attributes plus MMR (the sold price itself
is never a feature). Probabilities are calibrated, and the decision threshold is
tuned on a validation set to maximize F1 (not fixed at 0.5).

Note: this dataset is wholesale/auction data, so `sellingprice` is a wholesale
value, not a final retail price. M3 therefore estimates profitability at the
wholesale level, a conservative proxy for a dealer's true retail margin.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import precision_recall_curve
from sklearn.pipeline import Pipeline

from ..features.engineering import build_features
from .preprocessing import build_preprocessor


def make_profit_labels(
    df: pd.DataFrame, acquisition_discount: float, target_margin: float
) -> pd.Series:
    """1 if buying at the wholesale discount clears the target margin, else 0.

    Uses `market_value` (the real Manheim MMR from car_prices) as the reference.
    The actual sale `price` stands in for realized value.
    """
    buy_price = (1.0 - acquisition_discount) * df["market_value"].replace(0, np.nan)
    gain = (df["price"] - buy_price) / buy_price
    return (gain >= target_margin).astype(int)


class ProfitabilityModel:
    def __init__(self, random_state: int = 42):
        pipe = Pipeline(
            steps=[
                ("pre", build_preprocessor()),
                (
                    "gb",
                    HistGradientBoostingClassifier(
                        max_iter=300,
                        learning_rate=0.1,
                        random_state=random_state,
                        class_weight="balanced",
                    ),
                ),
            ]
        )
        # Isotonic calibration (rank-based, numerically stable). Kept memory-safe
        # by calibrating on a capped sample in training (see train.py).
        self.model = CalibratedClassifierCV(pipe, method="isotonic", cv=3)
        self.threshold: float = 0.5  # tuned in choose_threshold()

    def fit(
        self, df: pd.DataFrame, acquisition_discount: float, target_margin: float
    ) -> "ProfitabilityModel":
        X = build_features(df)
        y = make_profit_labels(df, acquisition_discount, target_margin)
        self.model.fit(X, y)
        return self

    def choose_threshold(
        self, val_df: pd.DataFrame, acquisition_discount: float, target_margin: float
    ) -> float:
        """Pick the probability cutoff that maximizes F1 on a validation set."""
        y = make_profit_labels(val_df, acquisition_discount, target_margin)
        if y.nunique() < 2:
            self.threshold = 0.5
            return self.threshold
        proba = self.predict_proba(val_df)
        prec, rec, thr = precision_recall_curve(y, proba)
        f1 = 2 * prec * rec / (prec + rec + 1e-12)
        best = int(np.nanargmax(f1[:-1])) if len(thr) else 0
        self.threshold = float(thr[best]) if len(thr) else 0.5
        return self.threshold

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        """P(good buy) for each row."""
        proba = self.model.predict_proba(build_features(df))
        classes = list(self.model.classes_)
        idx = classes.index(1) if 1 in classes else -1
        return proba[:, idx]

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return (self.predict_proba(df) >= self.threshold).astype(int)
