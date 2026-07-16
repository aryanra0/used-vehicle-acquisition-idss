"""Tests for the monitoring module: drift (PSI), fairness gap, and the
prediction -> realized-outcome reconciliation loop."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np

from idss.monitoring import monitor


def test_psi_zero_for_identical_distribution():
    rng = np.random.default_rng(0)
    x = rng.normal(size=3000)
    assert monitor.population_stability_index(x, x) < 0.01


def test_psi_detects_large_shift():
    rng = np.random.default_rng(0)
    a = rng.normal(0, 1, size=3000)
    b = rng.normal(3, 1, size=3000)
    assert monitor.population_stability_index(a, b) > 0.25


def test_psi_label_buckets():
    assert monitor.psi_label(0.05) == "no significant drift"
    assert monitor.psi_label(0.15) == "moderate drift"
    assert monitor.psi_label(0.50) == "large drift"


def test_per_state_error_gap():
    gap = monitor.per_state_error_gap({"ca": 100.0, "tx": 300.0, "ny": 200.0})
    assert gap["best_state"] == "ca"
    assert gap["worst_state"] == "tx"
    assert gap["gap"] == 200.0


def test_per_state_error_gap_none_when_too_few():
    assert monitor.per_state_error_gap({"ca": 100.0}) is None


def test_log_and_reconcile_outcomes(tmp_path):
    pred_path = tmp_path / "predictions.jsonl"
    outcome_path = tmp_path / "outcomes.jsonl"

    pid = monitor.log_prediction(
        {"make": "kia", "model": "sorento"},
        {"predicted_resale_price": 10000.0},
        {"m1_resale": {"saved_at": "now"}},
        path=pred_path,
    )
    assert pid and isinstance(pid, str)

    monitor.log_outcome(
        {"prediction_id": pid, "actual_sale_price": 11000.0}, path=outcome_path
    )
    rec = monitor.reconcile_outcomes(pred_path=pred_path, outcome_path=outcome_path)
    assert rec["matched_to_predictions"] == 1
    assert rec["realized_resale_mae"] == 1000.0


def test_reconcile_handles_unmatched_outcomes(tmp_path):
    pred_path = tmp_path / "p.jsonl"
    outcome_path = tmp_path / "o.jsonl"
    monitor.log_prediction({"make": "x"}, {"predicted_resale_price": 5000.0}, {}, path=pred_path)
    # Outcome referencing a non-existent prediction id -> no match, no crash.
    monitor.log_outcome({"prediction_id": "missing", "actual_sale_price": 6000.0}, path=outcome_path)
    rec = monitor.reconcile_outcomes(pred_path=pred_path, outcome_path=outcome_path)
    assert rec["outcomes_logged"] == 1
    assert rec["matched_to_predictions"] == 0
    assert rec["realized_resale_mae"] is None
