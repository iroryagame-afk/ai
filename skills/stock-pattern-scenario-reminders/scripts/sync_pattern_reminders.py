#!/usr/bin/env python3
"""Preview or write direct pattern levels to Futu reminders with exact readback."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


CONFIRM_TEXT = "WRITE_FUTU_PATTERN_REMINDERS"


def reminder_price(reminder: dict) -> float:
    """Return the canonical reminder price while accepting legacy plans."""
    raw = reminder.get("price", reminder.get("value"))
    if raw is None:
        raise ValueError(f"reminder needs price: {reminder}")
    return round(float(raw), 4)


def normalized_rule(reminder: dict) -> dict:
    return {
        "price": reminder_price(reminder),
        "direction": reminder["direction"],
        "note": reminder["note"],
        "freq": "ALWAYS",
    }


def load_plans(paths: list[Path]) -> list[dict]:
    plans = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    codes = [plan.get("code") for plan in plans]
    if any(not code for code in codes):
        raise ValueError("every plan needs code")
    if len(codes) != len(set(codes)):
        raise ValueError("duplicate stock codes in plans")
    for plan in plans:
        reminders = plan.get("reminders", [])
        if not reminders:
            raise ValueError(f"{plan['code']} has no reminders")
        if len(reminders) > 3:
            raise ValueError(f"{plan['code']} has more than 3 reminders")
        seen = set()
        for reminder in reminders:
            price = reminder_price(reminder)
            if price in seen:
                raise ValueError(f"{plan['code']} duplicate reminder price {price}")
            seen.add(price)
            if reminder.get("direction") not in {"PRICE_UP", "PRICE_DOWN"}:
                raise ValueError(f"{plan['code']} invalid direction: {reminder}")
            note = str(reminder.get("note", ""))
            if not note or len(note) > 20:
                raise ValueError(f"{plan['code']} note must be 1-20 characters: {note}")
    return plans


def preview(plans: list[dict]) -> dict:
    return {
        "status": "DRY_RUN_NO_FUTU_WRITE",
        "stocks": {
            plan["code"]: [
                normalized_rule(reminder)
                for reminder in plan["reminders"]
            ]
            for plan in plans
        },
    }


def same_price(frame, value: float):
    if frame is None or len(frame) == 0 or "value" not in frame.columns:
        return frame.iloc[0:0] if frame is not None else None
    return frame[(frame["value"].astype(float) - value).abs() <= 0.01]


def apply_and_verify(plans: list[dict], host: str, port: int) -> tuple[dict, dict]:
    from futu import (
        OpenQuoteContext,
        PriceReminderFreq,
        PriceReminderType,
        RET_OK,
        SetPriceReminderOp,
    )

    ctx = OpenQuoteContext(host=host, port=port)
    applied = {"generated_at": datetime.now().isoformat(timespec="seconds"), "stocks": {}}
    readback = {"status": "VERIFIED_FUTU_OPEND", "stocks": {}}
    try:
        codes = [plan["code"] for plan in plans]
        ret, snapshots = ctx.get_market_snapshot(codes)
        if ret != RET_OK:
            raise RuntimeError(str(snapshots))
        snapshots = snapshots.set_index("code")

        for plan in plans:
            code = plan["code"]
            ret, existing = ctx.get_price_reminder(code=code)
            if ret != RET_OK:
                raise RuntimeError(f"{code}: {existing}")
            rows = []
            for reminder in plan["reminders"]:
                rule = normalized_rule(reminder)
                matches = same_price(existing, rule["price"])
                reminder_type = getattr(PriceReminderType, rule["direction"])
                if matches is not None and len(matches):
                    key = matches.iloc[0]["key"]
                    ret, data = ctx.set_price_reminder(
                        code,
                        SetPriceReminderOp.MODIFY,
                        key=key,
                        reminder_type=reminder_type,
                        reminder_freq=PriceReminderFreq.ALWAYS,
                        value=rule["price"],
                        note=rule["note"],
                    )
                    if ret == RET_OK:
                        ret, data = ctx.set_price_reminder(code, SetPriceReminderOp.ENABLE, key=key)
                    operation = "MODIFY+ENABLE"
                else:
                    ret, data = ctx.set_price_reminder(
                        code,
                        SetPriceReminderOp.ADD,
                        reminder_type=reminder_type,
                        reminder_freq=PriceReminderFreq.ALWAYS,
                        value=rule["price"],
                        note=rule["note"],
                    )
                    operation = "ADD"
                if ret != RET_OK:
                    raise RuntimeError(f"{code} {rule['price']} {operation}: {data}")
                rows.append({"op": operation, **rule})
            applied["stocks"][code] = {
                "current": float(snapshots.loc[code]["last_price"]),
                "rules": [normalized_rule(row) for row in plan["reminders"]],
                "applied": rows,
            }

        for plan in plans:
            code = plan["code"]
            ret, reminders = ctx.get_price_reminder(code=code)
            if ret != RET_OK:
                raise RuntimeError(f"{code} readback: {reminders}")
            checks = []
            for rule in plan["reminders"]:
                price = reminder_price(rule)
                matches = same_price(reminders, price)
                exact = matches[matches["note"].astype(str) == rule["note"]] if matches is not None and len(matches) else matches
                enabled = True
                if exact is not None and len(exact) and "is_enable" in exact.columns:
                    enabled = bool(exact.iloc[0]["is_enable"])
                checks.append(
                    {
                        "price": price,
                        "note": rule["note"],
                        "enabled": enabled,
                        "verified": bool(exact is not None and len(exact) and enabled),
                    }
                )
            readback["stocks"][code] = {"verified": all(row["verified"] for row in checks), "checks": checks}
    finally:
        ctx.close()

    all_checks = [check for stock in readback["stocks"].values() for check in stock["checks"]]
    readback["verified_count"] = sum(check["verified"] for check in all_checks)
    readback["expected_count"] = len(all_checks)
    if readback["verified_count"] != readback["expected_count"]:
        raise RuntimeError("Futu reminder readback did not match all planned reminders")
    return applied, readback


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, action="append", required=True, help="Repeat for multiple stocks")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/futu-reminders"))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=11111)
    args = parser.parse_args()

    plans = load_plans(args.plan)
    if not args.apply:
        print(json.dumps(preview(plans), ensure_ascii=False, indent=2))
        return 0
    if args.confirm != CONFIRM_TEXT:
        raise SystemExit(f"Refusing to write. Use --apply --confirm {CONFIRM_TEXT}")

    applied, readback = apply_and_verify(plans, args.host, args.port)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    applied_path = args.output_dir / f"{stamp}-pattern-reminders-applied.json"
    readback_path = args.output_dir / f"{stamp}-pattern-reminders-readback.json"
    applied_path.write_text(json.dumps(applied, ensure_ascii=False, indent=2), encoding="utf-8")
    readback_path.write_text(json.dumps(readback, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "VERIFIED_FUTU_OPEND",
                "applied": str(applied_path),
                "readback": str(readback_path),
                "verified_count": readback["verified_count"],
                "expected_count": readback["expected_count"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
