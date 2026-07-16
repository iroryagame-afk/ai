#!/usr/bin/env python3
"""Validate and summarize an auditable pattern-evidence score.

The score measures naming quality, not future return probability.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


COMPONENT_MAX = {
    "geometry": 25,
    "touches_duration": 15,
    "volume": 15,
    "breakout": 15,
    "retest": 10,
    "momentum": 10,
    "regime_relative_strength": 10,
}


def quality_for(score: float) -> str:
    if score >= 75:
        return "high"
    if score >= 55:
        return "medium"
    if score >= 35:
        return "low"
    return "insufficient"


def score_assessment(assessment: dict) -> dict:
    components = assessment.get("components") or {}
    unknown = sorted(set(components) - set(COMPONENT_MAX))
    if unknown:
        raise ValueError(f"unknown assessment components: {unknown}")

    normalized = {}
    for name, maximum in COMPONENT_MAX.items():
        value = float(components.get(name, 0))
        if value < 0 or value > maximum:
            raise ValueError(f"{name} must be between 0 and {maximum}")
        normalized[name] = value

    score = round(sum(normalized.values()), 2)
    missing = list(assessment.get("missing_evidence") or [])
    contradictions = list(assessment.get("contradictions") or [])
    alternatives = list(assessment.get("alternatives") or [])
    if quality_for(score) != "high" and not alternatives:
        raise ValueError("non-high assessments need at least one alternative classification")

    return {
        "quality": quality_for(score),
        "score": score,
        "score_is_probability": False,
        "components": normalized,
        "alternatives": alternatives,
        "contradictions": contradictions,
        "missing_evidence": missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--write-back", action="store_true")
    args = parser.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    result = score_assessment(plan.get("assessment") or {})
    if args.write_back:
        plan["assessment"] = result
        args.plan.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
