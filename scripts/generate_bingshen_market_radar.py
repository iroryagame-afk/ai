#!/usr/bin/env python3
"""Generate the no-login /bingshen/ A-share close dashboard.

Primary all-market/plate source: local Futu OpenD in read-only mode.
Independent index-date cross-check: Tencent Finance's zero-key public endpoint.
The generator is conservative: required-source failure aborts before overwriting
data.json, so the published page keeps the last verified close. Unsupported
money-flow and quarterly datasets remain explicitly unconnected.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "bingshen" / "data.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128 Safari/537.36"
WATCH_CODES = {
    "002422", "002603", "002737", "603983", "688065", "300975", "688662",
    "688807", "688143", "688596", "688758", "688105", "301047", "000630",
    "001337", "301026", "300274",
}


def request_bytes(url: str, *, referer: str | None = None, timeout: int = 25) -> bytes:
    headers = {"User-Agent": UA, "Accept": "*/*"}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def get_json(base: str, params: dict[str, object], *, referer: str | None = None) -> dict:
    url = base + "?" + urllib.parse.urlencode(params)
    payload = json.loads(request_bytes(url, referer=referer).decode("utf-8"))
    if payload.get("rc") not in (None, 0):
        raise RuntimeError(f"source rc={payload.get('rc')} url={base}")
    return payload


def pause() -> None:
    time.sleep(1.05 + random.random() * 0.35)


def number(value: object, default: float = 0.0) -> float:
    try:
        v = float(value)
        return v if math.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def compact_amount(value: float) -> str:
    value = number(value)
    if abs(value) >= 1e8:
        return f"{value / 1e8:.1f}亿"
    if abs(value) >= 1e4:
        return f"{value / 1e4:.0f}万"
    return f"{value:.0f}"


def tencent_indices() -> tuple[list[dict], str]:
    symbols = [
        ("sh000001", "上证指数", "000001.SH"),
        ("sz399001", "深证成指", "399001.SZ"),
        ("sz399006", "创业板指", "399006.SZ"),
        ("sh000688", "科创50", "000688.SH"),
        ("sh000300", "沪深300", "000300.SH"),
        ("sh000905", "中证500", "000905.SH"),
    ]
    raw = request_bytes("https://qt.gtimg.cn/q=" + ",".join(x[0] for x in symbols)).decode("gbk", "replace")
    result: list[dict] = []
    dates: list[str] = []
    for symbol, fallback_name, code in symbols:
        match = re.search(rf'v_{symbol}="([^"]+)"', raw)
        if not match:
            raise RuntimeError(f"Tencent index missing: {symbol}")
        fields = match.group(1).split("~")
        if len(fields) < 33:
            raise RuntimeError(f"Tencent index malformed: {symbol}")
        stamp = fields[30]
        if len(stamp) >= 8 and stamp[:8].isdigit():
            dates.append(f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}")
        result.append({
            "name": fields[1] or fallback_name,
            "code": code,
            "value": number(fields[3]),
            "change": number(fields[32]),
            "amount": number(fields[37]) * 1e4 if len(fields) > 37 else 0,
            "timestamp": stamp,
        })
    if len(set(dates)) != 1:
        raise RuntimeError(f"Tencent index dates are not unique: {dates}")
    return result, dates[0]


def em_list(fs: str, *, fid: str = "f3", descending: bool = True, size: int = 100) -> list[dict]:
    """Read one ranked slice; full-market coverage comes from Futu OpenD."""
    payload = get_json(
        "https://push2.eastmoney.com/api/qt/clist/get",
        {
            "pn": 1, "pz": min(size, 100), "po": 1 if descending else 0,
            "np": 1, "fltt": 2, "invt": 2, "fid": fid, "fs": fs,
            "fields": "f2,f3,f4,f5,f6,f8,f12,f14,f62,f100,f104,f105,f106,f128,f136",
        },
        referer="https://quote.eastmoney.com/center/",
    )
    rows = ((payload.get("data") or {}).get("diff") or [])
    if not isinstance(rows, list):
        raise RuntimeError("Eastmoney clist diff missing")
    return rows


def futu_stocks() -> list[dict]:
    from futu import Market, OpenQuoteContext, RET_OK, SecurityType

    ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
    try:
        basics = []
        for market in (Market.SH, Market.SZ):
            ret, frame = ctx.get_stock_basicinfo(market, SecurityType.STOCK)
            if ret != RET_OK or frame is None:
                raise RuntimeError(f"Futu get_stock_basicinfo failed: {market} {frame}")
            basics.extend(frame.to_dict("records"))
        today = datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
        codes = [
            str(x.get("code")) for x in basics
            if str(x.get("code", "")).startswith(("SH.", "SZ."))
            and not bool(x.get("delisting"))
            and (not str(x.get("listing_date") or "") or str(x.get("listing_date"))[:10] <= today)
        ]
        rows = []
        for start in range(0, len(codes), 400):
            ret, frame = ctx.get_market_snapshot(codes[start:start + 400])
            if ret != RET_OK or frame is None:
                raise RuntimeError(f"Futu get_market_snapshot failed at {start}: {frame}")
            for x in frame.to_dict("records"):
                price = number(x.get("last_price"))
                previous = number(x.get("prev_close_price"))
                if price <= 0 or previous <= 0:
                    continue
                rows.append({
                    "code": str(x.get("code", "")).split(".")[-1],
                    "futuCode": str(x.get("code", "")), "name": str(x.get("name") or ""),
                    "price": price, "change": (price / previous - 1) * 100,
                    "amount": number(x.get("turnover")), "turnover": number(x.get("turnover_rate")),
                    "flow": None, "industry": "—", "updateTime": str(x.get("update_time") or ""),
                })
        return rows
    finally:
        ctx.close()


def futu_plates(kind: str) -> list[dict]:
    from futu import Market, OpenQuoteContext, Plate, RET_OK

    plate_type = Plate.INDUSTRY if kind == "industry" else Plate.CONCEPT
    ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
    try:
        ret, frame = ctx.get_plate_list(Market.SH, plate_type)
        if ret != RET_OK or frame is None:
            raise RuntimeError(f"Futu get_plate_list failed: {kind} {frame}")
        names = {str(x["code"]): str(x["plate_name"]) for x in frame.to_dict("records")}
        codes = list(names)
        rows = []
        pending = [codes[start:start + 400] for start in range(0, len(codes), 400)]
        while pending:
            batch = pending.pop(0)
            ret, snap = ctx.get_market_snapshot(batch)
            if ret != RET_OK or snap is None:
                if len(batch) == 1:
                    continue
                middle = len(batch) // 2
                pending[:0] = [batch[:middle], batch[middle:]]
                continue
            for x in snap.to_dict("records"):
                price = number(x.get("last_price"))
                previous = number(x.get("prev_close_price"))
                if price <= 0 or previous <= 0:
                    continue
                rows.append({
                    "code": str(x.get("code") or ""), "name": names.get(str(x.get("code")), str(x.get("name") or "")),
                    "change": (price / previous - 1) * 100, "flow": None,
                    "up": None, "down": None, "flat": None, "leader": "—", "leaderChange": None,
                    "amount": number(x.get("turnover")),
                })
        return rows
    finally:
        ctx.close()


def futu_index_kline() -> list[dict]:
    from datetime import timedelta
    from futu import AuType, KLType, OpenQuoteContext, RET_OK

    ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
    try:
        end = datetime.now(ZoneInfo("Asia/Shanghai")).date()
        ret, frame, _ = ctx.request_history_kline(
            "SH.000001", start=(end - timedelta(days=240)).isoformat(), end=end.isoformat(),
            ktype=KLType.K_DAY, autype=AuType.NONE, max_count=500,
        )
        if ret != RET_OK or frame is None or len(frame) < 60:
            raise RuntimeError(f"Futu index kline insufficient: {frame}")
        return [
            {"date": str(x.get("time_key"))[:10], "open": number(x.get("open")), "close": number(x.get("close")),
             "high": number(x.get("high")), "low": number(x.get("low")), "volume": number(x.get("volume")),
             "amount": number(x.get("turnover"))}
            for x in frame.to_dict("records")
        ]
    finally:
        ctx.close()


def limit_ratio(stock: dict) -> float:
    code = stock["code"]
    name = stock["name"].upper()
    if "ST" in name:
        return 5.0
    if code.startswith(("300", "301", "688")):
        return 20.0
    if code.startswith(("4", "8", "92")):
        return 30.0
    return 10.0


def is_limit(stock: dict, side: str) -> bool:
    threshold = limit_ratio(stock)
    return stock["change"] >= threshold - 0.12 if side == "up" else stock["change"] <= -threshold + 0.12


def limit_pool(date: str, kind: str) -> list[dict]:
    endpoint = "getTopicZTPool" if kind == "up" else "getTopicDTPool"
    payload = get_json(
        f"https://push2ex.eastmoney.com/{endpoint}",
        {
            "ut": "7eea3edcaed734bea9cbfc24409ed989", "dpt": "wz.ztzt",
            "Pageindex": 0, "pagesize": 1000, "sort": "fbt:asc", "date": date.replace("-", ""),
        },
        referer="https://quote.eastmoney.com/ztb/",
    )
    data = payload.get("data") or {}
    rows = data.get("pool") or []
    return rows if isinstance(rows, list) else []


def index_kline(secid: str) -> list[dict]:
    payload = get_json(
        "https://push2his.eastmoney.com/api/qt/stock/kline/get",
        {
            "secid": secid, "klt": 101, "fqt": 1, "lmt": 130, "end": "20500101",
            "iscca": 1, "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        },
        referer="https://quote.eastmoney.com/",
    )
    rows = ((payload.get("data") or {}).get("klines") or [])
    out = []
    for row in rows:
        f = row.split(",")
        if len(f) >= 7:
            out.append({"date": f[0], "open": number(f[1]), "close": number(f[2]), "high": number(f[3]), "low": number(f[4]), "volume": number(f[5]), "amount": number(f[6])})
    if len(out) < 60:
        raise RuntimeError("index kline coverage below 60 bars")
    return out


def clean_stock(row: dict) -> dict:
    return {
        "code": str(row.get("f12") or ""), "name": str(row.get("f14") or ""),
        "price": number(row.get("f2")), "change": number(row.get("f3")),
        "amount": number(row.get("f6")), "turnover": number(row.get("f8")),
        "flow": number(row.get("f62")), "industry": str(row.get("f100") or "未分类"),
    }


def clean_sector(row: dict) -> dict:
    return {
        "code": str(row.get("f12") or ""), "name": str(row.get("f14") or ""),
        "change": number(row.get("f3")), "flow": number(row.get("f62")),
        "up": int(number(row.get("f104"))), "down": int(number(row.get("f105"))),
        "flat": int(number(row.get("f106"))), "leader": str(row.get("f128") or "—"),
        "leaderChange": number(row.get("f136")),
    }


def bucket(change: float) -> str:
    if change >= 5: return ">=5%"
    if change >= 2: return "2~5%"
    if change > 0: return "0~2%"
    if change == 0: return "平盘"
    if change > -2: return "-2~0%"
    if change > -5: return "-5~-2%"
    return "<=-5%"


def sentiment_score(up: int, down: int, zt: int, dt: int, avg: float) -> int:
    breadth = up / max(1, up + down)
    raw = 45 * breadth + min(30, zt * 0.45) - min(18, dt * 0.7) + 15 + avg * 3
    return int(max(0, min(100, round(raw))))


def build() -> dict:
    indices, data_date = tencent_indices()
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    if now.date().isoformat() == data_date and now.hour < 15:
        raise RuntimeError("latest quote is intraday; refuse to publish")
    stocks = futu_stocks()
    if len(stocks) < 5000:
        raise RuntimeError(f"A-share coverage too low: {len(stocks)}")
    industry = futu_plates("industry")
    concept = futu_plates("concept")
    kline = futu_index_kline()
    if kline[-1]["date"] != data_date:
        raise RuntimeError(f"Futu/Tencent close date mismatch: {kline[-1]['date']} != {data_date}")

    up = sum(x["change"] > 0 for x in stocks)
    down = sum(x["change"] < 0 for x in stocks)
    flat = len(stocks) - up - down
    changes = [x["change"] for x in stocks]
    average = sum(changes) / len(changes)
    dist = Counter(bucket(x) for x in changes)
    order = [">=5%", "2~5%", "0~2%", "平盘", "-2~0%", "-5~-2%", "<=-5%"]
    distribution = [{"bucket": name, "count": dist[name]} for name in order]
    gainers = sorted(stocks, key=lambda x: (x["change"], x["amount"]), reverse=True)[:15]
    losers = sorted(stocks, key=lambda x: (x["change"], -x["amount"]))[:15]
    turnover = sorted(stocks, key=lambda x: x["amount"], reverse=True)[:15]
    inflow: list[dict] = []
    outflow: list[dict] = []
    ind_rise = sorted(industry, key=lambda x: x["change"], reverse=True)[:15]
    ind_fall = sorted(industry, key=lambda x: x["change"])[:15]
    concept_rise = sorted(concept, key=lambda x: x["change"], reverse=True)[:15]
    concept_fall = sorted(concept, key=lambda x: x["change"])[:15]
    ind_inflow: list[dict] = []
    ind_outflow: list[dict] = []

    zt_rows = [x for x in stocks if is_limit(x, "up")]
    dt_rows = [x for x in stocks if is_limit(x, "down")]
    streaks: dict[str, list[dict]] = {"1": [dict(x, sealed=None, sector="—", streak=1) for x in sorted(zt_rows, key=lambda x: x["amount"], reverse=True)]}
    limits = {
        "up": sum(len(v) for v in streaks.values()), "down": len(dt_rows),
        "highestStreak": None,
        "streaks": [{"streak": int(k), "stocks": v} for k, v in sorted(streaks.items(), key=lambda kv: int(kv[0]), reverse=True)],
        "themes": [],
    }
    watch = [x for x in stocks if x["code"] in WATCH_CODES]
    watch.sort(key=lambda x: x["change"], reverse=True)
    score = sentiment_score(up, down, limits["up"], limits["down"], average)

    return {
        "schemaVersion": 1,
        "data_date": data_date,
        "generated_at": now.isoformat(timespec="seconds"),
        "market": {
            "status": "verified_close", "coverage": len(stocks), "up": up, "down": down, "flat": flat,
            "averageChange": round(average, 3), "amount": sum(x["amount"] for x in stocks),
            "mainFlow": None, "sentiment": score, "distribution": distribution,
        },
        "indices": indices,
        "kline": {"name": "上证指数", "bars": kline},
        "rankings": {"gainers": gainers, "losers": losers, "turnover": turnover},
        "sectors": {"industryRise": ind_rise, "industryFall": ind_fall, "conceptRise": concept_rise, "conceptFall": concept_fall},
        "flows": {"stocksIn": inflow, "stocksOut": outflow, "sectorsIn": ind_inflow, "sectorsOut": ind_outflow},
        "limits": limits,
        "watchlist": watch,
        "slowData": {
            "institutions": {"status": "separate_snapshot", "label": "独立快照", "note": "由同交易日 tencent-snapshot.json 提供观察池十大流通股东机构席位与北向季度持仓。"},
            "chips": {"status": "separate_snapshot", "label": "独立快照", "note": "由同交易日 tencent-snapshot.json 提供观察池筹码获利率、平均成本与集中度。"},
        },
        "sources": [
            {"name": "Futu OpenD", "role": "A股全市场快照与覆盖率硬门", "access": "本机只读"},
            {"name": "腾讯财经", "role": "指数收盘与交易日期交叉核验", "access": "公开零密钥"},
            {"name": "Futu OpenD", "role": "行业与概念板块、上证指数K线", "access": "本机只读"},
            {"name": "腾讯自选股", "role": "观察池筹码、十大股东与北向季度持仓", "access": "授权只读；独立快照"},
        ],
        "display": {"amount": compact_amount(sum(x["amount"] for x in stocks)), "mainFlow": "未接入"},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    data = build()
    encoded = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix(args.output.suffix + ".tmp")
    temp.write_text(encoded, encoding="utf-8")
    json.loads(temp.read_text(encoding="utf-8"))
    temp.replace(args.output)
    print(json.dumps({"status": "PASS", "output": str(args.output), "data_date": data["data_date"], "coverage": data["market"]["coverage"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
