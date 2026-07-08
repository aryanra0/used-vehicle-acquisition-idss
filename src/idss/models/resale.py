"""M1: resale price regression.

Gradient-boosted trees on a log-transformed target (sold price is right-skewed),
inverted on output so errors are reported on the dollar scale.

Alongside the point estimate the model fits two quantile regressors (default the
10th and 90th percentiles) so every prediction carries an ~80% prediction
interval instead of a single number. It also exposes cheap per-instance
"ceteris paribus" explanations: how much each key feature moves this car's
resale versus a typical car.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.pipeline import Pipeline

from ..features.engineering import build_features
from .preprocessing import build_preprocessor

# Raw feature columns perturbed to their training reference for explanations.
_EXPLAIN_COLS = ("market_value", "mileage", "condition", "year")


class ResalePriceModel:
    """Predicts expected resale (sold) price in dollars, with an interval."""

    def __init__(self, random_state: int = 42, quantiles: tuple[float, float] = (0.1, 0.9)):
        self.random_state = random_state
        self.quantiles = quantiles
        self.model = self._make_regressor(loss="squared_error")
        # Lower/upper quantile models for the prediction interval.
        self._q_models: dict[float, TransformedTargetRegressor] = {}
        # Training reference values (medians) used for explanations.
        self.reference: dict[str, float] = {}

    def _make_regressor(self, loss: str, quantile: float | None = None):
        gb = HistGradientBoostingRegressor(
            loss=loss,
            quantile=quantile,
            max_iter=300 if loss == "squared_error" else 200,
            learning_rate=0.08,
            max_depth=None,
            random_state=self.random_state,
        )
        base = Pipeline(steps=[("pre", build_preprocessor()), ("gb", gb)])
        # Log-transform the skewed price target; invert on predict. Quantiles are
        # preserved under the monotonic log1p/expm1 transform.
        return TransformedTargetRegressor(regressor=base, func=np.log1p, inverse_func=np.expm1)

    def fit(self, df: pd.DataFrame) -> "ResalePriceModel":
        X = build_features(df)
        y = df["price"].astype(float).values
        self.model.fit(X, y)

        # Reference (typical) values for ceteris-paribus explanations.
        self.reference = {
            col: float(pd.to_numeric(df[col], errors="coerce").median())
            for col in _EXPLAIN_COLS
            if col in df.columns
        }

        # Quantile models for the prediction interval (share the same X, y).
        self._q_models = {}
        for q in self.quantiles:
            qm = self._make_regressor(loss="quantile", quantile=q)
            qm.fit(X, y)
            self._q_models[q] = qm
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        X = build_features(df)
        return np.clip(self.model.predict(X), 0, None)

    def predict_interval(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        """Lower/upper bounds of the prediction interval (per row).

        Returns (low, high). Falls back to (nan, nan) when quantile models are
        unavailable (e.g. an artifact trained before intervals were added).
        """
        if not self._q_models:
            n = len(df)
            nan = np.full(n, np.nan)
            return nan, nan
        X = build_features(df)
        qs = sorted(self._q_models)
        lo = np.clip(self._q_models[qs[0]].predict(X), 0, None)
        hi = np.clip(self._q_models[qs[-1]].predict(X), 0, None)
        # Guard against quantile crossing.
        return np.minimum(lo, hi), np.maximum(lo, hi)

    def explain_contributions(self, df: pd.DataFrame, reference: dict | None = None) -> list[dict]:
        """Per-instance contributions in dollars (single-row df expected).

        For each key feature, contribution = predict(actual) - predict(actual
        with that feature set to its training reference). Positive means this
        car's value for that feature pushes resale ABOVE a typical car's.
        """
        ref = reference or self.reference
        if not ref:
            return []
        base = float(self.predict(df)[0])
        out: list[dict] = []
        for col in _EXPLAIN_COLS:
            if col not in df.columns or col not in ref:
                continue
            alt = df.copy()
            alt[col] = ref[col]
            alt_pred = float(self.predict(alt)[0])
            out.append(
                {
                    "feature": col,
                    "value": df[col].iloc[0],
                    "reference": ref[col],
                    "contribution": base - alt_pred,
                }
            )
        out.sort(key=lambda d: abs(d["contribution"]), reverse=True)
        return out
