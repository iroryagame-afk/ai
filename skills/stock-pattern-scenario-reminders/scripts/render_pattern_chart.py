#!/usr/bin/env python3
"""Render a verified pattern plan to standalone HTML and an optional high-resolution PNG."""

from __future__ import annotations

import argparse
import html
import json
import subprocess
from pathlib import Path
from urllib.parse import quote


COLORS = {
    "history": "#258ff0",
    "neckline": "#ff8a3d",
    "structure": "#7b8794",
    "bullish": "#42c878",
    "range": "#ee67b0",
    "bearish": "#ef5b13",
    "grid": "#e8edf2",
    "text": "#17212b",
    "muted": "#7a8692",
}


def validate_plan(plan: dict) -> None:
    required = ("code", "current", "history", "pattern", "scenarios")
    missing = [key for key in required if key not in plan]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")
    if len(plan["history"]) < 10:
        raise ValueError("history must contain at least 10 points")
    dates = [row["date"] for row in plan["history"]]
    if dates != sorted(dates):
        raise ValueError("history must be chronological")
    scenario_ids = [row["id"] for row in plan["scenarios"]]
    if sorted(scenario_ids) != ["A", "B", "C"]:
        raise ValueError("scenarios must contain A, B and C exactly once")
    allowed_kinds = {"bullish", "range", "bearish"}
    scenario_map = {row["id"]: row for row in plan["scenarios"]}
    for scenario in plan["scenarios"]:
        if scenario.get("kind") not in allowed_kinds:
            raise ValueError(f"invalid scenario kind: {scenario.get('kind')}")
        if len(scenario.get("path", [])) < 3:
            raise ValueError(f"scenario {scenario['id']} path needs at least 3 values")
    if scenario_map["B"].get("kind") != "range":
        raise ValueError("scenario B must be the range / unresolved path")
    if scenario_map["A"].get("kind") not in {"bullish", "bearish"}:
        raise ValueError("scenario A must express the primary bullish or bearish confirmation")
    opposite = "bearish" if scenario_map["A"]["kind"] == "bullish" else "bullish"
    if scenario_map["C"].get("kind") != opposite:
        raise ValueError("scenario C must invalidate A in the opposite direction")
    assessment = plan.get("assessment", {})
    if assessment:
        if assessment.get("quality") not in {"high", "medium", "low", "insufficient"}:
            raise ValueError("assessment.quality must be high/medium/low/insufficient")
        score = assessment.get("score")
        if score is not None and not 0 <= float(score) <= 100:
            raise ValueError("assessment.score must be between 0 and 100")
    overlay = plan.get("timing_overlay", {})
    if overlay and len(str(overlay.get("summary", ""))) > 30:
        raise ValueError("timing_overlay.summary must be <= 30 characters")
    status = str(plan.get("status", ""))
    if "非头肩" in status or "不是" in status:
        raise ValueError("chart status must state the selected pattern only; keep rejected alternatives in assessment")
    reminders = plan.get("reminders", [])
    if len(reminders) > 3:
        raise ValueError("reminders must contain at most 3 entries")
    for reminder in reminders:
        if reminder.get("direction") not in {"PRICE_UP", "PRICE_DOWN"}:
            raise ValueError(f"invalid reminder direction: {reminder}")
        if len(str(reminder.get("note", ""))) > 20:
            raise ValueError(f"Futu note exceeds 20 characters: {reminder['note']}")


def svg_text(x, y, text, *, anchor="start", size=14, weight=400, fill=None) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill or COLORS["text"]}">'
        f"{html.escape(str(text))}</text>"
    )


