"""Rule-based decision engine: Buy/Pass, maximum purchase price, and financials.

Pure functions of their inputs (no I/O, no model calls) so results are
reproducible and cheap to recompute when a user changes an assumption.

Implements the decision logic from the PRD (Section 6.8):

    Buy only if ALL hold, else Pass:
      1. expected ROI            >= target profit margin
      2. expected gross profit   >= minimum dollar profit
      3. model confidence        >= risk tolerance

    MaxPurchasePrice = resale - repairs - holding_cost - required_profit
      holding_cost   = holding_cost_per_day * holding_days
      required_profit = target_margin * resale

    holding_days is the model's predicted days-to-sell by default, but a user
    who supplies an explicit holding period (assumptions.holding_period_days)
    overrides that estimate.
"""

from __future__ import annotations

from ..service.types import Assumptions, FinancialSummary

BUY = "Buy"
PASS = "Pass"

# Fallback horizon when neither a user override nor a predicted days-to-sell
# is available (keeps the engine usable in isolation, e.g. unit tests).
DEFAULT_HOLDING_DAYS = 45


def total_holding_cost(assumptions: Assumptions, days_to_sell: float | None = None) -> float:
    """Holding cost over the expected time in inventory.

    Priority for the number of days:
      1. an explicit user holding period (assumptions.holding_period_days), else
      2. the model's predicted days_to_sell passed by the caller, else
      3. a default horizon.

    This makes the "holding period" control load-bearing: when the user sets it,
    it overrides the model estimate; when left blank (None) the prediction is used.
    """
    if assumptions.holding_period_days is not None:
        days = float(assumptions.holding_period_days)
    elif days_to_sell is not None:
        days = float(days_to_sell)
    else:
        days = float(DEFAULT_HOLDING_DAYS)
    return assumptions.holding_cost_per_day * days


def required_profit(resale_price: float, target_margin: float) -> float:
    """Absolute profit the deal must clear, expressed as a fraction of resale."""
    return target_margin * resale_price


def max_purchase_price(
    resale_price: float,
    assumptions: Assumptions,
    days_to_sell: float | None = None,
) -> float:
    """Highest acquisition price that still meets the target margin."""
    holding = total_holding_cost(assumptions, days_to_sell)
    req = required_profit(resale_price, assumptions.target_profit_margin)
    return resale_price - assumptions.repair_estimate - holding - req


def financials(
    purchase_price: float,
    resale_price: float,
    assumptions: Assumptions,
    days_to_sell: float | None = None,
) -> FinancialSummary:
    """Compute gross profit and ROI at a given purchase price."""
    holding = total_holding_cost(assumptions, days_to_sell)
    invested = purchase_price + assumptions.repair_estimate
    net_profit = resale_price - purchase_price - assumptions.repair_estimate - holding
    roi = (net_profit / invested) if invested > 0 else 0.0
    return FinancialSummary(
        purchase_price=round(purchase_price, 2),
        estimated_repairs=round(assumptions.repair_estimate, 2),
        predicted_resale_price=round(resale_price, 2),
        total_holding_cost=round(holding, 2),
        net_profit=round(net_profit, 2),
        roi=round(roi, 4),
    )


def buy_or_pass(
    fin: FinancialSummary,
    confidence: float,
    assumptions: Assumptions,
) -> tuple[str, list[str]]:
    """Apply the three-part Buy rule. Returns (decision, reasons)."""
    reasons: list[str] = []

    roi_ok = fin.roi >= assumptions.target_profit_margin
    profit_ok = fin.net_profit >= assumptions.min_dollar_profit
    conf_ok = confidence >= assumptions.risk_tolerance

    if not roi_ok:
        reasons.append(
            f"ROI {fin.roi:.1%} below target {assumptions.target_profit_margin:.1%}"
        )
    if not profit_ok:
        reasons.append(
            f"Gross profit ${fin.net_profit:,.0f} below minimum "
            f"${assumptions.min_dollar_profit:,.0f}"
        )
    if not conf_ok:
        reasons.append(
            f"Confidence {confidence:.2f} below risk tolerance "
            f"{assumptions.risk_tolerance:.2f}"
        )

    decision = BUY if (roi_ok and profit_ok and conf_ok) else PASS
    if decision == BUY:
        reasons.append("Meets ROI, profit, and confidence thresholds")
    return decision, reasons
