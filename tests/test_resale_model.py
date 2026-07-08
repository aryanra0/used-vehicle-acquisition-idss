"""Tests for M1 prediction intervals + per-instance explanations, and the
interval / confidence-vs-error evaluation helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd

from idss.models import evaluate
from idss.models.resale import ResalePriceModel


def _toy(n: int = 150, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    mmr = rng.uniform(5000, 30000, n)
    price = mmr * rng.uniform(0.9, 1.1, n)  # resale tracks MMR with noise
    return pd.DataFrame({
        "year": rng.integers(2008, 2016, n),
        "make": rng.choice(["kia", "ford", "bmw"], n),
        "model": rng.choice(["a", "b", "c"], n),
        "body": rng.choice(["suv", "sedan"], n),
        "transmission": rng.choice(["automatic", "manual"], n),
        "state": rng.choice(["ca", "tx"], n),
        "color": rng.choice(["white", "black"], n),
        "mileage": rng.uniform(10000, 120000, n),
        "condition": rng.uniform(1, 49, n),
        "market_value": mmr,
        "price": price,
    })


def test_predict_interval_is_ordered_and_finite():
    m = ResalePriceModel().fit(_toy())
    df = _toy(8, seed=1)
    lo, hi = m.predict_interval(df)
    assert np.all(np.isfinite(lo)) and np.all(np.isfinite(hi))
    assert np.all(lo <= hi)
    assert np.mean(hi - lo) > 0  # non-degenerate interval


def test_predict_interval_graceful_without_quantile_models():
    # A fresh (unfit) model has no quantile models -> nan interval, no crash.
    m = ResalePriceModel()
    lo, hi = m.predict_interval(pd.DataFrame({"x": [1, 2, 3]}))
    assert len(lo) == 3 and np.all(np.isnan(lo)) and np.all(np.isnan(hi))


def test_explanations_present_and_scoped():
    m = ResalePriceModel().fit(_toy())
    ex = m.explain_contributions(_toy(1, seed=2))
    assert len(ex) >= 1
    feats = {e["feature"] for e in ex}
    assert feats <= {"market_value", "mileage", "condition", "year"}
    # Sorted by absolute contribution (most influential first).
    contribs = [abs(e["contribution"]) for e in ex]
    assert contribs == sorted(contribs, reverse=True)


def test_explanations_empty_without_reference():
    m = ResalePriceModel()  # no fit -> no reference
    assert m.explain_contributions(pd.DataFrame({"market_value": [10000]})) == []


def test_interval_metrics_coverage():
    y = np.array([100.0, 200.0, 300.0, 400.0])
    lo = np.array([90.0, 180.0, 280.0, 380.0])
    hi = np.array([110.0, 220.0, 320.0, 420.0])
    m = evaluate.interval_metrics(y, lo, hi)
    assert m["coverage"] == 1.0
    # Widths are [20, 40, 40, 40] -> mean 35.
    assert m["avg_width"] == 35.0


def test_confidence_vs_error_buckets_by_divergence():
    # Predictions far from MMR should land in the high-divergence bucket.
    y_true = np.array([100.0, 100.0, 100.0])
    y_pred = np.array([101.0, 100.0, 200.0])  # 1%, 0%, 100% divergence
    mmr = np.array([100.0, 100.0, 100.0])
    out = evaluate.confidence_vs_error(y_true, y_pred, mmr)
    assert any("high_divergence" in k for k in out)
