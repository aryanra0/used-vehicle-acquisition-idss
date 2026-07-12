"""Shared data types for the IDSS evaluation pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class VehicleInput:
    """A candidate vehicle to evaluate. Mirrors the primary dataset schema."""

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
    # MMR (market-value benchmark). Optional: looked up if not supplied.
    mmr: Optional[float] = None
    # The price currently being considered / asked for the vehicle.
    listing_price: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Assumptions:
    """User-adjustable business assumptions for one evaluation."""

    target_profit_margin: float = 0.15
    min_dollar_profit: float = 1000.0
    risk_tolerance: float = 0.60
    holding_cost_per_day: float = 20.0
    # None -> use the model's predicted days-to-sell; a number overrides it.
    holding_period_days: Optional[int] = None
    repair_estimate: float = 0.0
    # Typical wholesale discount below market value at which the dealer acquires.
    acquisition_discount: float = 0.20


@dataclass
class FinancialSummary:
    purchase_price: float
    estimated_repairs: float
    predicted_resale_price: float
    total_holding_cost: float
    net_profit: float
    roi: float


@dataclass
class RiskSummary:
    days_to_sell_band: str
    days_to_sell_benchmark: Optional[float]
    market_demand: str
    risk_level: str


@dataclass
class PredictionConfidence:
    """How much to trust a single model output.

    score : reliability in [0, 1]
    level : bucketed label ("High" | "Medium" | "Low" | "Very low")
    basis : short, human-readable reason for the score
    """

    score: float
    level: str
    basis: str = ""


@dataclass
class DataQualityFlag:
    """A signal that an input or output does not add up.

    severity : "alert" (likely bad data / too-good-to-be-true) | "warn" | "info"
    """

    severity: str
    message: str


@dataclass
class EvaluationResult:
    recommendation: str  # "Buy" | "Pass"
    confidence: float
    predicted_resale_price: float
    days_to_sell_band: str
    expected_gross_profit: float
    roi: float
    max_purchase_price: float
    market_value_mmr: Optional[float]
    price_vs_mmr_delta: Optional[float]
    financial_summary: FinancialSummary
    risk_summary: RiskSummary
    # ~80% prediction interval around the resale estimate (model path only).
    predicted_resale_low: Optional[float] = None
    predicted_resale_high: Optional[float] = None
    # "live" when a current-market price feed was used, else "model".
    price_source: str = "model"
    # Set when the vehicle is outside the training data's coverage (e.g., a
    # future model year) and no live price was available -> low reliability.
    coverage_warning: Optional[str] = None
    # Per-prediction reliability scores (each model output gets its own).
    resale_confidence: Optional[PredictionConfidence] = None
    market_value_confidence: Optional[PredictionConfidence] = None
    days_band_confidence: Optional[PredictionConfidence] = None
    buy_pass_confidence: Optional[PredictionConfidence] = None
    # Inputs/outputs that don't add up (implausible discount, divergence, etc.).
    data_quality_flags: list = field(default_factory=list)
    # Plain-language guidance on what to actually pay vs. the max-price ceiling.
    price_guidance: Optional[str] = None
    top_factors: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
