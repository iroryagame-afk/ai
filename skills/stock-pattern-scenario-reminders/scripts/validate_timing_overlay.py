#!/usr/bin/env python3
"""Validate the market-specific timing overlay attached to a pattern plan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ENUMS = {
    "market": {"A_SHARE", "US", "HK"},
    "trend_state": {"healthy", "repair", "overheated", "broken", "unknown"},
    "heat_state": {"normal", "warm", "overheated", "unknown"},
    "market_gate": {"offense", "neutral", "defense", "not_applicable", "unknown"},
    "signal_state": {"alert", "pending_close", "confirmed", "failed"},
    "position_state": {"flat", "existing_sellable", "new_today_locked", "mixed", "unknown"},
    "decision": {"wait_confirmation", "observe", "candidate", "execute_small", "hold", "reduce", "avoid"},
}


def validate_overlay(overlay: dict) -> dict:
    required = {
        "market", "source_skill", "data_status", "trend_state", "heat_state",
        "market_gate", "signal_state", "position_state", "decision", "summary",
        "confirmation", "execution",
    }
    missing = sorted(required - set(overlay))
    if missing:
        raise ValueError(f"timing_overlay missing fields: {missing}")
    for field, allowed in ENUMS.items():
        if overlay.get(field) not in allowed:
            raise ValueError(f"invalid {field}: {overlay.get(field)}")
    if len(str(overlay["summary"])) > 30:
        raise ValueError("timing_overlay.summary must be <= 30 characters")

    decision = overlay["decision"]
    signal_state = overlay["signal_state"]
    if signal_state in {"alert", "pending_close"} and decision in {"candidate", "execute_small"}:
        raise ValueError("unconfirmed signals cannot become candidate/execute_small")
    if overlay["trend_state"] == "broken" and decision in {"candidate", "execute_small"}:
        raise ValueError("broken trends cannot become fresh entries")
    if overlay["heat_state"] == "overheated" and decision == "execute_small":
        raise ValueError("overheated setups cannot be fresh execute_small entries")
    if overlay["market_gate"] == "defense" and decision == "execute_small":
        raise ValueError("defensive market gate cannot permit execute_small")
    if overlay["data_status"] != "VERIFIED_FUTU_OPEND" and decision == "execute_small":
        raise ValueError("unverified data cannot permit execute_small")

    market = overlay["market"]
    execution = overlay["execution"]
    if market == "A_SHARE":
        if overlay["source_skill"] != "a-stock-position-timing":
            raise ValueError("A shares must route to a-stock-position-timing")
        needed = {"signal_date", "earliest_entry_date", "earliest_sell_date_if_filled", "same_day_exit_allowed", "t1_scenarios", "tradability_checks"}
        absent = sorted(needed - set(execution))
        if absent:
            raise ValueError(f"A-share execution missing: {absent}")
        if execution["same_day_exit_allowed"] is not False:
            raise ValueError("ordinary A-share new positions cannot exit on entry day")
        if not execution["signal_date"] < execution["earliest_entry_date"] < execution["earliest_sell_date_if_filled"]:
            raise ValueError("A-share signal/entry/earliest-sell dates must be strictly ordered")
        branches = set((execution.get("t1_scenarios") or {}).keys())
        if branches != {"flat_or_small_gap", "large_gap_up", "large_gap_down"}:
            raise ValueError("A-share T+1 plan needs flat/up-gap/down-gap branches")
    else:
        if overlay["source_skill"] != "stock-position-timing":
            raise ValueError("US/HK names must route to stock-position-timing")
        if market == "US" and overlay["market_gate"] == "not_applicable":
            raise ValueError("US timing must evaluate the QQQ/SPY market gate")
        session = execution.get("session")
        if decision == "execute_small" and session in {"premarket", "open_observation", None}:
            raise ValueError("premarket/first-15-minute states cannot execute_small")
        if decision == "execute_small" and not execution.get("intraday_trigger"):
            raise ValueError("same-day execute_small needs an intraday trigger")

    return {"status": "VALID", "market": market, "decision": decision, "source_skill": overlay["source_skill"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    result = validate_overlay(plan.get("timing_overlay") or {})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
