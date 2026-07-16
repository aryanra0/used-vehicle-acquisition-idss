"""FastAPI backend for the Used Vehicle Acquisition IDSS.

Run from the src/ directory (or with PYTHONPATH=src):

    uvicorn idss.api.main:app --reload --port 8000
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .. import config
from ..data.live_pricing import get_provider
from ..models import registry
from ..monitoring import monitor
from ..service.evaluation import EvaluationService
from ..service.types import Assumptions, VehicleInput

app = FastAPI(title="Used Vehicle IDSS API", version="1.0.0")

# Prediction logging (audit trail) can be disabled via env for tests/CI.
_LOG_PREDICTIONS = os.environ.get("IDSS_LOG_PREDICTIONS", "1").lower() not in (
    "0", "false", "no", "off",
)


@lru_cache(maxsize=1)
def _model_versions() -> dict:
    """Artifact name + training timestamp for each model (from registry meta)."""
    out = {}
    for name in ("m1_resale", "m2_dts_band", "m3_buy_pass", "mmr_lookup", "dts_benchmark"):
        meta = registry.load_metadata(name)
        out[name] = {"saved_at": meta.get("saved_at"), "artifact": meta.get("artifact")}
    return out

app.add_middleware(
    CORSMiddleware,
    # Allow the local dev web app on any port (Next may fall back to 3001, etc.).
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def get_service() -> EvaluationService:
    return EvaluationService()


# request models
class AssumptionsIn(BaseModel):
    target_profit_margin: float = 0.15
    min_dollar_profit: float = 1000.0
    risk_tolerance: float = 0.60
    holding_cost_per_day: float = 20.0
    # None -> use the model's predicted days-to-sell; a number overrides it.
    holding_period_days: Optional[int] = None
    repair_estimate: float = 0.0
    acquisition_discount: float = 0.20


class VehicleIn(BaseModel):
    year: int
    make: str
    model: str
    odometer: float
    condition: float
    body: str = ""
    transmission: str = ""
    trim: str = ""
    color: str = ""
    interior: str = ""
    state: str = ""
    mmr: Optional[float] = None
    listing_price: Optional[float] = None


class EvaluateRequest(BaseModel):
    vehicle: VehicleIn
    assumptions: AssumptionsIn = Field(default_factory=AssumptionsIn)


# endpoints
@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/options")
def options() -> dict:
    path = config.MODELS_DIR / "options.json"
    if not path.exists():
        raise HTTPException(500, "options.json not found; run training / option build.")
    return json.loads(path.read_text())


@app.get("/metadata")
def metadata() -> dict:
    versions = _model_versions()
    return {
        "defaults": AssumptionsIn().model_dump(),
        "dts_bands": {"edges": config.DTS_BAND_EDGES, "labels": config.DTS_BAND_LABELS},
        "models": {
            name: registry.load_metadata(name).get("metrics", {})
            for name in ("m1_resale", "m2_dts_band", "m3_buy_pass")
        },
        "versions": versions,
        "trained_at": versions.get("m1_resale", {}).get("saved_at"),
        "live_pricing_enabled": get_provider() is not None,
    }


@app.post("/evaluate")
def evaluate(req: EvaluateRequest) -> dict:
    svc = get_service()
    vehicle = VehicleInput(**req.vehicle.model_dump())
    assumptions = Assumptions(**req.assumptions.model_dump())
    try:
        result = svc.evaluate(vehicle, assumptions)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"Evaluation failed: {exc}") from exc

    result_dict = result.to_dict()
    # Audit trail: log every served recommendation (with model versions) so it
    # can be reconstructed later and joined to realized outcomes. Never let a
    # logging failure break serving.
    if _LOG_PREDICTIONS:
        try:
            pid = monitor.log_prediction(
                req.vehicle.model_dump(), result_dict, _model_versions()
            )
            result_dict["prediction_id"] = pid
        except Exception:  # noqa: BLE001
            pass
    return result_dict


class OutcomeIn(BaseModel):
    """A realized outcome for a previously-evaluated vehicle (closes the loop)."""

    actual_sale_price: float
    prediction_id: Optional[str] = None
    actual_days_to_sell: Optional[float] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    notes: Optional[str] = None


@app.post("/outcomes")
def record_outcome(o: OutcomeIn) -> dict:
    """Record what a vehicle actually sold for, to track realized accuracy."""
    try:
        monitor.log_outcome(o.model_dump(exclude_none=True))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"Could not record outcome: {exc}") from exc
    return {"status": "recorded", "prediction_id": o.prediction_id}


@app.get("/monitor/summary")
def monitor_summary() -> dict:
    """Operational health: audit volume, realized accuracy, input drift, fairness."""
    preds = monitor.read_jsonl(monitor.LOG_PATH)
    return {
        "predictions_logged": len(preds),
        "realized_outcomes": monitor.reconcile_outcomes(),
        "drift": {f: monitor.drift_report(f) for f in ("mileage", "year", "condition")},
        "fairness_per_state": monitor.fairness_report(),
        "model_versions": _model_versions(),
    }


