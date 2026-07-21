"""M2: days-to-sell band classifier.

Labels come from the make-level "Days To Turn" benchmark: each training
row's make is mapped to an average days-to-sell, then to a band (Fast, Moderate,
Slow, Very slow). A HistGradientBoosting classifier learns to reproduce and
generalize that mapping from vehicle features. This is a benchmark-level
estimate, not a per-car duration.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.pipeline import Pipeline

from ..data.dtt_benchmark import DtsBenchmark
from ..features.engineering import build_features
from .preprocessing import build_preprocessor


def make_band_labels(df: pd.DataFrame, benchmark: DtsBenchmark) -> pd.Series:
    """Derive the band label for each row from its make via the benchmark."""
    return df["make"].map(benchmark.band_for)


class DaysToSellBandModel:
    def __init__(self, random_state: int = 42):
        self.model = Pipeline(
            steps=[
                ("pre", build_preprocessor()),
                (
                    "gb",
                    HistGradientBoostingClassifier(
                        max_iter=200,
                        learning_rate=0.1,
                        random_state=random_state,
                    ),
                ),
            ]
        )
        self.classes_: list[str] = []

    def fit(self, df: pd.DataFrame, benchmark: DtsBenchmark) -> "DaysToSellBandModel":
        X = build_features(df)
        y = make_band_labels(df, benchmark)
        self.model.fit(X, y)
        self.classes_ = list(self.model.named_steps["gb"].classes_)
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return self.model.predict(build_features(df))

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        """Class-probability matrix (n_rows x n_classes) for the band labels."""
        return self.model.predict_proba(build_features(df))

    def predict_confidence(self, df: pd.DataFrame) -> np.ndarray:
        """Confidence in the predicted band = probability of the argmax class."""
        return self.predict_proba(df).max(axis=1)
