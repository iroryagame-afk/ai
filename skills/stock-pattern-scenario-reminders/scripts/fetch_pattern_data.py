#!/usr/bin/env python3
"""Fetch Futu snapshot, daily bars, indicators and local extrema for pattern review."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd


def fetch_daily(ctx, code: str, start: str, end: str) -> pd.DataFrame:
    from futu import AuType, KLType, RET_OK

    ret, frame, page_key = ctx.request_history_kline(
        code,
        start=start,
        end=end,
        ktype=KLType.K_DAY,
        autype=AuType.QFQ,
        max_count=1000,
    )
    if ret != RET_OK:
        raise RuntimeError(f"{code} request_history_kline: {frame}")
    parts = [frame]
    while page_key:
        ret, frame, page_key = ctx.request_history_kline(
            code,
            start=start,
            end=end,
            ktype=KLType.K_DAY,
            autype=AuType.QFQ,
            max_count=1000,
            page_req_key=page_key,
        )
        if ret != RET_OK:
            raise RuntimeError(f"{code} request_history_kline page: {frame}")
        parts.append(frame)
    return (
        pd.concat(parts, ignore_index=True)
        .drop_duplicates("time_key")
        .sort_values("time_key")
        .reset_index(drop=True)
    )


def enrich(frame: pd.DataFrame, extrema_window: int) -> pd.DataFrame:
    out = frame.copy()
    for period in (5, 10, 20, 55, 200):
        out[f"ema{period}"] = out["close"].ewm(span=period, adjust=False).mean()
    true_range = pd.concat(
        [
            out["high"] - out["low"],
            (out["high"] - out["close"].shift()).abs(),
            (out["low"] - out["close"].shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    out["atr14"] = true_range.ewm(alpha=1 / 14, adjust=False).mean()
    delta = out["close"].diff()
    gains = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    losses = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    relative_strength = gains / losses.replace(0, float("nan"))
    out["rsi14"] = 100 - 100 / (1 + relative_strength)
    out.loc[losses.eq(0) & gains.gt(0), "rsi14"] = 100.0
    out.loc[gains.eq(0) & losses.gt(0), "rsi14"] = 0.0
    out.loc[gains.eq(0) & losses.eq(0), "rsi14"] = 50.0
    ema12 = out["close"].ewm(span=12, adjust=False).mean()
    ema26 = out["close"].ewm(span=26, adjust=False).mean()
    out["macd"] = ema12 - ema26
    out["macd_signal"] = out["macd"].ewm(span=9, adjust=False).mean()
    out["macd_hist"] = out["macd"] - out["macd_signal"]
    out["volume_ma20"] = out["volume"].rolling(20).mean()
    out["volume_ratio20"] = out["volume"] / out["volume_ma20"].replace(0, float("nan"))
    middle = out["close"].rolling(20).mean()
    deviation = out["close"].rolling(20).std(ddof=0)
    out["bb_width_pct"] = (4 * deviation / middle.replace(0, float("nan"))) * 100
    out["return_20d"] = out["close"].pct_change(20) * 100
    out["return_60d"] = out["close"].pct_change(60) * 100
    out["high_55"] = out["high"].rolling(55).max()
    out["low_55"] = out["low"].rolling(55).min()
    span = extrema_window * 2 + 1
    out["is_local_min"] = out["low"].eq(out["low"].rolling(span, center=True).min())
    out["is_local_max"] = out["high"].eq(out["high"].rolling(span, center=True).max())
    return out


def clean_value(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def snapshot_record(frame: pd.DataFrame, code: str) -> dict:
    row = frame.set_index("code").loc[code]
    fields = [
        "code",
        "name",
        "update_time",
        "last_price",
        "open_price",
        "high_price",
        "low_price",
        "prev_close_price",
        "volume",
        "after_price",
        "after_high_price",
        "after_low_price",
        "after_volume",
        "overnight_price",
    ]
    result = {"code": code}
    for field in fields:
        if field == "code" or field not in row.index:
            continue
        value = clean_value(row[field])
        if value == "N/A":
            value = None
        result[field] = value
    return result


def is_live_daily_bar(code: str, last_date: str, snapshot: dict, today: str | None = None) -> bool:
    """Return True only when today's daily bar is still inside the regular session."""
    today = today or date.today().isoformat()
    update_time = str(snapshot.get("update_time") or "")
    if last_date != today or update_time[:10] != last_date:
        return False
    market = code.split(".", 1)[0]
    close_time = {
        "SH": "15:00:00",
        "SZ": "15:00:00",
        "BJ": "15:00:00",
        "HK": "16:00:00",
        "US": "16:00:00",
    }.get(market)
    if close_time is None:
        return True
    update_clock = update_time[11:19]
    return not update_clock or update_clock < close_time


