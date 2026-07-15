#!/usr/bin/env python3
"""Project repair and Fibonacci extension targets from A-B-C anchors."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def load_analyze():
    path = Path(__file__).with_name("analyze.py")
    spec = importlib.util.spec_from_file_location("stock_drawdown_analyze", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--low", type=float, required=True, help="A: impulse low")
    parser.add_argument("--peak", type=float, required=True, help="B: impulse peak")
    parser.add_argument("--rebound-low", type=float, required=True, help="C: confirmed pullback low")
    args = parser.parse_args()
    analyze = load_analyze()
    anchor = {"low": args.low, "peak": args.peak}
    repair = analyze.repair_ladder(anchor, args.rebound_low)
    extension = analyze.extension_ladder(anchor, args.rebound_low)
    result = {
        "anchor": {"A": args.low, "B": args.peak, "C": args.rebound_low},
        "repair_targets": [{**row, "value": round(row["value"], 4)} for row in repair],
        "extension_targets": [{**row, "value": round(row["value"], 4)} for row in extension],
        "semantics": {
            "support_touch": "candidate entry zone, not bottom confirmation",
            "first_reclaim": "first shallower retracement level above C; require a completed-bar close and preferably a successful retest",
            "extension_gate": "do not promote extension targets until B is reclaimed and C remains valid",
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
