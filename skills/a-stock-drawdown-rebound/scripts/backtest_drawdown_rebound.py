#!/usr/bin/env python3
"""Describe A-share drawdown/rebound cycles from Futu OpenD daily bars."""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd


SKILL_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = SKILL_ROOT.parents[2]
ROOT = WORKSPACE_ROOT
os.environ["HOME"] = str(ROOT / ".runtime" / "futu_home")


@dataclass(frozen=True)
class Pivot:
    kind: str
    index: int
    date: str
    price: float
    confirmed: bool = True


def fetch_history(code: str, start: str, end: str) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    from futu import AuType, KLType, OpenQuoteContext, RET_OK

    ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
    try:
        series = {}
        for label, autype in (("qfq", AuType.QFQ), ("hfq", AuType.HFQ)):
            frames = []
            key = None
            while True:
                ret, frame, key = ctx.request_history_kline(
                    code,
                    start=start,
                    end=end,
                    ktype=KLType.K_DAY,
                    autype=autype,
                    max_count=1000,
                    page_req_key=key,
                )
                if ret != RET_OK:
                    raise RuntimeError(str(frame))
                if frame is not None and len(frame):
                    frames.append(frame)
                if key is None:
                    break
            if not frames:
                raise RuntimeError(f"empty {label} history")
            series[label] = pd.concat(frames, ignore_index=True).drop_duplicates("time_key").sort_values("time_key")
        ret, snapshot = ctx.get_market_snapshot([code])
        if ret != RET_OK:
            raise RuntimeError(str(snapshot))
        snap = snapshot.iloc[0].to_dict()
    finally:
        ctx.close()
    qfq = series["qfq"]
    hfq = series["hfq"]
    common_dates = set(qfq["time_key"].astype(str)) & set(hfq["time_key"].astype(str))
    qfq = qfq[qfq["time_key"].astype(str).isin(common_dates)].copy()
    hfq = hfq[hfq["time_key"].astype(str).isin(common_dates)].copy()
    qfq = qfq[qfq["close"].astype(float) > 0].sort_values("time_key")
    hfq = hfq[hfq["close"].astype(float) > 0].sort_values("time_key")
    valid_dates = set(qfq["time_key"].astype(str)) & set(hfq["time_key"].astype(str))
    qfq = qfq[qfq["time_key"].astype(str).isin(valid_dates)].sort_values("time_key").reset_index(drop=True)
    hfq = hfq[hfq["time_key"].astype(str).isin(valid_dates)].sort_values("time_key").reset_index(drop=True)
    return qfq, hfq, {key: (None if pd.isna(value) else value) for key, value in snap.items()}


