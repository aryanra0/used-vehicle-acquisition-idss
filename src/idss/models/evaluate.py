"""Model evaluation: metrics, baselines, per-state fairness, and release gate."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    mean_absolute_error,
    mean_squared_log_error,
    r2_score,
    roc_auc_score,
)


# M1 resale price
def regression_metrics(y_true, y_pred) -> dict:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = y_true > 0
    mape = float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask]))) if mask.any() else float("nan")
    yp = np.clip(y_pred, 0, None)
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "mape": mape,
        "rmsle": float(np.sqrt(mean_squared_log_error(y_true, yp))),
        "r2": float(r2_score(y_true, y_pred)),
    }


def resale_baseline_pred(train_df: pd.DataFrame, test_df: pd.DataFrame) -> np.ndarray:
    """Baseline: predict each vehicle's MMR (market value) as the resale price."""
    return test_df["mmr"].astype(float).values


def per_state_mae(test_df: pd.DataFrame, y_pred) -> dict:
    """MAE broken down by state (fairness check)."""
    tmp = test_df[["state", "sellingprice"]].copy()
    tmp["pred"] = np.asarray(y_pred, dtype=float)
    out = {}
    for state, g in tmp.groupby("state"):
        if len(g) >= 30:  # only report states with enough samples
            out[str(state)] = float(mean_absolute_error(g["sellingprice"], g["pred"]))
    return dict(sorted(out.items(), key=lambda kv: kv[1], reverse=True))


def confidence_vs_error(y_true, y_pred, mmr, edges=(0.05, 0.15)) -> dict:
    """Validate that 'low confidence' really does mean larger error.

    The serving layer lowers resale confidence when the model diverges from the
    market benchmark (MMR). Here we bucket held-out rows by that same relative
    divergence and report realized MAE per bucket. If MAE rises with divergence,
    the confidence signal is trustworthy.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mmr = np.asarray(mmr, dtype=float)
    div = np.abs(y_pred - mmr) / np.clip(np.abs(mmr), 1.0, None)
    buckets = {
        f"low_divergence(<{edges[0]:.0%})": div < edges[0],
        f"mid_divergence({edges[0]:.0%}-{edges[1]:.0%})": (div >= edges[0]) & (div < edges[1]),
        f"high_divergence(>={edges[1]:.0%})": div >= edges[1],
    }
    out = {}
    for name, mask in buckets.items():
        if mask.any():
            out[name] = {
                "n": int(mask.sum()),
                "mae": float(mean_absolute_error(y_true[mask], y_pred[mask])),
            }
    return out


def interval_metrics(y_true, low, high) -> dict:
    """Empirical coverage and average width of the prediction interval."""
    y_true = np.asarray(y_true, dtype=float)
    low = np.asarray(low, dtype=float)
    high = np.asarray(high, dtype=float)
    ok = np.isfinite(low) & np.isfinite(high)
    if not ok.any():
        return {"coverage": float("nan"), "avg_width": float("nan")}
    inside = (y_true[ok] >= low[ok]) & (y_true[ok] <= high[ok])
    return {
        "coverage": float(np.mean(inside)),
        "avg_width": float(np.mean(high[ok] - low[ok])),
    }


# M2 days-to-sell band
def classification_metrics(y_true, y_pred) -> dict:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro")),
    }


# M3 buy/pass
def trivial_f1(y_true) -> float:
    """F1 of the naive 'always predict positive' classifier (the bias floor)."""
    base = float(np.mean(np.asarray(y_true, dtype=int)))
    return (2 * base / (base + 1)) if base > 0 else 0.0


def binary_metrics(y_true, proba, threshold: float = 0.5) -> dict:
    """Report metrics at the tuned threshold, plus reference points:
    AUC/AUC-PR (threshold-independent skill) and the trivial 'always Buy' F1.
    """
    y_true = np.asarray(y_true, dtype=int)
    proba = np.asarray(proba, dtype=float)
    pred = (proba >= threshold).astype(int)
    has_both = len(np.unique(y_true)) > 1
    return {
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, pred)),
        "f1": float(f1_score(y_true, pred, zero_division=0)),
        "f1_at_0.5": float(f1_score(y_true, (proba >= 0.5).astype(int), zero_division=0)),
        "trivial_f1_baseline": trivial_f1(y_true),
        "roc_auc": float(roc_auc_score(y_true, proba)) if has_both else float("nan"),
        "auc_pr": float(average_precision_score(y_true, proba)) if has_both else float("nan"),
        "brier": float(brier_score_loss(y_true, proba)) if has_both else float("nan"),
        "positive_rate": float(np.mean(y_true)),
    }


# Release gate
def gate_m1(model_mae: float, baseline_mae: float, min_improvement: float = 0.05) -> bool:
    """M1 passes if it beats the MMR baseline MAE by at least min_improvement."""
    if baseline_mae <= 0:
        return False
    return (baseline_mae - model_mae) / baseline_mae >= min_improvement
