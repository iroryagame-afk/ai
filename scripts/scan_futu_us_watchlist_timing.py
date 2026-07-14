#!/usr/bin/env python3
import argparse
import csv
import json
import math
import sys
import time
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FUTU_SCRIPTS = ROOT / "integrations" / "futu_readonly" / "scripts"
if str(FUTU_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(FUTU_SCRIPTS))

import common  # noqa: E402


def safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        if isinstance(value, float) and math.isnan(value):
            return default
        return float(value)
    except Exception:
        return default


def ema(values, span):
    if not values:
        return 0.0
    alpha = 2 / (span + 1)
    current = values[0]
    for value in values[1:]:
        current = alpha * value + (1 - alpha) * current
    return current


def sma(values, n):
    values = values[-n:]
    return sum(values) / len(values) if values else 0.0


def pct(a, b):
    return (a / b - 1) * 100 if b else 0.0


def atr14(bars):
    if len(bars) < 15:
        return 0.0
    trs = []
    for i in range(-14, 0):
        row = bars[i]
        prev = bars[i - 1]
        trs.append(max(row["high"] - row["low"], abs(row["high"] - prev["close"]), abs(row["low"] - prev["close"])))
    return sum(trs) / len(trs)


def rsi14(closes):
    if len(closes) < 15:
        return 50.0
    gains = []
    losses = []
    for i in range(-14, 0):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains) / 14
    avg_loss = sum(losses) / 14
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def futu_code(ticker):
    return "US." + ticker.upper().replace("-", ".")


def fetch_user_group(ctx, group_name):
    ret, data = ctx.get_user_security(group_name)
    if ret != common.RET_OK:
        raise RuntimeError(f"读取自选分组失败: {data}")
    rows = []
    for i in range(len(data)):
        row = data.iloc[i]
        rows.append({
            "code": str(common.safe_get(row, "code", default="")),
            "ticker": str(common.safe_get(row, "code", default="")).replace("US.", ""),
            "name": str(common.safe_get(row, "name", default="")),
            "stock_type": str(common.safe_get(row, "stock_type", default="")),
            "listing_date": str(common.safe_get(row, "listing_date", default="")),
        })
    return rows


def fetch_daily_bars(ctx, code, start, end):
    ret, data, page_req_key = ctx.request_history_kline(
        code,
        start=start,
        end=end,
        ktype=common.KLType.K_DAY,
        autype=common.AuType.NONE,
        max_count=1000,
        session=common.Session.RTH,
    )
    if ret != common.RET_OK:
        raise RuntimeError(str(data))
    parts = [data]
    while page_req_key is not None:
        ret, data, page_req_key = ctx.request_history_kline(
            code,
            start=start,
            end=end,
            ktype=common.KLType.K_DAY,
            autype=common.AuType.NONE,
            max_count=1000,
            page_req_key=page_req_key,
            session=common.Session.RTH,
        )
        if ret != common.RET_OK:
            raise RuntimeError(str(data))
        parts.append(data)
    try:
        import pandas as pd
        data = pd.concat(parts, ignore_index=True)
    except Exception:
        data = parts[0]
    bars = []
    for i in range(len(data)):
        row = data.iloc[i]
        bars.append({
            "date": str(common.safe_get(row, "time_key", default="")).split(" ")[0],
            "open": safe_float(common.safe_get(row, "open", default=0)),
            "high": safe_float(common.safe_get(row, "high", default=0)),
            "low": safe_float(common.safe_get(row, "low", default=0)),
            "close": safe_float(common.safe_get(row, "close", default=0)),
            "volume": safe_float(common.safe_get(row, "volume", default=0)),
        })
    return [b for b in bars if b["open"] and b["high"] and b["low"] and b["close"]]


