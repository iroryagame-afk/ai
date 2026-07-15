#!/usr/bin/env python3
"""Analyze historical drawdown clusters with ATR and peer validation."""

from __future__ import annotations

import argparse
import json
import math
import os
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd


DEFAULT_RATIOS = [0.382, 0.500, 0.618, 0.786]
DEFAULT_THRESHOLDS = [0.08, 0.12, 0.15, 0.20]
RECOVERY_RATIOS = [0.786, 0.618, 0.500, 0.382, 0.236, 0.000]
EXTENSION_RATIOS = [0.618, 1.000, 1.272, 1.618]


def add_atr(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy().sort_values("time_key").reset_index(drop=True)
    prev = data["close"].astype(float).shift(1)
    tr = pd.concat(
        [
            data["high"].astype(float) - data["low"].astype(float),
            (data["high"].astype(float) - prev).abs(),
            (data["low"].astype(float) - prev).abs(),
        ],
        axis=1,
    ).max(axis=1)
    data["atr14"] = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    return data


def fetch_history(ctx, code: str, start: str, end: str) -> pd.DataFrame:
    from futu import AuType, KLType, RET_OK

    frames = []
    key = None
    while True:
        ret, frame, key = ctx.request_history_kline(
            code,
            start=start,
            end=end,
            ktype=KLType.K_DAY,
            autype=AuType.QFQ,
            max_count=1000,
            page_req_key=key,
        )
        if ret != RET_OK:
            raise RuntimeError(f"{code}: {frame}")
        if frame is not None and len(frame):
            frames.append(frame)
        if key is None:
            break
    if not frames:
        raise RuntimeError(f"{code}: empty history")
    merged = pd.concat(frames, ignore_index=True).drop_duplicates("time_key")
    return add_atr(merged)


def zigzag(prices: list[float], threshold: float) -> list[tuple[str, int, bool]]:
    if len(prices) < 2:
        return []
    direction = 0
    high_i = low_i = 0
    pivots: list[tuple[str, int, bool]] = []
    for i in range(1, len(prices)):
        price = prices[i]
        if price > prices[high_i]:
            high_i = i
        if price < prices[low_i]:
            low_i = i
        if direction == 0:
            if price <= prices[high_i] * (1 - threshold):
                pivots.append(("peak", high_i, True))
                direction = -1
                low_i = i
            elif price >= prices[low_i] * (1 + threshold):
                pivots.append(("trough", low_i, True))
                direction = 1
                high_i = i
        elif direction == 1 and price <= prices[high_i] * (1 - threshold):
            pivots.append(("peak", high_i, True))
            direction = -1
            low_i = i
        elif direction == -1 and price >= prices[low_i] * (1 + threshold):
            pivots.append(("trough", low_i, True))
            direction = 1
            high_i = i
    final_i = high_i if direction == 1 else low_i
    final_kind = "peak" if direction == 1 else "trough"
    if not pivots or pivots[-1][1] != final_i:
        pivots.append((final_kind, final_i, False))
    return pivots


def classify_depth(depth: float, ratios: list[float]) -> str:
    if depth > 1.0:
        return ">100%"
    if depth >= 0.90:
        return "100%"
    nearest = min(ratios, key=lambda ratio: abs(depth - ratio))
    return f"{nearest:.3f}"


def extract_cycles(
    frame: pd.DataFrame,
    threshold: float,
    ratios: list[float],
    half_life: float,
) -> list[dict]:
    prices = frame["close"].astype(float).tolist()
    pivots = [pivot for pivot in zigzag(prices, threshold) if pivot[2]]
    cycles = []
    for left, middle, right in zip(pivots, pivots[1:], pivots[2:]):
        if (left[0], middle[0], right[0]) != ("trough", "peak", "trough"):
            continue
        low_i, peak_i, end_i = left[1], middle[1], right[1]
        low, peak, end_low = prices[low_i], prices[peak_i], prices[end_i]
        impulse = peak - low
        atr_peak = float(frame.iloc[peak_i]["atr14"])
        if impulse <= 0 or not math.isfinite(atr_peak) or atr_peak <= 0:
            continue
        depth = (peak - end_low) / impulse
        age = max(0, len(frame) - 1 - end_i)
        weight = 0.5 ** (age / half_life)
        cycles.append(
            {
                "start_date": str(frame.iloc[low_i]["time_key"])[:10],
                "peak_date": str(frame.iloc[peak_i]["time_key"])[:10],
                "end_date": str(frame.iloc[end_i]["time_key"])[:10],
                "retracement": depth,
                "bucket": classify_depth(depth, ratios),
                "drawdown_atr": (peak - end_low) / atr_peak,
                "recency_weight": weight,
            }
        )
    return cycles


def summarize(cycles: list[dict], ratios: list[float]) -> dict:
    support = {f"{ratio:.3f}": 0.0 for ratio in ratios}
    risk = {"100%": 0.0, ">100%": 0.0}
    for cycle in cycles:
        bucket = cycle["bucket"]
        if bucket in support:
            support[bucket] += cycle["recency_weight"]
        elif bucket in risk:
            risk[bucket] += cycle["recency_weight"]
    support_total = sum(support.values()) or 1.0
    all_total = support_total + sum(risk.values())
    return {
        "sample_count": len(cycles),
        "support_scores": {key: value / support_total for key, value in support.items()},
        "risk_shares": {key: value / all_total for key, value in risk.items()},
        "median_drawdown_atr": float(pd.Series([row["drawdown_atr"] for row in cycles]).median()) if cycles else None,
    }


def robust_summary(
    frame: pd.DataFrame,
    thresholds: list[float],
    ratios: list[float],
    half_life: float,
) -> dict:
    combined = {f"{ratio:.3f}": 0.0 for ratio in ratios}
    per_threshold = {}
    for threshold in thresholds:
        cycles = extract_cycles(frame, threshold, ratios, half_life)
        summary = summarize(cycles, ratios)
        per_threshold[f"{threshold:.2f}"] = summary
        for key, value in summary["support_scores"].items():
            combined[key] += value / len(thresholds)
    return {"scores": combined, "per_threshold": per_threshold}


def active_anchor(frame: pd.DataFrame, threshold: float = 0.12) -> dict:
    prices = frame["close"].astype(float).tolist()
    pivots = zigzag(prices, threshold)
    peak_positions = [i for i, pivot in enumerate(pivots) if pivot[0] == "peak"]
    if not peak_positions:
        start = max(0, len(prices) - 252)
        low_i = min(range(start, len(prices)), key=lambda i: prices[i])
        peak_i = max(range(low_i, len(prices)), key=lambda i: prices[i])
        confirmed = False
    else:
        p = peak_positions[-1]
        peak_i = pivots[p][1]
        confirmed = pivots[p][2]
        troughs = [pivot for pivot in pivots[:p] if pivot[0] == "trough" and pivot[1] < peak_i]
        start = max(0, peak_i - 252)
        low_i = troughs[-1][1] if troughs else min(range(start, peak_i + 1), key=lambda i: prices[i])
        active_peak_i = max(range(low_i, len(prices)), key=lambda i: prices[i])
        if prices[active_peak_i] > prices[peak_i]:
            peak_i = active_peak_i
            confirmed = False
    if peak_i <= low_i or prices[peak_i] <= prices[low_i]:
        raise RuntimeError("invalid active anchor")
    return {
        "low_date": str(frame.iloc[low_i]["time_key"])[:10],
        "low": prices[low_i],
        "peak_date": str(frame.iloc[peak_i]["time_key"])[:10],
        "peak": prices[peak_i],
        "peak_confirmed": confirmed,
    }


def level(anchor: dict, ratio: float) -> float:
    return anchor["peak"] - ratio * (anchor["peak"] - anchor["low"])


def repair_ladder(anchor: dict, rebound_low: float) -> list[dict]:
    """Return the next shallower retracement levels above a candidate C low."""
    impulse = float(anchor["peak"]) - float(anchor["low"])
    if impulse <= 0:
        raise ValueError("anchor peak must be above anchor low")
    tolerance = max(0.01, impulse * 0.001)
    rows = []
    for ratio in RECOVERY_RATIOS:
        value = level(anchor, ratio)
        if value > float(rebound_low) + tolerance:
            rows.append({"ratio": ratio, "value": value})
    return sorted(rows, key=lambda row: row["value"])


def extension_ladder(anchor: dict, rebound_low: float) -> list[dict]:
    """Project ABC extensions from confirmed C using the prior AB impulse."""
    impulse = float(anchor["peak"]) - float(anchor["low"])
    if impulse <= 0:
        raise ValueError("anchor peak must be above anchor low")
    if not float(anchor["low"]) < float(rebound_low) < float(anchor["peak"]):
        raise ValueError("confirmed rebound low C must be between anchor low A and peak B")
    return [{"ratio": ratio, "value": float(rebound_low) + ratio * impulse} for ratio in EXTENSION_RATIOS]


def normalize_weights(peers: dict[str, float]) -> dict[str, float]:
    total = sum(float(value) for value in peers.values())
    if total <= 0:
        return {}
    return {code: float(value) / total for code, value in peers.items()}


def combine_scores(
    own: dict[str, float],
    peer_summaries: dict[str, dict],
    peer_weights: dict[str, float],
    target_weight: float,
) -> dict[str, float]:
    if not peer_summaries:
        return own.copy()
    result = {key: target_weight * value for key, value in own.items()}
    for code, summary in peer_summaries.items():
        for key, value in summary["scores"].items():
            result[key] += (1 - target_weight) * peer_weights[code] * value
    total = sum(result.values()) or 1.0
    return {key: value / total for key, value in result.items()}


def ranked_result(scores: dict[str, float], tie_threshold: float) -> dict:
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    tied = len(ranked) > 1 and abs(ranked[0][1] - ranked[1][1]) < tie_threshold
    return {
        "ranked": [{"ratio": float(key), "score": value} for key, value in ranked],
        "primary_ratio": float(ranked[0][0]),
        "secondary_ratio": float(ranked[1][0]),
        "tied_core_zone": tied,
    }


def analyze(config: dict, ctx) -> dict:
    targets = list(config["targets"])
    peers = normalize_weights(config.get("peers", {}))
    codes = list(dict.fromkeys(targets + list(peers)))
    ratios = [float(value) for value in config.get("candidate_ratios", DEFAULT_RATIOS)]
    if 0.718 in ratios and not config.get("allow_experimental_718", False):
        raise ValueError("0.718 is experimental; set allow_experimental_718=true explicitly")
    thresholds = [float(value) for value in config.get("thresholds", DEFAULT_THRESHOLDS)]
    target_weight = float(config.get("target_weight", 0.60))
    tie_threshold = float(config.get("tie_threshold", 0.01))
    half_life = float(config.get("recency_half_life_bars", 756))
    start = str(config.get("start", "2010-01-01"))
    end = str(config.get("end") or (date.today() - timedelta(days=1)).isoformat())

    frames = {code: fetch_history(ctx, code, start, end) for code in codes}
    summaries = {code: robust_summary(frame, thresholds, ratios, half_life) for code, frame in frames.items()}
    result = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "data_status": "VERIFIED_FUTU_OPEND",
        "completed_bar_end": end,
        "config": config,
        "targets": {},
        "peers": {},
    }
    for code in peers:
        frame = frames[code]
        result["peers"][code] = {
            "weight": peers[code],
            "bars": len(frame),
            "last_bar": str(frame.iloc[-1]["time_key"])[:10],
            "atr_pct": float(frame.iloc[-1]["atr14"] / frame.iloc[-1]["close"]),
            "summary": summaries[code],
        }
    peer_summaries = {code: summaries[code] for code in peers}
    for code in targets:
        frame = frames[code]
        anchor = active_anchor(frame)
        final_scores = combine_scores(summaries[code]["scores"], peer_summaries, peers, target_weight)
        ranking = ranked_result(final_scores, tie_threshold)
        levels = {f"{ratio:.3f}": round(level(anchor, ratio), 4) for ratio in ratios}
        levels["1.000"] = round(anchor["low"], 4)
        recovery_levels = {f"{ratio:.3f}": round(level(anchor, ratio), 4) for ratio in RECOVERY_RATIOS}
        result["targets"][code] = {
            "bars": len(frame),
            "last_bar": str(frame.iloc[-1]["time_key"])[:10],
            "latest_close": float(frame.iloc[-1]["close"]),
            "atr14": float(frame.iloc[-1]["atr14"]),
            "atr_pct": float(frame.iloc[-1]["atr14"] / frame.iloc[-1]["close"]),
            "sample_count_12": summaries[code]["per_threshold"].get("0.12", {}).get("sample_count", 0),
            "sample_warning": len(frame) < 250 or summaries[code]["per_threshold"].get("0.12", {}).get("sample_count", 0) < 10,
            "anchor": anchor,
            "own_summary": summaries[code],
            "final_scores": final_scores,
            "ranking": ranking,
            "levels": levels,
            "recovery_levels": recovery_levels,
            "extension_requires_confirmed_c": True,
        }
    return result


def main() -> int:
    from futu import OpenQuoteContext

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=11111)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    ctx = OpenQuoteContext(host=args.host, port=args.port)
    try:
        result = analyze(config, ctx)
    finally:
        ctx.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "result": result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
