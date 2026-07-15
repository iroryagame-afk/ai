#!/usr/bin/env python3
"""Write ranked drawdown reminders to Futu after explicit confirmation."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path


CONFIRM_TEXT = "WRITE_FUTU_REMINDERS"


def is_a_share(code: str) -> bool:
    return code.startswith(("SH.", "SZ.", "BJ."))


def make_note(code: str, ratio: float, score: float, rank: int, direction: str, tied: bool) -> str:
    prefix = "并1" if tied else f"P{rank}"
    probability = round(score * 100)
    if is_a_share(code):
        action = "收复次日" if direction == "PRICE_UP" else "到达次日"
    else:
        action = "收复看" if direction == "PRICE_UP" else "到达看"
    note = f"{prefix}·{ratio * 100:.1f}/{probability}%｜{action}"
    if len(note) > 20:
        raise ValueError(f"Futu note too long: {note}")
    return note


def sync_one(ctx, code: str, rule: dict, existing):
    from futu import PriceReminderFreq, PriceReminderType, RET_OK, SetPriceReminderOp

    same = existing[(existing["value"].astype(float) - rule["value"]).abs() <= 0.01]
    reminder_type = getattr(PriceReminderType, rule["direction"])
    if len(same):
        row = same.iloc[0]
        ret, data = ctx.set_price_reminder(
            code,
            SetPriceReminderOp.MODIFY,
            key=row["key"],
            reminder_type=reminder_type,
            reminder_freq=PriceReminderFreq.ALWAYS,
            value=rule["value"],
            note=rule["note"],
        )
        if ret == RET_OK:
            ret, data = ctx.set_price_reminder(code, SetPriceReminderOp.ENABLE, key=row["key"])
        op = "MODIFY"
    else:
        ret, data = ctx.set_price_reminder(
            code,
            SetPriceReminderOp.ADD,
            reminder_type=reminder_type,
            reminder_freq=PriceReminderFreq.ALWAYS,
            value=rule["value"],
            note=rule["note"],
        )
        op = "ADD"
    if ret != RET_OK:
        raise RuntimeError(f"{code} {rule['value']} {op}: {data}")
    return {"op": op, **rule}


def build_rules(code: str, target: dict, current: float) -> list[dict]:
    ranking = target["ranking"]
    ratios = [float(ranking["primary_ratio"]), float(ranking["secondary_ratio"])]
    tied = bool(ranking.get("tied_core_zone"))
    rules = []
    for index, ratio in enumerate(ratios):
        value = round(float(target["levels"][f"{ratio:.3f}"]), 2)
        direction = "PRICE_UP" if value > current else "PRICE_DOWN"
        score = float(target["final_scores"][f"{ratio:.3f}"])
        rules.append(
            {
                "ratio": ratio,
                "probability": score,
                "value": value,
                "direction": direction,
                "note": make_note(code, ratio, score, index + 1, direction, tied),
            }
        )
    invalidation = round(float(target["levels"]["1.000"]), 2)
    direction = "PRICE_UP" if invalidation > current else "PRICE_DOWN"
    note = "前低收复｜重回波段" if direction == "PRICE_UP" else ("前低失效｜次日风控" if is_a_share(code) else "前低失效｜跌破风控")
    rules.append({"ratio": 1.0, "value": invalidation, "direction": direction, "note": note})
    return rules


def main() -> int:
    from futu import OpenQuoteContext, RET_OK

    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=11111)
    args = parser.parse_args()
    if not args.apply or args.confirm != CONFIRM_TEXT:
        raise SystemExit(f"Refusing to write. Use --apply --confirm {CONFIRM_TEXT}")
    analysis = json.loads(args.analysis.read_text(encoding="utf-8"))
    codes = list(analysis["targets"])
    ctx = OpenQuoteContext(host=args.host, port=args.port)
    result = {"generated_at": datetime.now().isoformat(timespec="seconds"), "source": str(args.analysis), "stocks": {}}
    try:
        ret, snapshots = ctx.get_market_snapshot(codes)
        if ret != RET_OK:
            raise RuntimeError(str(snapshots))
        snapshots = snapshots.set_index("code")
        for code, target in analysis["targets"].items():
            current = float(snapshots.loc[code]["last_price"])
            rules = build_rules(code, target, current)
            ret, existing = ctx.get_price_reminder(code=code)
            if ret != RET_OK:
                raise RuntimeError(f"{code}: {existing}")
            result["stocks"][code] = {
                "current": current,
                "rules": rules,
                "applied": [sync_one(ctx, code, rule, existing) for rule in rules],
            }
    finally:
        ctx.close()
    output = args.output or args.analysis.with_name(args.analysis.stem + "_applied.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "result": result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
