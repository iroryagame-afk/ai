#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "backtest_drawdown_rebound.py"
SPEC = importlib.util.spec_from_file_location("drawdown_model", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_recovery_ratio_and_ongoing_status() -> None:
    dates = ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"]
    prices = [100.0, 80.0, 90.0, 92.0]
    pivots = [
        MODULE.Pivot("peak", 0, dates[0], prices[0]),
        MODULE.Pivot("trough", 1, dates[1], prices[1]),
    ]
    item = MODULE.build_episodes(pivots, dates, prices, prices)[0]
    assert round(item["drawdown_pct"], 6) == -0.2
    assert round(item["rebound_pct"], 6) == 0.15
    assert round(item["recovery_ratio"], 6) == 0.6
    assert item["status"] == "ongoing"


def test_price_zone_merging() -> None:
    import pandas as pd

    frame = pd.DataFrame({
        "time_key": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"],
        "close": [10.2, 10.8, 11.1, 14.2],
    })
    zones = MODULE.occupancy_zones(frame, years=5, bin_width=1.0, top_bins=3)
    assert zones[0]["low"] == 10.0
    assert zones[0]["high"] == 12.0
    assert zones[0]["trading_days"] == 3


if __name__ == "__main__":
    test_recovery_ratio_and_ongoing_status()
    test_price_zone_merging()
    print("PASS: drawdown/rebound model tests")
