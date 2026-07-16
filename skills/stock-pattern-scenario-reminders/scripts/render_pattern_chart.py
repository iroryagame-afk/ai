#!/usr/bin/env python3
"""Render a verified pattern plan to standalone HTML and an optional high-resolution PNG."""

from __future__ import annotations

import argparse
import html
import json
import subprocess
import unicodedata
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

TEXT_COLORS = {
    "history": "#1269b5",
    "neckline": "#a94c00",
    "bullish": "#187c4d",
    "range": "#9c2f70",
    "bearish": "#ad3d08",
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


def svg_text(x, y, text, *, anchor="start", size=14, weight=400, fill=None, halo=False) -> str:
    halo_attrs = ' stroke="#ffffff" stroke-width="4" paint-order="stroke" stroke-linejoin="round"' if halo else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill or COLORS["text"]}"{halo_attrs}>'
        f"{html.escape(str(text))}</text>"
    )


def text_units(text: str) -> float:
    """Approximate rendered width: CJK counts as 1em, Latin/digits as 0.55em."""
    units = 0.0
    for char in str(text):
        units += 1.0 if unicodedata.east_asian_width(char) in {"W", "F", "A"} else 0.55
    return units


def wrap_text(text: str, *, max_units: float = 16.5, max_lines: int = 2) -> list[str]:
    """Wrap compact chart labels without splitting them into an unrelated fixed panel."""
    source = str(text).strip()
    if not source:
        return []
    lines: list[str] = []
    current = ""
    current_units = 0.0
    index = 0
    while index < len(source):
        char = source[index]
        char_units = text_units(char)
        if current and current_units + char_units > max_units:
            lines.append(current.rstrip())
            current = ""
            current_units = 0.0
            if len(lines) == max_lines:
                remainder = source[index:]
                if remainder:
                    last = lines[-1]
                    while last and text_units(last + "…") > max_units:
                        last = last[:-1]
                    lines[-1] = last.rstrip() + "…"
                return lines
        current += char
        current_units += char_units
        index += 1
    if current:
        lines.append(current.rstrip())
    return lines[:max_lines]


def resolve_label_tops(blocks: list[dict], *, top: float, bottom: float, gap: float = 8) -> dict[str, float]:
    """Place variable-height scenario blocks near path endpoints without collisions."""
    ordered = sorted(blocks, key=lambda row: (float(row["desired_center"]), row["id"]))
    available = bottom - top
    required = sum(float(row["height"]) for row in ordered) + gap * max(len(ordered) - 1, 0)
    if required > available:
        raise ValueError("scenario labels exceed the available future-label track")

    placed = []
    cursor = top
    for row in ordered:
        height = float(row["height"])
        desired_top = float(row["desired_center"]) - height / 2
        actual_top = max(cursor, min(desired_top, bottom - height))
        placed.append({"id": row["id"], "top": actual_top, "height": height})
        cursor = actual_top + height + gap

    overflow = placed[-1]["top"] + placed[-1]["height"] - bottom if placed else 0
    if overflow > 0:
        for row in placed:
            row["top"] -= overflow
    if placed and placed[0]["top"] < top:
        shift = top - placed[0]["top"]
        for row in placed:
            row["top"] += shift
    return {row["id"]: row["top"] for row in placed}


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
        pieces.append(svg_text(left + 8, y_price(middle) - 8, decision_zone.get("label", "决策区"), size=13, weight=500, fill=TEXT_COLORS["neckline"], halo=True))

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

    future_path_right = 1120
    label_left = 1150
    label_right = 1356
    scenario_draws = []
    for scenario in scenarios:
        path = [float(value) for value in scenario["path"]]
        path[0] = float(plan["current"])
        points = []
        for index, value in enumerate(path):
            px = history_right + index * (future_path_right - history_right) / max(len(path) - 1, 1)
            points.append((px, y_price(value)))
        color = COLORS[scenario["kind"]]
        pieces.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in points)}" fill="none" stroke="{color}" stroke-width="4" stroke-dasharray="9 6" stroke-linejoin="round"/>')
        trigger_lines = wrap_text(scenario.get("trigger", ""), max_units=16.5, max_lines=2)
        target_lines = wrap_text(scenario.get("targets_label", ""), max_units=16.5, max_lines=2)
        block_height = 40 + 16 * len(trigger_lines) + 16 * len(target_lines)
        scenario_draws.append(
            {
                "scenario": scenario,
                "points": points,
                "color": color,
                "text_color": TEXT_COLORS[scenario["kind"]],
                "trigger_lines": trigger_lines,
                "target_lines": target_lines,
                "height": block_height,
                "desired_center": points[-1][1],
            }
        )

    label_tops = resolve_label_tops(
        [{"id": row["scenario"]["id"], "height": row["height"], "desired_center": row["desired_center"]} for row in scenario_draws],
        top=plot_top + 30,
        bottom=plot_bottom - 4,
        gap=8,
    )
    for row in scenario_draws:
        scenario = row["scenario"]
        top = label_tops[scenario["id"]]
        center = top + row["height"] / 2
        end_x, end_y = row["points"][-1]
        color = row["color"]
        text_color = row["text_color"]
        pieces.append(f'<g data-scenario-label="{html.escape(scenario["id"])}" data-kind="{html.escape(scenario["kind"])}">')
        pieces.append(f'<title>{html.escape(scenario.get("trigger", ""))} | {html.escape(scenario.get("targets_label", ""))}</title>')
        pieces.append(f'<line x1="{end_x:.1f}" y1="{end_y:.1f}" x2="{label_left-8:.1f}" y2="{center:.1f}" stroke="{color}" stroke-width="2"/>')
        pieces.append(f'<circle cx="{end_x:.1f}" cy="{end_y:.1f}" r="5" fill="{color}" stroke="#ffffff" stroke-width="2"/>')
        pieces.append(f'<rect x="{label_left-8:.1f}" y="{top:.1f}" width="{label_right-label_left+8:.1f}" height="{row["height"]:.1f}" rx="8" fill="#ffffff" stroke="{color}" stroke-opacity="0.45"/>')
        pieces.append(svg_text(label_left + 4, top + 19, f"{scenario['id']} {scenario['label']}", size=14, weight=600, fill=text_color))
        cursor_y = top + 39
        for line in row["trigger_lines"]:
            pieces.append(svg_text(label_left + 4, cursor_y, line, size=12, fill=text_color))
            cursor_y += 16
        cursor_y += 2
        for line in row["target_lines"]:
            pieces.append(svg_text(label_left + 4, cursor_y, line, size=12, weight=600, fill=text_color))
            cursor_y += 16
        pieces.append("</g>")

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
        legend_text_color = TEXT_COLORS["history"] if color == COLORS["history"] else next(
            TEXT_COLORS[kind] for kind in ("bullish", "range", "bearish") if COLORS[kind] == color
        )
        pieces.append(svg_text(lx + 38, 527, label, size=12, weight=500, fill=legend_text_color))
        lx += max(170, min(220, 68 + text_units(label) * 9))
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