def render_svg(plan: dict) -> str:
    history = plan["history"]
    scenarios = sorted(plan["scenarios"], key=lambda row: row["id"])
    key_points = plan["pattern"].get("key_points", [])
    decision_zone = plan["pattern"].get("decision_zone") or plan["pattern"].get("neckline", {})
    structure_lines = plan["pattern"].get("structure_lines", [])

    values = [float(row["close"]) for row in history]
    values.extend(float(point["value"]) for point in key_points)
    values.append(float(plan["current"]))
    values.extend(float(value) for scenario in scenarios for value in scenario["path"])
    if decision_zone:
        values.extend([float(decision_zone["low"]), float(decision_zone["high"])])
    values.extend(float(point["value"]) for line in structure_lines for point in line.get("points", []))
    low, high = min(values), max(values)
    padding = max((high - low) * 0.08, abs(high) * 0.015, 0.5)
    y_min, y_max = low - padding, high + padding

    width, height = 1400, 550
    left, history_right, future_right = 80, 920, 1360
    plot_top, plot_bottom = 82, 455

    def x_hist(index: int) -> float:
        return left + index * (history_right - left) / max(len(history) - 1, 1)

    def y_price(value: float) -> float:
        return plot_top + (y_max - value) * (plot_bottom - plot_top) / (y_max - y_min)

    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img">',
        f"<title>{html.escape(plan.get('name') or plan['code'])} technical pattern scenarios</title>",
        '<rect width="1400" height="550" fill="#ffffff"/>',
    ]
    identity = f"{plan['name']}（{plan['code']}）" if plan.get("name") else plan["code"]
    title = f"{identity} · {plan.get('as_of', '')} · {plan['current']:g} {plan.get('currency', '')}".strip()
    pieces.append(svg_text(80, 35, title, size=18, weight=500, fill=COLORS["history"]))
    overlay = plan.get("timing_overlay", {})
    if overlay:
        decision_colors = {
            "execute_small": COLORS["bullish"], "candidate": COLORS["bullish"],
            "hold": COLORS["history"], "reduce": COLORS["bearish"],
            "avoid": COLORS["bearish"], "observe": COLORS["range"],
            "wait_confirmation": COLORS["range"],
        }
        overlay_label = f"执行：{overlay.get('summary', '')}"
        pieces.append(svg_text(1360, 35, overlay_label, anchor="end", size=13, weight=500, fill=decision_colors.get(overlay.get("decision"), COLORS["muted"])))
    assessment = plan.get("assessment", {})
    assessment_text = ""
    if assessment:
        quality_map = {"high": "高", "medium": "中", "low": "低", "insufficient": "证据不足"}
        assessment_text = f" · 结构质量 {quality_map.get(assessment.get('quality'), assessment.get('quality'))}"
        if assessment.get("score") is not None:
            assessment_text += f" {assessment['score']:g}/100（非胜率）"
    pieces.append(svg_text(80, 59, f"{plan.get('status', '')}{assessment_text}  {plan.get('session_label', '')}".strip(), size=14, fill=COLORS["muted"]))

    ticks = 7
    for index in range(ticks):
        value = y_min + index * (y_max - y_min) / (ticks - 1)
        y = y_price(value)
        pieces.append(f'<line x1="{left}" y1="{y:.1f}" x2="{future_right}" y2="{y:.1f}" stroke="{COLORS["grid"]}"/>')
        pieces.append(svg_text(left - 12, y + 5, f"{value:.0f}" if abs(value) >= 20 else f"{value:.1f}", anchor="end", size=12, fill=COLORS["muted"]))

    if decision_zone:
        band_y = y_price(float(decision_zone["high"]))
        band_h = y_price(float(decision_zone["low"])) - band_y
        pieces.append(f'<rect x="{left}" y="{band_y:.1f}" width="{future_right-left}" height="{band_h:.1f}" fill="{COLORS["neckline"]}" opacity="0.16"/>')
        middle = (float(decision_zone["low"]) + float(decision_zone["high"])) / 2
        pieces.append(f'<line x1="{left}" y1="{y_price(middle):.1f}" x2="{future_right}" y2="{y_price(middle):.1f}" stroke="{COLORS["neckline"]}" stroke-width="2" stroke-dasharray="8 5"/>')
        pieces.append(svg_text(future_right - 6, y_price(middle) - 8, decision_zone.get("label", "决策区"), anchor="end", size=13, weight=500))

    history_points = " ".join(f"{x_hist(i):.1f},{y_price(float(row['close'])):.1f}" for i, row in enumerate(history))
    pieces.append(f'<polygon points="{history_points} {history_right:.1f},{plot_bottom:.1f} {left:.1f},{plot_bottom:.1f}" fill="{COLORS["history"]}" opacity="0.08"/>')
    pieces.append(f'<polyline points="{history_points}" fill="none" stroke="{COLORS["history"]}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>')

    date_to_index = {row["date"]: index for index, row in enumerate(history)}
    line_colors = {"support": COLORS["bullish"], "resistance": COLORS["bearish"], "neutral": COLORS["structure"]}
    for line in structure_lines:
        points = []
        for point in line.get("points", []):
            if point.get("date") in date_to_index:
                points.append((x_hist(date_to_index[point["date"]]), y_price(float(point["value"]))))
        if len(points) < 2:
            continue
        color = line_colors.get(line.get("style", "neutral"), COLORS["structure"])
        pieces.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in points)}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="7 5"/>')
        pieces.append(svg_text(points[-1][0] - 4, points[-1][1] - 8, line.get("label", "结构线"), anchor="end", size=11, fill=color))
    structure_points = []
    for point in key_points:
        if point["date"] not in date_to_index:
            continue
        px, py = x_hist(date_to_index[point["date"]]), y_price(float(point["value"]))
        structure_points.append((px, py))
    if structure_points:
        pieces.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in structure_points)}" fill="none" stroke="{COLORS["structure"]}" stroke-width="2" stroke-dasharray="5 5"/>')
    for point in key_points:
        if point["date"] not in date_to_index:
            continue
        px, py = x_hist(date_to_index[point["date"]]), y_price(float(point["value"]))
        label_above = float(point["value"]) > (y_min + y_max) / 2
        label_y = py - 16 if label_above else py + 25
        value_y = label_y - 16 if label_above else label_y + 16
        pieces.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="6" fill="#ffffff" stroke="{COLORS["history"]}" stroke-width="3"/>')
        pieces.append(svg_text(px, label_y, point["label"], anchor="middle", size=13, weight=500))
        pieces.append(svg_text(px, value_y, f"{float(point['value']):g}", anchor="middle", size=12, fill=COLORS["muted"]))

    current_y = y_price(float(plan["current"]))
    pieces.append(f'<circle cx="{history_right:.1f}" cy="{current_y:.1f}" r="7" fill="{COLORS["history"]}" stroke="#ffffff" stroke-width="3"/>')
    pieces.append(svg_text(history_right - 12, current_y - 14, f"当前 {float(plan['current']):g}", anchor="end", size=14, weight=500))
    pieces.append(f'<line x1="{history_right+18}" y1="{plot_top}" x2="{history_right+18}" y2="{plot_bottom}" stroke="{COLORS["grid"]}" stroke-width="2" stroke-dasharray="2 7"/>')
    pieces.append(svg_text(history_right + 30, plot_top + 16, "未来路径", size=12, fill=COLORS["muted"]))

    scenario_label_positions = {"A": 125, "B": 300, "C": 405}
    for scenario in scenarios:
        path = [float(value) for value in scenario["path"]]
        path[0] = float(plan["current"])
        points = []
        for index, value in enumerate(path):
            px = history_right + index * (future_right - history_right) / max(len(path) - 1, 1)
            points.append((px, y_price(value)))
        color = COLORS[scenario["kind"]]
        pieces.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in points)}" fill="none" stroke="{color}" stroke-width="4" stroke-dasharray="9 6" stroke-linejoin="round"/>')
        label_y = scenario_label_positions[scenario["id"]]
        pieces.append(svg_text(1015, label_y, f"{scenario['id']} {scenario['label']}", size=14, weight=500))
        pieces.append(svg_text(1015, label_y + 20, scenario.get("trigger", ""), size=12, fill=COLORS["muted"]))
        pieces.append(svg_text(1015, label_y + 40, scenario.get("targets_label", ""), size=12, weight=500))

    tick_indices = sorted(set([0, len(history) // 4, len(history) // 2, len(history) * 3 // 4, len(history) - 1]))
    for index in tick_indices:
        pieces.append(svg_text(x_hist(index), 482, history[index]["date"][5:], anchor="middle", size=12, fill=COLORS["muted"]))
    pieces.append(svg_text((history_right + future_right) / 2, 482, "后续情景（非时间预测）", anchor="middle", size=12, fill=COLORS["muted"]))

    legend = [("已发生走势", COLORS["history"])] + [
        (f"{scenario['id']} {scenario['label']}", COLORS[scenario["kind"]]) for scenario in scenarios
    ]
    lx = 360
    for label, color in legend:
        pieces.append(f'<line x1="{lx}" y1="522" x2="{lx+28}" y2="522" stroke="{color}" stroke-width="4"/>')
        pieces.append(svg_text(lx + 38, 527, label, size=12, fill=COLORS["muted"]))
        lx += 190
    pieces.append("</svg>")
    return "\n".join(pieces)


def standalone_html(svg: str) -> str:
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN"><head><meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width,initial-scale=1">',
            "<style>html,body{margin:0;background:#fff}body{width:1400px;height:550px;overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif}svg{display:block;width:1400px;height:550px}</style>",
            "</head><body>",
            svg,
            "</body></html>",
        ]
    )


def render_png(html_path: Path, png_path: Path, chrome: Path) -> None:
    if not chrome.exists():
        raise FileNotFoundError(f"Chrome not found: {chrome}")
    command = [
        str(chrome),
        "--headless",
        "--hide-scrollbars",
        "--disable-gpu",
        "--no-sandbox",
        "--force-device-scale-factor=2",
        "--window-size=1400,550",
        f"--screenshot={png_path.resolve()}",
        f"file://{quote(str(html_path.resolve()))}",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=60)
    if completed.returncode != 0 or not png_path.exists():
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(f"Chrome PNG render failed; rerun with host permission. {detail}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--png", action="store_true")
    parser.add_argument("--chrome", type=Path, default=Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"))
    args = parser.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    validate_plan(plan)
    ticker = plan["code"].split(".")[-1].lower()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    html_path = args.output_dir / f"{ticker}-scenarios.html"
    png_path = args.output_dir / f"{ticker}-scenarios.png"
    html_path.write_text(standalone_html(render_svg(plan)), encoding="utf-8")
    if args.png:
        render_png(html_path, png_path, args.chrome)
    result = {"html": str(html_path), "png": str(png_path) if args.png else None}
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