def save_cache(qfq: pd.DataFrame, hfq: pd.DataFrame, snapshot: dict, path: Path) -> None:
    fields = ["time_key", "open", "high", "low", "close", "volume", "turnover", "change_rate"]
    fields = [field for field in fields if field in qfq.columns and field in hfq.columns]
    def rows(frame: pd.DataFrame) -> list[dict]:
        return frame[fields].where(pd.notna(frame[fields]), None).to_dict(orient="records")
    payload = {
        "source": "Futu OpenD request_history_kline K_DAY QFQ+HFQ",
        "snapshot": snapshot,
        "bars_qfq": rows(qfq),
        "bars_hfq": rows(hfq),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def load_cache(path: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return pd.DataFrame(payload["bars_qfq"]), pd.DataFrame(payload["bars_hfq"]), payload.get("snapshot", {})


def zigzag(dates: list[str], prices: list[float], threshold: float) -> list[Pivot]:
    if len(prices) < 2:
        return []
    direction = 0
    high_i = low_i = 0
    pivots: list[Pivot] = []
    for i in range(1, len(prices)):
        price = prices[i]
        if price > prices[high_i]:
            high_i = i
        if price < prices[low_i]:
            low_i = i
        if direction == 0:
            if price <= prices[high_i] * (1 - threshold):
                pivots.append(Pivot("peak", high_i, dates[high_i], prices[high_i]))
                direction = -1
                low_i = i
            elif price >= prices[low_i] * (1 + threshold):
                pivots.append(Pivot("trough", low_i, dates[low_i], prices[low_i]))
                direction = 1
                high_i = i
        elif direction == 1:
            if price <= prices[high_i] * (1 - threshold):
                pivots.append(Pivot("peak", high_i, dates[high_i], prices[high_i]))
                direction = -1
                low_i = i
        else:
            if price >= prices[low_i] * (1 + threshold):
                pivots.append(Pivot("trough", low_i, dates[low_i], prices[low_i]))
                direction = 1
                high_i = i
    final_i = high_i if direction == 1 else low_i
    final_kind = "peak" if direction == 1 else "trough"
    final = Pivot(final_kind, final_i, dates[final_i], prices[final_i], confirmed=False)
    if not pivots or pivots[-1].index != final.index:
        pivots.append(final)
    return pivots


def trading_days(start_idx: int, end_idx: int) -> int:
    return max(0, end_idx - start_idx)


def build_episodes(
    pivots: list[Pivot], dates: list[str], prices: list[float], display_prices: list[float]
) -> list[dict]:
    episodes = []
    for i, peak in enumerate(pivots):
        if peak.kind != "peak" or i + 1 >= len(pivots) or pivots[i + 1].kind != "trough":
            continue
        trough = pivots[i + 1]
        next_peak = pivots[i + 2] if i + 2 < len(pivots) and pivots[i + 2].kind == "peak" else None
        rebound_end_idx = next_peak.index if next_peak else len(prices) - 1
        rebound_end_price = next_peak.price if next_peak else prices[-1]
        drawdown = trough.price / peak.price - 1
        rebound = rebound_end_price / trough.price - 1
        recovery_ratio = (rebound_end_price - trough.price) / (peak.price - trough.price) if peak.price > trough.price else 0
        recovered_idx = None
        for idx in range(trough.index + 1, rebound_end_idx + 1):
            if prices[idx] >= peak.price:
                recovered_idx = idx
                break
        episodes.append({
            "peak_date": peak.date,
            "peak_price_qfq": display_prices[peak.index],
            "trough_date": trough.date,
            "trough_price_qfq": display_prices[trough.index],
            "drawdown_pct": drawdown,
            "drawdown_days": trading_days(peak.index, trough.index),
            "rebound_end_date": dates[rebound_end_idx],
            "rebound_end_price_qfq": display_prices[rebound_end_idx],
            "rebound_pct": rebound,
            "recovery_ratio": recovery_ratio,
            "recovered_previous_peak": recovered_idx is not None,
            "recovery_date": dates[recovered_idx] if recovered_idx is not None else None,
            "rebound_days": trading_days(trough.index, rebound_end_idx),
            "status": "complete" if next_peak and next_peak.confirmed else "ongoing",
        })
    return episodes


def summary(episodes: list[dict]) -> dict:
    if not episodes:
        return {}
    dds = [item["drawdown_pct"] for item in episodes]
    rebounds = [item["rebound_pct"] for item in episodes]
    ratios = [item["recovery_ratio"] for item in episodes]
    return {
        "cycles": len(episodes),
        "median_drawdown_pct": statistics.median(dds),
        "average_drawdown_pct": statistics.fmean(dds),
        "worst_drawdown_pct": min(dds),
        "median_rebound_pct": statistics.median(rebounds),
        "average_rebound_pct": statistics.fmean(rebounds),
        "median_recovery_ratio": statistics.median(ratios),
        "full_recovery_rate": sum(item["recovered_previous_peak"] for item in episodes) / len(episodes),
        "median_drawdown_days": statistics.median(item["drawdown_days"] for item in episodes),
        "median_rebound_days": statistics.median(item["rebound_days"] for item in episodes),
    }


def occupancy_zones(frame: pd.DataFrame, years: int = 5, bin_width: float = 1.0, top_bins: int = 8) -> list[dict]:
    last_date = datetime.strptime(str(frame.iloc[-1]["time_key"])[:10], "%Y-%m-%d")
    cutoff = last_date - timedelta(days=365 * years)
    recent = frame[pd.to_datetime(frame["time_key"]) >= cutoff].copy()
    closes = [float(value) for value in recent["close"].tolist() if float(value) > 0]
    bins = Counter(math.floor(value / bin_width) for value in closes)
    selected = sorted(key for key, _ in bins.most_common(top_bins))
    groups: list[list[int]] = []
    for key in selected:
        if not groups or key != groups[-1][-1] + 1:
            groups.append([key])
        else:
            groups[-1].append(key)
    total = len(closes)
    zones = []
    for group in groups:
        count = sum(bins[key] for key in group)
        zones.append({
            "low": group[0] * bin_width,
            "high": (group[-1] + 1) * bin_width,
            "trading_days": count,
            "share": count / total if total else 0,
        })
    return sorted(zones, key=lambda item: item["trading_days"], reverse=True)


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def render_markdown(result: dict) -> str:
    lines = [
        f"# {result['name']}（{result['code']}）回撤与反弹回测",
        "",
        f"数据：Futu OpenD 日线，{result['date_range']['start']} 至 {result['date_range']['end']}；未完成的盘中日K已排除。",
        f"主要周期阈值：{result['primary_threshold']:.0%}；反弹修复比例 =（反弹终点价－低点）/（前高－低点）。",
        "",
        "## 主要回撤周期",
        "",
        "| 前高日 | 低点日 | 回撤 | 下跌日数 | 反弹终点 | 反弹 | 修复比例 | 状态 |",
        "|---|---|---:|---:|---|---:|---:|---|",
    ]
    for item in result["primary_episodes"]:
        lines.append(
            f"| {item['peak_date']} | {item['trough_date']} | {pct(item['drawdown_pct'])} | {item['drawdown_days']} | "
            f"{item['rebound_end_date']} | {pct(item['rebound_pct'])} | {pct(item['recovery_ratio'])} | {item['status']} |"
        )
    lines.extend(["", "## 最近五年价格停留密集区", "", "| 前复权区间 | 交易日 | 占比 |", "|---|---:|---:|"])
    for zone in result["occupancy_zones"]:
        lines.append(f"| {zone['low']:.1f}–{zone['high']:.1f} 元 | {zone['trading_days']} | {pct(zone['share'])} |")
    lines.extend(["", "> 历史回测只用于描述价格行为，不代表未来收益或买卖保证。", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", required=True, help="Futu A-share code, e.g. SH.600900 or SZ.300308")
    parser.add_argument("--name", help="Optional display name; snapshot name is used by default")
    parser.add_argument("--start", default="2003-01-01")
    parser.add_argument("--end", default=date.today().isoformat())
    parser.add_argument("--technical-start", default="2015-01-01")
    parser.add_argument("--threshold", type=float, default=0.08)
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if not 0.02 <= args.threshold <= 0.30:
        parser.error("--threshold must be between 0.02 and 0.30")
    ticker = args.code.split(".")[-1].lower()
    if args.output_dir is None:
        args.output_dir = ROOT / "outputs" / "a_stock_drawdown_rebound" / ticker
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cache_path = args.output_dir / "history_cache.json"
    if args.fetch or not cache_path.exists():
        qfq, hfq, snapshot = fetch_history(args.code, args.start, args.end)
        save_cache(qfq, hfq, snapshot, cache_path)
    else:
        qfq, hfq, snapshot = load_cache(cache_path)
    qfq = qfq.sort_values("time_key").copy()
    hfq = hfq.sort_values("time_key").copy()
    update_time = str(snapshot.get("update_time") or "")
    if update_time[:10] == date.today().isoformat() and update_time[11:19] < "15:00:00":
        qfq = qfq[qfq["time_key"].astype(str).str[:10] < date.today().isoformat()].copy()
        hfq = hfq[hfq["time_key"].astype(str).str[:10] < date.today().isoformat()].copy()
    dates = [str(value)[:10] for value in hfq["time_key"].tolist()]
    prices = [float(value) for value in hfq["close"].tolist()]
    display_prices = [float(value) for value in qfq["close"].tolist()]
    thresholds = [0.05, 0.08, 0.12]
    episodes_by_threshold = {}
    summaries = {}
    for threshold in thresholds:
        pivots = zigzag(dates, prices, threshold)
        episodes = build_episodes(pivots, dates, prices, display_prices)
        episodes_by_threshold[f"{threshold:.0%}"] = episodes
        summaries[f"{threshold:.0%}"] = summary(episodes)
    modern_qfq = qfq[qfq["time_key"].astype(str).str[:10] >= args.technical_start].copy()
    if len(modern_qfq) < 60:
        raise RuntimeError("fewer than 60 completed daily bars in the technical window")
    modern_dates = [str(value)[:10] for value in modern_qfq["time_key"].tolist()]
    modern_prices = [float(value) for value in modern_qfq["close"].tolist()]
    modern_pivots = zigzag(modern_dates, modern_prices, args.threshold)
    primary = build_episodes(modern_pivots, modern_dates, modern_prices, modern_prices)
    result = {
        "code": args.code,
        "name": args.name or snapshot.get("name", args.code),
        "data_source": "Futu OpenD K_DAY; HFQ for returns, QFQ for displayed price zones",
        "date_range": {"start": dates[0], "end": dates[-1], "bars": len(dates)},
        "latest_snapshot": snapshot,
        "primary_threshold": args.threshold,
        "technical_start": args.technical_start,
        "method": {
            "pivot": "close-price ZigZag",
            "recovery_ratio": "(rebound_end - trough) / (peak - trough)",
            "note": "2015+ user-facing cycles use QFQ technical prices; full-history sensitivity uses HFQ total-return ratios to avoid cash-dividend artifacts. Endpoints are confirmed with hindsight.",
        },
        "sensitivity": summaries,
        "primary_summary": summary(primary),
        "primary_episodes": primary,
        "occupancy_zones": occupancy_zones(qfq, years=5, bin_width=1.0, top_bins=8),
    }
    json_path = args.output_dir / "latest_backtest.json"
    md_path = args.output_dir / "latest_backtest.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    md_path.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps({
        "name": result["name"],
        "date_range": result["date_range"],
        "sensitivity": result["sensitivity"],
        "primary_episodes": result["primary_episodes"],
        "occupancy_zones": result["occupancy_zones"],
        "json": str(json_path),
        "markdown": str(md_path),
    }, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
