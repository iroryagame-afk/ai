#!/usr/bin/env python3
"""Deterministic tests for the drawdown model; no OpenD connection required."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


analyze = load("drawdown_analyze", ROOT / "scripts/analyze.py")
sync = load("drawdown_sync", ROOT / "scripts/sync_reminders.py")


def test_standard_ratios_exclude_718():
    assert 0.718 not in analyze.DEFAULT_RATIOS
    assert analyze.DEFAULT_RATIOS == [0.382, 0.500, 0.618, 0.786]


def test_level_formula():
    anchor = {"low": 275.15, "peak": 317.31}
    assert round(analyze.level(anchor, 0.382), 2) == 301.20
    assert round(analyze.level(anchor, 0.618), 2) == 291.26


def test_repair_ladder_starts_at_next_shallower_level():
    anchor = {"low": 149.51, "peak": 195.40}
    rows = analyze.repair_ladder(anchor, 172.45)
    assert [round(row["value"], 2) for row in rows[:3]] == [177.87, 184.57, 195.40]
    assert [row["ratio"] for row in rows[:3]] == [0.382, 0.236, 0.0]


def test_extension_ladder_uses_confirmed_c_and_ab_impulse():
    anchor = {"low": 149.51, "peak": 195.40}
    rows = analyze.extension_ladder(anchor, 172.45)
    assert [round(row["value"], 2) for row in rows] == [200.81, 218.34, 230.82, 246.70]


def test_extension_rejects_unconfirmed_out_of_range_c():
    anchor = {"low": 149.51, "peak": 195.40}
    try:
        analyze.extension_ladder(anchor, 196.0)
    except ValueError:
        return
    raise AssertionError("out-of-range C must be rejected")


def test_failure_is_not_support():
    assert analyze.classify_depth(1.01, analyze.DEFAULT_RATIOS) == ">100%"
    assert analyze.classify_depth(0.95, analyze.DEFAULT_RATIOS) == "100%"
    assert analyze.classify_depth(0.61, analyze.DEFAULT_RATIOS) == "0.618"


def test_tied_core_zone():
    result = analyze.ranked_result({"0.382": 0.2828, "0.618": 0.2829, "0.500": 0.20}, 0.01)
    assert result["tied_core_zone"] is True


def test_active_breakout_marks_peak_unconfirmed():
    frame = pd.DataFrame(
        {
            "time_key": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05"],
            "close": [100.0, 120.0, 100.0, 110.0, 125.0],
        }
    )
    anchor = analyze.active_anchor(frame, 0.12)
    assert anchor["low"] == 100.0
    assert anchor["peak"] == 125.0
    assert anchor["peak_confirmed"] is False


def test_notes_fit_futu_limit():
    for code in ["US.NVDA", "SH.603986"]:
        for direction in ["PRICE_UP", "PRICE_DOWN"]:
            note = sync.make_note(code, 0.618, 0.442, 1, direction, False)
            assert len(note) <= 20
            assert "P1" in note and "44%" in note


def test_tied_note_is_explicit():
    note = sync.make_note("US.AAPL", 0.618, 0.2829, 1, "PRICE_DOWN", True)
    assert note.startswith("并1")
    assert "28%" in note


def main() -> int:
    tests = [value for name, value in globals().items() if name.startswith("test_") and callable(value)]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"PASS {len(tests)} tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
