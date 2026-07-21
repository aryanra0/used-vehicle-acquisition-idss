"""Train and evaluate the three models on a SINGLE source: car_prices.csv.

car_prices is the only source with a real MMR benchmark and condition grade, it
uses consistent model naming, and it is entirely wholesale, so the resale target
and MMR are comparable. Run from src/ (or with PYTHONPATH=src):

    python -m idss.train                # full dataset
    python -m idss.train --sample 20000 # cap rows (fast dev loop)
"""

from __future__ import annotations

import argparse
import gc
import json

import numpy as np
import pandas as pd

from . import config
from .data import dataset
from .data.dtt_benchmark import load_benchmark
from .data.mmr_lookup import MmrLookup
from .models import evaluate, registry
from .models.dts_band import DaysToSellBandModel, make_band_labels
from .models.profitability import ProfitabilityModel, make_profit_labels
from .models.resale import ResalePriceModel


def _attach_mmr_feature(*frames: pd.DataFrame) -> None:
    """Expose the real MMR column to the models as the `market_value` feature."""
    for df in frames:
        df["market_value"] = df["mmr"]


def _options_from(df: pd.DataFrame) -> dict:
    """Build UI dropdown options from the dataset so picks match the lookup."""
    def top(col, n):
        return sorted(df[col].value_counts().head(n).index.tolist())

    models_by_make = {}
    for mk, g in df.groupby("make"):
        models_by_make[mk] = sorted(g["model"].value_counts().head(40).index.tolist())
    return {
        "makes": sorted(df["make"].value_counts().head(60).index.tolist()),
        "models_by_make": models_by_make,
        "bodies": [b for b in top("body", 30) if b and b != "unknown"],
        "transmissions": ["automatic", "manual"],
        "colors": [c for c in top("color", 25) if c and c != "unknown"],
        "states": [s for s in top("state", 60) if s and s != "unknown"],
        "year_min": int(df["year"].min()),
        "year_max": int(df["year"].max()),
        "condition_min": 1.0,
        "condition_max": 49.0,
    }


