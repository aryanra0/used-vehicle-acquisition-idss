"""Sanity tests for configuration and the days-to-sell band mapping."""

import sys
from pathlib import Path

# Make the src/ layout importable without installation.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from idss import config


def test_default_thresholds():
    assert config.DEFAULT_TARGET_MARGIN == 0.15
    assert config.DEFAULT_MIN_DOLLAR_PROFIT == 1000
    assert config.DEFAULT_RISK_TOLERANCE == 0.60


def test_days_to_band_boundaries():
    # Boundaries are inclusive on the lower band.
    assert config.days_to_band(45) == "Fast"
    assert config.days_to_band(60) == "Fast"
    assert config.days_to_band(61) == "Moderate"
    assert config.days_to_band(90) == "Moderate"
    assert config.days_to_band(91) == "Slow"
    assert config.days_to_band(120) == "Slow"
    assert config.days_to_band(121) == "Very slow"
    assert config.days_to_band(167) == "Very slow"