def benchmark_summary(ctx, codes: list[str], start: str, end: str) -> dict:
    result = {}
    for code in codes:
        frame = enrich(fetch_daily(ctx, code, start, end), 4)
        row = frame.iloc[-1]
        result[code] = {
            "date": str(row["time_key"])[:10],
            "close": round(float(row["close"]), 4),
            "ema20": round(float(row["ema20"]), 4),
            "ema55": round(float(row["ema55"]), 4),
            "above_ema20": bool(row["close"] >= row["ema20"]),
            "above_ema55": bool(row["close"] >= row["ema55"]),
            "return_20d": round(float(row["return_20d"]), 2),
            "return_60d": round(float(row["return_60d"]), 2),
        }
    return result


def main() -> int:
    from futu import OpenQuoteContext, RET_OK

    parser = argparse.ArgumentParser()
    parser.add_argument("--code", required=True, help="Futu code, e.g. HK.00700 or US.PLTR")
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default=date.today().isoformat())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=11111)
    parser.add_argument("--extrema-window", type=int, default=4)
    parser.add_argument("--display-bars", type=int, default=100)
    parser.add_argument("--no-benchmarks", action="store_true")
    args = parser.parse_args()

    ctx = OpenQuoteContext(host=args.host, port=args.port)
    try:
        ret, snapshots = ctx.get_market_snapshot([args.code])
        if ret != RET_OK:
            raise RuntimeError(str(snapshots))
        snapshot = snapshot_record(snapshots, args.code)
        daily = enrich(fetch_daily(ctx, args.code, args.start, args.end), args.extrema_window)
        if len(daily) < 250:
            sample_warning = f"样本仅{len(daily)}根，少于250根"
        else:
            sample_warning = None

        last_date = str(daily.iloc[-1]["time_key"])[:10]
        includes_live_bar = is_live_daily_bar(args.code, last_date, snapshot)
        completed = daily.iloc[:-1] if includes_live_bar and len(daily) > 1 else daily
        last_completed = completed.iloc[-1]

        extrema = daily[daily["is_local_min"] | daily["is_local_max"]].tail(80)
        history_fields = [
            "time_key", "open", "high", "low", "close", "volume",
            "ema20", "ema55", "ema200", "atr14", "rsi14", "macd",
            "macd_signal", "macd_hist", "volume_ratio20", "bb_width_pct",
        ]
        history = []
        for _, row in daily.tail(args.display_bars).iterrows():
            item = {field: clean_value(row[field]) for field in history_fields}
            item["date"] = str(item.pop("time_key"))[:10]
            history.append(item)
        extrema_rows = []
        for _, row in extrema.iterrows():
            extrema_rows.append(
                {
                    "date": str(row["time_key"])[:10],
                    "high": round(float(row["high"]), 4),
                    "low": round(float(row["low"]), 4),
                    "close": round(float(row["close"]), 4),
                    "kind": "low" if bool(row["is_local_min"]) else "high",
                }
            )

        benchmarks = {}
        if args.code.startswith("US.") and not args.no_benchmarks:
            benchmarks = benchmark_summary(ctx, ["US.QQQ", "US.SPY"], args.start, args.end)

        result = {
            "status": "VERIFIED_FUTU_OPEND",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "source": "Futu OpenD request_history_kline K_DAY QFQ + market snapshot",
            "code": args.code,
            "snapshot": snapshot,
            "daily_count": int(len(daily)),
            "sample_warning": sample_warning,
            "includes_live_daily_bar": includes_live_bar,
            "latest_daily_bar": last_date,
            "latest_completed_daily_bar": str(last_completed["time_key"])[:10],
            "latest_completed": {
                "close": round(float(last_completed["close"]), 4),
                "ema20": round(float(last_completed["ema20"]), 4),
                "ema55": round(float(last_completed["ema55"]), 4),
                "ema200": round(float(last_completed["ema200"]), 4),
                "atr14": round(float(last_completed["atr14"]), 4),
                "atr_pct": round(float(last_completed["atr14"] / last_completed["close"] * 100), 2),
                "rsi14": round(float(last_completed["rsi14"]), 2),
                "macd": round(float(last_completed["macd"]), 4),
                "macd_signal": round(float(last_completed["macd_signal"]), 4),
                "macd_hist": round(float(last_completed["macd_hist"]), 4),
                "volume_ratio20": round(float(last_completed["volume_ratio20"]), 2),
                "bb_width_pct": round(float(last_completed["bb_width_pct"]), 2),
                "return_20d": round(float(last_completed["return_20d"]), 2),
                "return_60d": round(float(last_completed["return_60d"]), 2),
                "high_55": round(float(last_completed["high_55"]), 4),
                "low_55": round(float(last_completed["low_55"]), 4),
            },
            "benchmarks": benchmarks,
            "extrema": extrema_rows,
            "history": history,
        }
    finally:
        ctx.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "status": result["status"], "daily_count": result["daily_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