def _heldout_make_eval(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    benchmark,
    holdout_frac: float = 0.2,
    sample_cap: int = 40_000,
    random_state: int = 42,
) -> dict:
    """M2 generalization check.

    The days-to-sell band is a deterministic function of `make` (a feature), so
    ordinary accuracy is ~1.0 and meaningless. The real question is whether the
    classifier can infer the band for makes it never saw in training (from body,
    mileage, state, etc.). Train on a subset of makes, evaluate on the held-out
    makes, and compare against a majority-band baseline.
    """
    makes = sorted(m for m in train_df["make"].dropna().unique())
    if len(makes) < 5:
        return {"heldout_make_available": False}

    rng = np.random.default_rng(random_state)
    order = list(makes)
    rng.shuffle(order)
    n_holdout = max(1, int(len(order) * holdout_frac))
    holdout = set(order[:n_holdout])

    train_sub = train_df[~train_df["make"].isin(holdout)]
    eval_sub = test_df[test_df["make"].isin(holdout)]
    if len(eval_sub) == 0 or make_band_labels(train_sub, benchmark).nunique() < 2:
        return {"heldout_make_available": False}
    if len(train_sub) > sample_cap:
        train_sub = train_sub.sample(n=sample_cap, random_state=random_state)

    model = DaysToSellBandModel().fit(train_sub, benchmark)
    y_true = make_band_labels(eval_sub, benchmark)
    y_pred = model.predict(eval_sub)
    metrics = evaluate.classification_metrics(y_true, y_pred)

    # Majority-band baseline: always predict the most common training band.
    majority = make_band_labels(train_sub, benchmark).mode().iat[0]
    majority_acc = float((y_true.values == majority).mean())

    return {
        "heldout_make_available": True,
        "heldout_make_accuracy": metrics["accuracy"],
        "heldout_make_macro_f1": metrics["macro_f1"],
        "heldout_make_majority_baseline_accuracy": majority_acc,
        "heldout_make_count": int(n_holdout),
        "heldout_make_eval_rows": int(len(eval_sub)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the IDSS models (car_prices only).")
    parser.add_argument("--sample", type=int, default=None,
                        help="Cap rows loaded before cleaning (faster dev loop).")
    args = parser.parse_args()

    print("Loading car_prices.csv ...")
    df = dataset.load_car_prices(nrows=args.sample)
    options = _options_from(df)  # capture before freeing df
    train_df, val_df, test_df = dataset.train_val_test_split(df)
    _attach_mmr_feature(train_df, val_df, test_df)
    out_dir = dataset.persist_splits(train_df, val_df, test_df)
    n_rows = len(df)
    print(f"  rows={n_rows:,}  train={len(train_df):,}  val={len(val_df):,}  "
          f"test={len(test_df):,}  -> splits in {out_dir}")
    del df
    gc.collect()  # free the full frame before the memory-heavy model training

    benchmark = load_benchmark()
    mmr_lookup = MmrLookup(train_df)  # real MMR medians by make/model/year
    margin = config.DEFAULT_TARGET_MARGIN
    discount = config.DEFAULT_ACQUISITION_DISCOUNT
    summary: dict = {}

    # M1 resale price
    print("Training M1 (resale price) ...")
    m1 = ResalePriceModel().fit(train_df)
    pred = m1.predict(test_df)
    m1_metrics = evaluate.regression_metrics(test_df["price"], pred)
    # Baseline: quote MMR as the resale. M1 must beat it by using
    # condition, mileage, etc.
    base_mae = float(np.mean(np.abs(test_df["price"].values - test_df["mmr"].values)))
    m1_metrics["mmr_baseline_mae"] = base_mae
    m1_metrics["beats_mmr_baseline"] = evaluate.gate_m1(m1_metrics["mae"], base_mae)
    per_state_mae = evaluate.per_state_mae(
        test_df.rename(columns={"price": "sellingprice"}), pred)
    m1_metrics["per_state_mae_top"] = dict(list(per_state_mae.items())[:5])
    # Prediction-interval quality: does the ~80% interval actually cover ~80%?
    lo, hi = m1.predict_interval(test_df)
    m1_metrics["interval_0.8"] = evaluate.interval_metrics(test_df["price"], lo, hi)
    # Trust check: larger divergence from MMR (what lowers serving confidence)
    # should track larger realized error.
    m1_metrics["confidence_vs_error"] = evaluate.confidence_vs_error(
        test_df["price"].values, pred, test_df["mmr"].values
    )
    summary["M1_resale"] = m1_metrics
    cov = m1_metrics["interval_0.8"]["coverage"]
    print(f"  M1 MAE=${m1_metrics['mae']:,.0f}  MAPE={m1_metrics['mape']:.1%}  "
          f"R2={m1_metrics['r2']:.3f}  MMR-baseline MAE=${base_mae:,.0f}  "
          f"beats={m1_metrics['beats_mmr_baseline']}  PI80 coverage={cov:.1%}")

    # M2 days-to-sell band
    print("Training M2 (days-to-sell band) ...")
    m2 = DaysToSellBandModel().fit(train_df, benchmark)
    m2_pred = m2.predict(test_df)
    m2_metrics = evaluate.classification_metrics(make_band_labels(test_df, benchmark), m2_pred)
    # Be explicit that headline accuracy is trivial: the band is a make-level
    # benchmark lookup and `make` is a feature, so seen makes are reproduced
    # perfectly. The generalization-to-unseen-makes number is the meaningful one.
    m2_metrics["label_is_deterministic_from_make"] = True
    m2_metrics["accuracy_note"] = (
        "Band = make-level days-to-turn benchmark lookup; `make` is a feature, so "
        "standard accuracy on seen makes is ~1.0 and not a measure of skill. "
        "Use heldout_make_accuracy for generalization to unseen makes."
    )
    m2_metrics.update(_heldout_make_eval(train_df, test_df, benchmark))
    summary["M2_dts_band"] = m2_metrics
    ho = m2_metrics.get("heldout_make_accuracy")
    ho_str = f"{ho:.3f}" if isinstance(ho, float) else "n/a"
    base = m2_metrics.get("heldout_make_majority_baseline_accuracy")
    base_str = f"{base:.3f}" if isinstance(base, float) else "n/a"
    print(f"  M2 accuracy={m2_metrics['accuracy']:.3f} (trivial: make->band lookup)  "
          f"heldout-make acc={ho_str} (majority baseline={base_str})  "
          f"macro_f1={m2_metrics['macro_f1']:.3f}")

    # Cap the calibration set, then FREE the full training frame: M1/M2 are done
    # with it, and CalibratedClassifierCV(cv=3) is memory-heavy, so keeping 368k
    # rows resident alongside it is what pushes the process over the limit.
    n_train = len(train_df)
    m3_train = train_df.sample(n=min(n_train, 60_000), random_state=42).copy()
    del train_df
    gc.collect()

    # M3 buy/pass
    print("Training M3 (buy/pass) ...")
    m3 = ProfitabilityModel().fit(m3_train, discount, margin)
    m3.choose_threshold(val_df, discount, margin)
    m3_proba = m3.predict_proba(test_df)
    m3_true = make_profit_labels(test_df, discount, margin)
    m3_metrics = evaluate.binary_metrics(m3_true, m3_proba, threshold=m3.threshold)
    summary["M3_buy_pass"] = m3_metrics
    del m3_train
    gc.collect()
    print(f"  M3 F1={m3_metrics['f1']:.3f} (thr={m3_metrics['threshold']:.2f}, "
          f"trivial={m3_metrics['trivial_f1_baseline']:.3f})  AUC={m3_metrics['roc_auc']:.3f}")

    # persist
    print("Saving models + lookups ...")
    meta = {
        "source": "car_prices",
        "rows_train": int(n_train),
        "rows_val": int(len(val_df)),
        "rows_test": int(len(test_df)),
    }
    registry.save_model("m1_resale", m1, {"metrics": m1_metrics, **meta})
    registry.save_model("m2_dts_band", m2, {"metrics": m2_metrics, **meta})
    registry.save_model("m3_buy_pass", m3, {"metrics": m3_metrics,
                        "acquisition_discount": discount, "target_margin": margin,
                        "threshold": m3.threshold, **meta})
    registry.save_model("mmr_lookup", mmr_lookup, {"proxy": False, **meta})
    registry.save_model("dts_benchmark", benchmark, {"makes": len(benchmark.as_dict())})

    (config.MODELS_DIR / "training_summary.json").write_text(
        json.dumps(summary, indent=2, default=str))
    (config.MODELS_DIR / "options.json").write_text(json.dumps(options))

    # Monitoring reference: a compact training-distribution sample for drift
    # (PSI) plus the full per-state MAE for fairness tracking. Consumed by
    # idss.monitoring at serve time; see the /monitor/summary endpoint.
    ref_n = min(len(test_df), 5000)
    ref_sample = test_df.sample(n=ref_n, random_state=42) if len(test_df) > ref_n else test_df
    monitoring_reference = {
        "built_at": pd.Timestamp.utcnow().isoformat(),
        "n": int(len(ref_sample)),
        "samples": {
            "mileage": ref_sample["mileage"].astype(float).round(1).tolist(),
            "year": ref_sample["year"].astype(float).tolist(),
            "condition": ref_sample["condition"].astype(float).tolist(),
        },
        "per_state_mae": per_state_mae,
    }
    (config.MODELS_DIR / "monitoring_reference.json").write_text(
        json.dumps(monitoring_reference, default=str))
    print(f"Done. Summary -> {config.MODELS_DIR / 'training_summary.json'}")


if __name__ == "__main__":
    main()
