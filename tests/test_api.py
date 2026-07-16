"""API contract / integration tests (skip if trained models are absent).

Verifies the trust-critical serving path: prediction intervals, explanations,
the load-bearing holding-period control, and the monitoring endpoints.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# Do not write audit logs during tests.
os.environ["IDSS_LOG_PREDICTIONS"] = "0"

from idss.models import registry  # noqa: E402

pytestmark = pytest.mark.skipif(
    not registry.model_exists("m1_resale"),
    reason="trained models not present; run `python -m idss.train` first",
)

from fastapi.testclient import TestClient  # noqa: E402

from idss.api.main import app  # noqa: E402

client = TestClient(app)

_VEHICLE = {
    "year": 2013, "make": "kia", "model": "sorento", "odometer": 40000,
    "condition": 30, "body": "suv", "transmission": "automatic",
    "state": "ca", "color": "white", "listing_price": 12000,
}


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_metadata_exposes_versions_and_pricing_mode():
    md = client.get("/metadata").json()
    assert "trained_at" in md
    assert "live_pricing_enabled" in md
    assert "versions" in md and "m1_resale" in md["versions"]
    # M2 is honestly labelled as a benchmark lookup.
    assert md["models"]["m2_dts_band"].get("label_is_deterministic_from_make") is True


def test_evaluate_returns_interval_and_explanations():
    r = client.post("/evaluate", json={"vehicle": _VEHICLE,
                                       "assumptions": {"target_profit_margin": 0.15}})
    assert r.status_code == 200
    d = r.json()
    assert d["recommendation"] in ("Buy", "Pass")
    assert d["predicted_resale_low"] is not None
    assert d["predicted_resale_high"] is not None
    assert d["predicted_resale_low"] <= d["predicted_resale_price"] <= d["predicted_resale_high"]
    # Explanations carry a signed dollar impact.
    assert any("impact" in f for f in d["top_factors"])


def test_holding_period_control_is_load_bearing():
    """The holding-period control must actually change the holding cost."""
    def holding_cost(days):
        r = client.post("/evaluate", json={
            "vehicle": _VEHICLE,
            "assumptions": {"holding_cost_per_day": 50, "holding_period_days": days},
        })
        return r.json()["financial_summary"]["total_holding_cost"]

    assert holding_cost(10) == 500.0
    assert holding_cost(120) == 6000.0


def test_unknown_make_raises_ood_flag():
    r = client.post("/evaluate", json={"vehicle": {
        "year": 2013, "make": "zzzunknownmake", "model": "zzz",
        "odometer": 40000, "condition": 30}})
    d = r.json()
    assert any("not found in the training data" in f["message"] for f in d["data_quality_flags"])


def test_outcomes_and_monitor_summary(monkeypatch, tmp_path):
    from idss.monitoring import monitor
    monkeypatch.setattr(monitor, "OUTCOME_PATH", tmp_path / "outcomes.jsonl")

    ro = client.post("/outcomes", json={"actual_sale_price": 12345})
    assert ro.status_code == 200

    ms = client.get("/monitor/summary")
    assert ms.status_code == 200
    body = ms.json()
    assert "drift" in body and "fairness_per_state" in body and "realized_outcomes" in body
