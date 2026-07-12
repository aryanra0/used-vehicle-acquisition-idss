"""Tests for the decision engine: max price, financials, and buy/pass."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from idss.decision import engine
from idss.service.types import Assumptions


def test_max_purchase_price_worked_example():
    # PRD worked example: resale $12,000, repairs $800, 45 days @ $20/day,
    # target margin 15% -> max purchase price $8,500.
    a = Assumptions(
        target_profit_margin=0.15,
        holding_cost_per_day=20.0,
        holding_period_days=45,
        repair_estimate=800.0,
    )
    mpp = engine.max_purchase_price(12000.0, a)
    assert round(mpp, 2) == 8500.0


def test_holding_cost_defaults_to_predicted_days():
    # No user override (None) -> use the model's predicted days-to-sell.
    a = Assumptions(holding_cost_per_day=20.0, holding_period_days=None)
    assert engine.total_holding_cost(a, days_to_sell=60) == 1200.0
    # No override and no predicted days -> fall back to the default horizon.
    assert engine.total_holding_cost(a) == engine.DEFAULT_HOLDING_DAYS * 20.0


def test_user_holding_period_overrides_predicted_days():
    # An explicit user holding period wins over the model's predicted days,
    # so the "holding period" control is load-bearing.
    a = Assumptions(holding_cost_per_day=20.0, holding_period_days=30)
    assert engine.total_holding_cost(a, days_to_sell=60) == 600.0
    assert engine.total_holding_cost(a) == 600.0


def test_financials_profit_and_roi():
    a = Assumptions(holding_cost_per_day=20.0, holding_period_days=45, repair_estimate=800.0)
    fin = engine.financials(purchase_price=8000.0, resale_price=12000.0, assumptions=a)
    # net = 12000 - 8000 - 800 - 900 = 2300 ; invested = 8800 ; roi = 0.2614
    assert fin.net_profit == 2300.0
    assert fin.roi == round(2300.0 / 8800.0, 4)


def test_buy_when_all_thresholds_met():
    a = Assumptions(target_profit_margin=0.15, min_dollar_profit=1000, risk_tolerance=0.60,
                    holding_cost_per_day=20.0, holding_period_days=45, repair_estimate=800.0)
    fin = engine.financials(8000.0, 12000.0, a)
    decision, _ = engine.buy_or_pass(fin, confidence=0.75, assumptions=a)
    assert decision == engine.BUY


def test_pass_when_confidence_too_low():
    a = Assumptions(risk_tolerance=0.60, repair_estimate=800.0,
                    holding_cost_per_day=20.0, holding_period_days=45)
    fin = engine.financials(8000.0, 12000.0, a)
    decision, reasons = engine.buy_or_pass(fin, confidence=0.40, assumptions=a)
    assert decision == engine.PASS
    assert any("Confidence" in r for r in reasons)


def test_pass_when_overpaying():
    a = Assumptions(target_profit_margin=0.15, min_dollar_profit=1000,
                    holding_cost_per_day=20.0, holding_period_days=45, repair_estimate=800.0)
    # Paying 11,500 for a car that resells at 12,000 -> thin/negative profit.
    fin = engine.financials(11500.0, 12000.0, a)
    decision, _ = engine.buy_or_pass(fin, confidence=0.9, assumptions=a)
    assert decision == engine.PASS