def analyze_bars(ticker, name, bars, qqq=None, spy=None):
    if len(bars) < 80:
        raise ValueError("K线不足")
    closes = [b["close"] for b in bars]
    volumes = [b["volume"] for b in bars]
    last = bars[-1]
    prev = bars[-2]
    close = last["close"]
    e5, e10, e20, e55, e200 = (ema(closes, n) for n in (5, 10, 20, 55, 200))
    a = atr14(bars)
    atr_pct = a / close * 100 if close else 0
    ret20 = pct(close, closes[-21]) if len(closes) > 21 else 0
    ret60 = pct(close, closes[-61]) if len(closes) > 61 else 0
    high20 = max(b["high"] for b in bars[-20:])
    high60 = max(b["high"] for b in bars[-60:])
    low20 = min(b["low"] for b in bars[-20:])
    vol_ratio = volumes[-1] / sma(volumes[:-1], 20) if sma(volumes[:-1], 20) else 0
    rsi = rsi14(closes)
    macd_fast = ema(closes, 12)
    macd_slow = ema(closes, 26)
    macd_line = macd_fast - macd_slow
    macd_signal = ema([ema(closes[:i + 1], 12) - ema(closes[:i + 1], 26) for i in range(len(closes))], 9)
    a6 = sum([
        close > e10,
        close > e20,
        closes[-1] > closes[-11] if len(closes) > 11 else False,
        rsi >= 52,
        macd_line >= macd_signal,
    ])
    q20 = qqq["ret20"] if qqq else 0
    s20 = spy["ret20"] if spy else 0
    q60 = qqq["ret60"] if qqq else 0
    s60 = spy["ret60"] if spy else 0
    rs_ok = ret20 > max(q20, s20) + 1.0 and ret60 > ((q60 + s60) / 2)
    trend_ok = close > e20 and e20 > e55 and close > e55
    reclaimed = close > e5 and close > e10 and prev["close"] <= max(e5, e10)
    close_above_prev_high = close > prev["high"]
    controlled_breakout = close >= high20 * 0.995 and vol_ratio >= 1.05 and vol_ratio <= 2.2 and atr_pct < 5 and close >= last["low"] + (last["high"] - last["low"]) * 0.6
    heat_flags = [
        ret20 > 25,
        atr_pct > 6,
        pct(close, e20) > 12,
        pct(close, e200) > 50,
    ]
    heat = sum(heat_flags)
    broken = close < e55
    near_ema20 = abs(pct(close, e20)) <= 3.5
    near_ema55 = abs(pct(close, e55)) <= 4.5
    benchmark_ok = bool(qqq and spy and not (qqq["close"] < qqq["ema20"] and spy["close"] < spy["ema20"]) and qqq["close"] >= qqq["ema55"])

    if not benchmark_ok:
        action = "等待确认"
        reason = "QQQ/SPY基准防守，禁止新买升级"
    elif broken:
        action = "破位观望"
        reason = "跌破EMA55，先等修复"
    elif heat:
        action = "暂不追"
        reason = "高热度/高波动，适合持有不适合新追"
    elif trend_ok and rs_ok and a6 >= 4 and (close_above_prev_high or reclaimed or controlled_breakout):
        action = "可小仓"
        reason = "趋势、相对强弱和确认信号同时满足"
    elif trend_ok and rs_ok and (near_ema20 or controlled_breakout):
        action = "观察仓"
        reason = "趋势和相对强弱合格，但确认不足"
    elif trend_ok and (near_ema20 or near_ema55):
        action = "等待确认"
        reason = "到观察区，但相对强弱或动能未达标"
    else:
        action = "暂不优先"
        reason = "买点不清晰"

    buy_zone = ""
    if trend_ok:
        buy_zone = f"{e20 * 0.985:.2f}-{e20 * 1.015:.2f}"
    if near_ema55:
        buy_zone = f"{e55 * 0.985:.2f}-{e55 * 1.015:.2f}"
    stop = min(e20 * 0.98, close - 1.2 * a) if trend_ok else e55 * 0.98
    score = 0
    score += 25 if benchmark_ok else 0
    score += 20 if trend_ok else 0
    score += 20 if rs_ok else 0
    score += a6 * 5
    score += 10 if controlled_breakout or close_above_prev_high or reclaimed else 0
    score -= heat * 12
    score -= 20 if broken else 0

    return {
        "ticker": ticker,
        "name": name,
        "date": last["date"],
        "close": round(close, 2),
        "ret1": round(pct(close, prev["close"]), 2),
        "ret20": round(ret20, 2),
        "ret60": round(ret60, 2),
        "ema10": round(e10, 2),
        "ema20": round(e20, 2),
        "ema55": round(e55, 2),
        "ema200": round(e200, 2),
        "atr_pct": round(atr_pct, 2),
        "vol_ratio": round(vol_ratio, 2),
        "a6": int(a6),
        "rs_ok": rs_ok,
        "heat": int(heat),
        "action": action,
        "reason": reason,
        "buy_zone": buy_zone,
        "stop": round(stop, 2),
        "pressure": f"{high20:.2f}/{high60:.2f}",
        "low20": round(low20, 2),
        "score": round(score, 1),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", default="US")
    parser.add_argument("--sleep", type=float, default=0.55)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--min-bars", type=int, default=80)
    args = parser.parse_args()

    end = date.today().isoformat()
    start = (date.today() - timedelta(days=430)).isoformat()
    out_dir = ROOT / "outputs" / "us_watchlist_timing"
    out_dir.mkdir(parents=True, exist_ok=True)

    ctx = common.create_quote_context()
    errors = []
    try:
        raw = fetch_user_group(ctx, args.group)
        stocks = []
        seen = set()
        for row in raw:
            code = row["code"]
            if not code.startswith("US."):
                continue
            if row["stock_type"] != "STOCK":
                continue
            if code in seen:
                continue
            seen.add(code)
            stocks.append(row)
        if args.limit:
            stocks = stocks[:args.limit]

        bench = {}
        for ticker in ("QQQ", "SPY"):
            bars = fetch_daily_bars(ctx, futu_code(ticker), start, end)
            bench[ticker] = analyze_bars(ticker, ticker, bars)
            time.sleep(args.sleep)

        results = []
        for item in stocks:
            try:
                bars = fetch_daily_bars(ctx, item["code"], start, end)
                if len(bars) < args.min_bars:
                    raise ValueError(f"K线不足 {len(bars)}")
                results.append(analyze_bars(item["ticker"], item["name"], bars, bench["QQQ"], bench["SPY"]))
            except Exception as exc:
                errors.append({"code": item["code"], "name": item["name"], "error": str(exc)})
            time.sleep(args.sleep)
    finally:
        common.safe_close(ctx)

    rank = {"可小仓": 0, "观察仓": 1, "等待确认": 2, "暂不追": 3, "暂不优先": 4, "破位观望": 5}
    results.sort(key=lambda r: (rank.get(r["action"], 9), -r["score"], -r["ret20"]))
    payload = {
        "generated_at": date.today().isoformat(),
        "group": args.group,
        "source": "Futu OpenD / request_history_kline / RTH daily",
        "benchmark": bench,
        "count": len(results),
        "results": results,
        "errors": errors,
    }
    json_path = out_dir / "latest_us_watchlist_timing.json"
    csv_path = out_dir / "latest_us_watchlist_timing.csv"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if results:
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
            writer.writeheader()
            writer.writerows(results)
    print(json.dumps({
        "source": payload["source"],
        "group": args.group,
        "count": len(results),
        "errors": len(errors),
        "json": str(json_path),
        "csv": str(csv_path),
        "benchmark": {k: {kk: v[kk] for kk in ("date", "close", "ema20", "ema55", "ret20", "ret60", "action")} for k, v in bench.items()},
        "top": results[:25],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
