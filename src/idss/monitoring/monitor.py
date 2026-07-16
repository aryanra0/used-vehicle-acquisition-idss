"""Lightweight monitoring: prediction logging and drift / fairness checks.

Prediction logging appends each served evaluation (with model versions) to a
JSONL file so realized outcomes can later be joined for accuracy tracking.
Drift and per-state fairness checks compare a recent batch against training
reference statistics.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from .. import config

LOG_DIR = config.PROJECT_ROOT / "logs"
LOG_PATH = LOG_DIR / "predictions.jsonl"
OUTCOME_PATH = LOG_DIR / "outcomes.jsonl"


def log_prediction(vehicle: dict, result: dict, model_versions: dict,
                   path: Optional[Path] = None) -> str:
    """Append one served prediction to the JSONL audit log.

    Returns a unique prediction id so a realized outcome can be joined back to
    it later (see log_outcome / reconcile_outcomes).
    """
    path = Path(path) if path else LOG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    pid = uuid.uuid4().hex
    record = {
        "id": pid,
        "ts": datetime.now(timezone.utc).isoformat(),
        "vehicle": vehicle,
        "result": result,
        "model_versions": model_versions,
    }
    with path.open("a") as f:
        f.write(json.dumps(record, default=str) + "\n")
    return pid


def log_outcome(outcome: dict, path: Optional[Path] = None) -> None:
    """Append a realized outcome (actual sale price / days-to-sell) to the log.

    `outcome` should carry a prediction_id (to join back to a served prediction)
    and/or enough vehicle identifiers, plus the actuals.
    """
    path = Path(path) if path else OUTCOME_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"ts": datetime.now(timezone.utc).isoformat(), **outcome}
    with path.open("a") as f:
        f.write(json.dumps(record, default=str) + "\n")


def read_jsonl(path: Path, limit: Optional[int] = None) -> list[dict]:
    """Read a JSONL log into a list of dicts (most recent last)."""
    path = Path(path)
    if not path.exists():
        return []
    rows: list[dict] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows[-limit:] if limit else rows


def reconcile_outcomes(
    pred_path: Optional[Path] = None, outcome_path: Optional[Path] = None
) -> dict:
    """Join realized outcomes to their predictions and score realized accuracy.

    This closes the loop: it measures how the predicted resale price compared to
    what the vehicle actually sold for. Returns realized MAE/MAPE and counts.
    """
    preds = {r.get("id"): r for r in read_jsonl(pred_path or LOG_PATH) if r.get("id")}
    outcomes = read_jsonl(outcome_path or OUTCOME_PATH)

    errs: list[float] = []
    pct: list[float] = []
    matched = 0
    for o in outcomes:
        actual = o.get("actual_sale_price")
        pred = preds.get(o.get("prediction_id"))
        if pred is None or actual in (None, 0):
            continue
        predicted = (pred.get("result") or {}).get("predicted_resale_price")
        if predicted is None:
            continue
        matched += 1
        errs.append(abs(float(predicted) - float(actual)))
        pct.append(abs(float(predicted) - float(actual)) / float(actual))

    return {
        "outcomes_logged": len(outcomes),
        "matched_to_predictions": matched,
        "realized_resale_mae": float(np.mean(errs)) if errs else None,
        "realized_resale_mape": float(np.mean(pct)) if pct else None,
    }


def psi_label(psi: float) -> str:
    """Human label for a PSI value."""
    if psi < 0.1:
        return "no significant drift"
    if psi < 0.25:
        return "moderate drift"
    return "large drift"


def population_stability_index(expected: np.ndarray, actual: np.ndarray,
                               bins: int = 10) -> float:
    """PSI between a reference (expected) and a new (actual) numeric sample.
    PSI < 0.1 = no significant shift; 0.1-0.25 = moderate; > 0.25 = large shift.
    """
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)
    quantiles = np.linspace(0, 100, bins + 1)
    edges = np.unique(np.percentile(expected, quantiles))
    if len(edges) < 3:
        return 0.0
    e_perc = np.histogram(expected, bins=edges)[0] / max(len(expected), 1)
    a_perc = np.histogram(actual, bins=edges)[0] / max(len(actual), 1)
    eps = 1e-6
    e_perc = np.clip(e_perc, eps, None)
    a_perc = np.clip(a_perc, eps, None)
    return float(np.sum((a_perc - e_perc) * np.log(a_perc / e_perc)))


def per_state_error_gap(errors_by_state: dict, min_states: int = 2) -> Optional[dict]:
    """Given {state: mae}, report the best/worst states and the gap between them."""
    if len(errors_by_state) < min_states:
        return None
    items = sorted(errors_by_state.items(), key=lambda kv: kv[1])
    best_state, best = items[0]
    worst_state, worst = items[-1]
    return {
        "best_state": best_state, "best_mae": best,
        "worst_state": worst_state, "worst_mae": worst,
        "gap": worst - best,
        "gap_ratio": (worst / best) if best > 0 else float("inf"),
    }


# training reference (written at train time)
REFERENCE_PATH = config.MODELS_DIR / "monitoring_reference.json"

# Logged vehicle payload keys differ from feature names (odometer == mileage).
_FEATURE_TO_VEHICLE_KEY = {"mileage": "odometer", "year": "year", "condition": "condition"}


def load_reference(path: Optional[Path] = None) -> Optional[dict]:
    """Load the training reference sample written by train.py, if present."""
    path = Path(path) if path else REFERENCE_PATH
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def drift_report(feature: str = "mileage", reference: Optional[dict] = None,
                 pred_path: Optional[Path] = None) -> Optional[dict]:
    """PSI drift for one logged input feature vs the training reference sample.

    Compares the distribution of recently-served inputs against the training
    distribution so silent input drift (e.g. newer, higher-mileage cars) surfaces.
    """
    reference = reference or load_reference()
    if not reference:
        return None
    ref_values = (reference.get("samples") or {}).get(feature)
    if not ref_values:
        return None
    veh_key = _FEATURE_TO_VEHICLE_KEY.get(feature, feature)
    actual: list[float] = []
    for r in read_jsonl(pred_path or LOG_PATH):
        val = (r.get("vehicle") or {}).get(veh_key)
        if isinstance(val, (int, float)):
            actual.append(float(val))
    if len(actual) < 20:
        return {"feature": feature, "n_recent": len(actual), "psi": None,
                "label": "insufficient serving data (need >= 20 predictions)"}
    psi = population_stability_index(np.asarray(ref_values, float), np.asarray(actual, float))
    return {"feature": feature, "n_recent": len(actual), "psi": round(psi, 4),
            "label": psi_label(psi)}


def fairness_report(reference: Optional[dict] = None) -> Optional[dict]:
    """Per-state MAE gap from the training reference (geographic fairness)."""
    reference = reference or load_reference()
    if not reference:
        return None
    return per_state_error_gap(reference.get("per_state_mae") or {})
