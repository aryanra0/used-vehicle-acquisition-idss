"""Evaluation service: orchestrates benchmarks, models, and the decision engine.

Per-vehicle model outputs (resale, band, days benchmark, confidence, MMR) are
cached so that changing an assumption only re-runs the cheap decision engine.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Optional

import pandas as pd

from .. import config
from ..data.live_pricing import get_provider
from ..data.mmr_lookup import price_vs_mmr_delta
from ..decision import engine
from ..features.engineering import REFERENCE_YEAR
from ..models import registry
from . import confidence as conf
from .types import (
    Assumptions,
    EvaluationResult,
    RiskSummary,
    VehicleInput,
)

_DEMAND_BY_BAND = {
    "Fast": "High demand",
    "Moderate": "Steady demand",
    "Slow": "Soft demand",
    "Very slow": "Weak demand",
}


class EvaluationService:
    """Loads the trained models once and evaluates vehicles."""

    # Training data covers model years up to this year; beyond it is out of coverage.
    TRAINING_YEAR_MAX = 2015

    def __init__(self, models_dir=None):
        self.m1 = registry.load_model("m1_resale", models_dir)
        self.m2 = registry.load_model("m2_dts_band", models_dir)
        self.m3 = registry.load_model("m3_buy_pass", models_dir)
        self.mmr_lookup = registry.load_model("mmr_lookup", models_dir)
        self.benchmark = registry.load_model("dts_benchmark", models_dir)
        self.provider = get_provider()  # live pricing if MARKETCHECK_API_KEY is set
        self._year_range = self._load_year_range(models_dir)
        self._cache: dict[tuple, dict] = {}

    @staticmethod
    def _load_year_range(models_dir) -> tuple[Optional[int], Optional[int]]:
        """Training model-year range (for OOD checks), read from options.json."""
        try:
            base = Path(models_dir) if models_dir else config.MODELS_DIR
            opts = json.loads((base / "options.json").read_text())
            return opts.get("year_min"), opts.get("year_max")
        except (OSError, json.JSONDecodeError):
            return (None, None)

    # per-vehicle model predictions (cached)
    @staticmethod
    def _cache_key(v: VehicleInput) -> tuple:
        return (
            int(v.year), v.make.lower(), v.model.lower(), round(float(v.odometer)),
            round(float(v.condition), 1), v.body.lower(), v.transmission.lower(),
            v.state.lower(), v.color.lower(), None if v.mmr is None else round(float(v.mmr)),
        )

    def _vehicle_frame(self, v: VehicleInput, mmr: float) -> pd.DataFrame:
        # Schema expected by build_features (single-source car_prices features).
        return pd.DataFrame(
            [{
                "year": v.year,
                "make": v.make,
                "model": v.model,
                "body": v.body or "unknown",
                "transmission": v.transmission or "unknown",
                "state": v.state or "unknown",
                "color": v.color or "unknown",
                "mileage": v.odometer,
                "condition": v.condition,
                "market_value": mmr,
            }]
        )

    def predict_vehicle(self, v: VehicleInput) -> dict:
        key = self._cache_key(v)
        if key in self._cache:
            return self._cache[key]

        # 1) Try a live current-market price first (if a provider is configured).
        live = None
        if self.provider is not None:
            try:
                live = self.provider.market_value(
                    v.make, v.model, v.year, mileage=v.odometer, state=v.state or None
                )
            except Exception:
                live = None

        # 2) Resolve the market-value benchmark (MMR): user-provided > live > lookup.
        match_level = "provided"
        mmr = v.mmr
        mmr_sample_size: Optional[int] = None
        if mmr is None and live is not None:
            mmr, match_level = live.market_value, "live"
            mmr_sample_size = live.sample_size
        if mmr is None:
            mmr, match_level, mmr_sample_size = self.mmr_lookup.lookup_detailed(
                v.make, v.model, v.year
            )
        mmr_val = float(mmr) if mmr is not None else 0.0

        # 3) Resale value: the live market value when available, else the ML model.
        frame = self._vehicle_frame(v, mmr_val)
        band = str(self.m2.predict(frame)[0])
        try:
            band_proba = float(self.m2.predict_confidence(frame)[0])
        except Exception:
            band_proba = None
        band_from_live = False
        benchmark_days = float(self.benchmark.days_for(v.make))
        coverage_warning = None
        resale_low = resale_high = None
        explanations = None

        if live is not None:
            resale = live.market_value
            price_source = "live"
            if live.days_on_market is not None:
                benchmark_days = live.days_on_market
                band = config.days_to_band(benchmark_days)
                band_from_live = True
        else:
            resale = float(self.m1.predict(frame)[0])
            price_source = "model"
            if v.year > self.TRAINING_YEAR_MAX:
                coverage_warning = (
                    f"{v.year} is beyond the model's training data (through "
                    f"{self.TRAINING_YEAR_MAX}). This estimate is unreliable; "
                    "connect a live price feed for current-year vehicles."
                )
            elif match_level == "global":
                coverage_warning = (
                    "No comparable vehicles for this make/model in the training "
                    "data; estimate is low-confidence."
                )
            # ~80% prediction interval + per-instance explanations (model path).
            try:
                lo_arr, hi_arr = self.m1.predict_interval(frame)
                lo_v, hi_v = float(lo_arr[0]), float(hi_arr[0])
                if pd.notna(lo_v) and pd.notna(hi_v):
                    resale_low, resale_high = lo_v, hi_v
            except Exception:
                pass
            try:
                explanations = self.m1.explain_contributions(frame)
            except Exception:
                explanations = None

        confidence = float(self.m3.predict_proba(frame)[0])

        out = {
            "predicted_resale": resale,
            "days_band": band,
            "band_proba": band_proba,
            "band_from_live": band_from_live,
            "benchmark_days": benchmark_days,
            "confidence": confidence,
            "mmr": mmr if mmr is not None else None,
            "mmr_match_level": match_level,
            "mmr_sample_size": mmr_sample_size,
            "price_source": price_source,
            "coverage_warning": coverage_warning,
            "live_sample_size": live.sample_size if live else None,
            "resale_low": resale_low,
            "resale_high": resale_high,
            "explanations": explanations,
        }
        self._cache[key] = out
        return out

    # full evaluation
    def evaluate(self, v: VehicleInput, assumptions: Optional[Assumptions] = None) -> EvaluationResult:
        a = assumptions or Assumptions()
        pred = self.predict_vehicle(v)
        model_resale = pred["predicted_resale"]
        band = pred["days_band"]
        days = pred["benchmark_days"]
        profit_p = pred["confidence"]  # M3 P(good buy)
        mmr = pred["mmr"]
        match_level = pred["mmr_match_level"]
        price_source = pred["price_source"]

        notes: list[str] = []
        if pred.get("coverage_warning"):
            notes.append(pred["coverage_warning"])
        if price_source == "live":
            n = pred.get("live_sample_size")
            notes.append(
                "Current market value from live listings"
                + (f" ({n} comparable listings)." if n else ".")
            )
        elif match_level not in ("provided", "make/model/year", "live"):
            notes.append(f"Market value estimated at the '{match_level}' level.")

        # How much to trust the raw model resale (few comparables / big
        # divergence from the market benchmark all lower this).
        resale_conf = conf.resale_confidence(
            price_source=price_source,
            match_level=match_level,
            resale=model_resale,
            mmr=mmr,
            coverage_warning=pred.get("coverage_warning"),
        )

        # Reconcile the resale estimate toward the market benchmark in proportion
        # to how much we trust the model. A well-supported prediction is kept
        # almost as-is; a low-confidence one (rare/exotic, or wildly divergent)
        # is pulled toward MMR instead of being trusted outright. This is a
        # confidence-weighted shrink, NOT a hard cap: high-confidence cars keep
        # any legitimate premium over MMR.
        resale = model_resale
        if price_source == "model" and mmr is not None and float(mmr) > 0:
            w = resale_conf.score
            resale = w * float(model_resale) + (1.0 - w) * float(mmr)
            if abs(resale - model_resale) / max(abs(model_resale), 1.0) >= 0.05:
                notes.append(
                    f"Raw model resale ${model_resale:,.0f} was {resale_conf.level.lower()} "
                    f"confidence; reconciled toward the market benchmark to ${resale:,.0f}."
                )

        # Prediction interval around the reported resale (widen to include the
        # reconciled point so the range always contains the shown estimate).
        resale_low = pred.get("resale_low")
        resale_high = pred.get("resale_high")
        if resale_low is not None and resale_high is not None:
            resale_low = min(float(resale_low), resale)
            resale_high = max(float(resale_high), resale)

        # Purchase price under consideration: listing price if given, else the
        # typical wholesale acquisition price (a discount below market value).
        if v.listing_price is not None:
            purchase_price = float(v.listing_price)
        elif mmr is not None:
            purchase_price = float(mmr) * (1.0 - a.acquisition_discount)
            notes.append(
                f"No listing price supplied; evaluated at a {a.acquisition_discount:.0%} "
                "wholesale discount below market value (MMR)."
            )
        else:
            purchase_price = resale
            notes.append("No listing price or market value; evaluated at predicted resale.")

        fin = engine.financials(purchase_price, resale, a, days_to_sell=days)
        max_price = engine.max_purchase_price(resale, a, days_to_sell=days)
        delta = price_vs_mmr_delta(purchase_price, mmr)

        # Transparency: make it explicit when the user's holding-period override
        # is what drove the holding cost (rather than the model's estimate).
        if a.holding_period_days is not None and abs(float(a.holding_period_days) - float(days)) >= 1.0:
            notes.append(
                f"Holding cost uses your {int(a.holding_period_days)}-day holding period "
                f"(model predicts ~{days:.0f} days to sell)."
            )

        # Data-quality guards: advisory warnings (abnormally low price, implausible
        # ROI, etc.). They are surfaced prominently but do NOT change the Buy/Pass
        # verdict. The recommendation is made on face-value economics.
        flags = conf.collect_flags(v, resale=resale, mmr=mmr, delta=delta, roi=fin.roi)
        # Out-of-distribution guards (unknown make/model, year below training range).
        ymin, ymax = self._year_range
        flags.extend(conf.ood_flags(v, match_level=match_level, year_min=ymin, year_max=ymax))

        # Confidence = trust in the underlying valuation: the weakest link of the
        # profit model and the resale estimate. Not affected by the price flags.
        confidence = min(profit_p, resale_conf.score)

        decision, reasons = engine.buy_or_pass(fin, confidence, a)
        notes.extend(reasons)

        # What to actually pay vs. the (auction-style) max-price ceiling.
        price_guidance = self._price_guidance(
            v.listing_price, max_price, a, decision=decision
        )
        if price_guidance:
            notes.append(price_guidance)

        market_value_conf = (
            None
            if mmr is None
            else conf.market_value_confidence(match_level, pred.get("mmr_sample_size"))
        )
        days_band_conf = conf.days_band_confidence(
            band_proba=pred.get("band_proba"), from_live_dom=pred.get("band_from_live", False)
        )
        buy_pass_conf = conf.buy_pass_confidence(profit_p, resale_conf.score)

        risk = RiskSummary(
            days_to_sell_band=band,
            days_to_sell_benchmark=round(days, 1),
            market_demand=_DEMAND_BY_BAND.get(band, "Unknown"),
            risk_level=self._risk_level(band, confidence, a.risk_tolerance),
        )

        return EvaluationResult(
            recommendation=decision,
            confidence=round(confidence, 3),
            predicted_resale_price=round(resale, 2),
            predicted_resale_low=None if resale_low is None else round(resale_low, 2),
            predicted_resale_high=None if resale_high is None else round(resale_high, 2),
            days_to_sell_band=band,
            expected_gross_profit=fin.net_profit,
            roi=fin.roi,
            max_purchase_price=round(max_price, 2),
            market_value_mmr=None if mmr is None else round(float(mmr), 2),
            price_vs_mmr_delta=None if delta is None else round(delta, 4),
            price_source=price_source,
            coverage_warning=pred.get("coverage_warning"),
            resale_confidence=resale_conf,
            market_value_confidence=market_value_conf,
            days_band_confidence=days_band_conf,
            buy_pass_confidence=buy_pass_conf,
            data_quality_flags=[asdict(f) for f in flags],
            price_guidance=price_guidance,
            financial_summary=fin,
            risk_summary=risk,
            top_factors=self._top_factors(v, pred, delta),
            notes=notes,
        )

    @staticmethod
    def _price_guidance(
        listing_price,
        max_price: float,
        a: Assumptions,
        decision: str = engine.BUY,
    ) -> Optional[str]:
        """Explain what to pay vs. the max-price *ceiling* (a walk-away limit).

        The message follows the face-value verdict. Abnormal-price warnings are
        shown separately as data-quality flags, so this never has to hedge a Buy.
        """
        margin = f"{a.target_profit_margin:.0%}"
        if listing_price is None:
            return (
                f"No listing price: ${max_price:,.0f} is the most you should bid at "
                f"auction to still clear a {margin} margin."
            )
        listing = float(listing_price)

        # Listing above the ceiling: negotiate down or pass.
        if listing > max_price:
            return (
                f"The ${listing:,.0f} listing is above your ${max_price:,.0f} ceiling for "
                f"a {margin} margin. Negotiate to ${max_price:,.0f} or below, or pass."
            )

        # Listing within the ceiling but the deal still didn't clear the rules.
        if decision != engine.BUY:
            return (
                f"Even at the ${listing:,.0f} listing this doesn't clear your criteria "
                "(see the reasons above), so hold off."
            )

        # A genuine buy: pay the listing, not the ceiling.
        head = max_price - listing
        return (
            f"Buy at the ${listing:,.0f} listing (or negotiate lower), never above it. "
            f"${max_price:,.0f} is only your walk-away ceiling for a {margin} margin, not a "
            f"target; the listing sits ${head:,.0f} under it."
        )

    @staticmethod
    def _risk_level(band: str, confidence: float, risk_tolerance: float) -> str:
        if band == "Very slow" or confidence < 0.40:
            return "High"
        if band in ("Fast", "Moderate") and confidence >= risk_tolerance:
            return "Low"
        return "Medium"

    _FACTOR_LABELS = {
        "market_value": "Market value (MMR)",
        "mileage": "Mileage",
        "condition": "Condition",
        "year": "Vehicle age",
    }

    @classmethod
    def _feature_value_str(cls, feat: str, v: VehicleInput, pred: dict) -> str:
        if feat == "mileage":
            return f"{float(v.odometer):,.0f} mi"
        if feat == "year":
            age = max(0, REFERENCE_YEAR - int(v.year))
            return f"{age} yr"
        if feat == "condition":
            # Model's native 1-49 grade -> friendlier 0-100 UI scale.
            return f"{max(0, min(100, round((float(v.condition) - 1) / 48 * 100)))}/100"
        if feat == "market_value":
            return f"${pred['mmr']:,.0f}" if pred.get("mmr") is not None else "-"
        return str(getattr(v, feat, "-"))

    @classmethod
    def _top_factors(cls, v: VehicleInput, pred: dict, delta: Optional[float]) -> list:
        """Explain the resale estimate. When per-instance model contributions
        are available, show how much each feature moves the price vs a typical
        car (a real explanation); otherwise fall back to echoing the inputs.
        """
        explanations = pred.get("explanations")
        factors: list = []
        if explanations:
            for e in explanations:
                feat = e["feature"]
                c = float(e["contribution"])
                sign = "+" if c >= 0 else "-"
                factors.append({
                    "factor": cls._FACTOR_LABELS.get(feat, feat),
                    "value": cls._feature_value_str(feat, v, pred),
                    "impact": f"{sign}${abs(c):,.0f}",
                })
        else:
            age = max(0, REFERENCE_YEAR - int(v.year))
            cond_100 = max(0, min(100, round((float(v.condition) - 1) / 48 * 100)))
            factors = [
                {"factor": "Mileage", "value": f"{float(v.odometer):,.0f} mi"},
                {"factor": "Vehicle age", "value": f"{age} yr"},
                {"factor": "Condition", "value": f"{cond_100}/100"},
            ]
            if pred.get("mmr") is not None:
                factors.append({"factor": "Market value (MMR)", "value": f"${pred['mmr']:,.0f}"})

        # Contextual (non-attributed) cards.
        factors.append({"factor": "Days-to-sell band", "value": pred["days_band"]})
        if delta is not None:
            factors.append({"factor": "Price vs market", "value": f"{delta:+.0%}"})
        return factors
