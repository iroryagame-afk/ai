#!/usr/bin/env python3
"""Read back exact Futu reminder values and notes from an applied audit file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    from futu import OpenQuoteContext, RET_OK

    parser = argparse.ArgumentParser()
    parser.add_argument("--applied", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=11111)
    args = parser.parse_args()
    applied = json.loads(args.applied.read_text(encoding="utf-8"))
    ctx = OpenQuoteContext(host=args.host, port=args.port)
    result = {"status": "VERIFIED_FUTU_OPEND", "stocks": {}}
    try:
        for code, stock in applied["stocks"].items():
            ret, reminders = ctx.get_price_reminder(code=code)
            if ret != RET_OK:
                raise RuntimeError(f"{code}: {reminders}")
            checks = []
            for rule in stock["rules"]:
                same = reminders[(reminders["value"].astype(float) - rule["value"]).abs() <= 0.01]
                matched = same[same["note"].astype(str) == rule["note"]]
                checks.append({"value": rule["value"], "note": rule["note"], "verified": bool(len(matched))})
            result["stocks"][code] = {"verified": all(row["verified"] for row in checks), "checks": checks}
    finally:
        ctx.close()
    result["verified_count"] = sum(row["verified"] for row in result["stocks"].values())
    result["expected_count"] = len(result["stocks"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "result": result}, ensure_ascii=False, indent=2))
    return 0 if result["verified_count"] == result["expected_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

