"""Shared preprocessing for the models.

Categorical features are ordinal-encoded (unknown categories map to -1), which
suits tree-based models and keeps dimensionality low even with high-cardinality
columns like `model`. Numeric features pass through unchanged.
"""

from __future__ import annotations

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OrdinalEncoder

from ..features.engineering import CATEGORICAL_FEATURES, NUMERIC_FEATURES


def build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            (
                "cat",
                OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1),
                CATEGORICAL_FEATURES,
            ),
            ("num", "passthrough", NUMERIC_FEATURES),
        ],
        remainder="drop",
    )
