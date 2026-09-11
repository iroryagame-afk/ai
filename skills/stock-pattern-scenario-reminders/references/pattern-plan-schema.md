# Pattern plan schema

计划文件是数据核验、图表渲染和富途提醒之间的唯一交接面。价格使用数值，不带货币符号。

```json
{
  "code": "US.PLTR",
  "name": "Palantir",
  "as_of": "2026-07-15 16:00 ET",
  "session_label": "正常时段收盘；隔夜 133.56",
  "currency": "USD",
  "current": 133.76,
  "status": "候选结构，尚未突破",
  "assessment": {
    "quality": "medium",
    "score": 68,
    "score_is_probability": false,
    "components": {
      "geometry": 22,
      "touches_duration": 10,
      "volume": 8,
      "breakout": 8,
      "retest": 0,
      "momentum": 10,
      "regime_relative_strength": 10
    },
    "alternatives": ["箱体上沿测试"],
    "contradictions": ["右肩仍未完成回踩"],
    "missing_evidence": ["突破后回踩"]
  },
  "pattern": {
    "type": "inverse_head_shoulders_candidate",
    "label": "头肩底候选",
    "family": "reversal",
    "decision_zone": {"low": 136.0, "high": 139.0, "label": "颈线 136–139"},
    "key_points": [
      {"date": "2026-06-12", "label": "左肩", "value": 126.65},
      {"date": "2026-06-25", "label": "头部", "value": 106.37},
      {"date": "2026-07-14", "label": "右肩", "value": 122.64}
    ],
    "structure_lines": [
      {
        "label": "肩部支撑线",
        "style": "support",
        "points": [
          {"date": "2026-06-12", "value": 126.65},
          {"date": "2026-07-14", "value": 122.64}
        ]
      }
    ]
  },
  "history": [
    {"date": "2026-06-12", "close": 127.99},
    {"date": "2026-06-15", "close": 134.71}
  ],
  "scenarios": [
    {
      "id": "A",
      "kind": "bullish",
      "label": "有效突破",
      "trigger": "收盘 >139，回踩 136–139 守住",
      "targets_label": "143–145 → 150–154 → 166–170",
      "path": [133.76, 138.0, 145.0, 152.0, 168.0]
    },
    {
      "id": "B",
      "kind": "range",
      "label": "区间整理",
      "trigger": "123–139 震荡，等待右肩完成",
      "targets_label": "不预设上行目标",
      "path": [133.76, 126.0, 136.0, 130.0, 133.0]
    },
    {
      "id": "C",
      "kind": "bearish",
      "label": "形态失效",
      "trigger": "收盘 <123；跌破 106 头部失效",
      "targets_label": "116 → 106",
      "path": [133.76, 125.0, 118.0, 110.0, 106.0]
    }
  ],
  "reminders": [
    {"price": 139.0, "direction": "PRICE_UP", "note": "突破139｜不追·回踩136观察仓"},
    {"price": 123.0, "direction": "PRICE_DOWN", "note": "跌破123｜减仓·收复再看"},
    {"price": 106.0, "direction": "PRICE_DOWN", "note": "跌破106｜头部失效·止损"}
  ],
  "timing_overlay": {
    "market": "US",
    "source_skill": "stock-position-timing",
    "data_status": "VERIFIED_FUTU_OPEND",
    "trend_state": "healthy",
    "heat_state": "normal",
    "market_gate": "neutral",
    "signal_state": "pending_close",
    "position_state": "flat",
    "decision": "wait_confirmation",
    "summary": "候选突破，等收盘确认",
    "confirmation": {
      "required": ["收盘站上139", "回踩136–139守住"],
      "met": []
    },
    "execution": {
      "session": "after_hours",
      "same_day_exit_allowed": true
    }
  }
}
```

## Validation rules

- `code`, `current`, `history`, `pattern`, `scenarios` are required.
- `history` is chronological and contains at least 10 points.
- Every key-point date must exist in `history`, unless the point uses an intraday low; then add `source_note`.
- `scenarios` contains A/B/C exactly once. A is the primary confirmed direction (`bullish` or `bearish`), B is `range`, and C must be the opposite direction from A.
- Every scenario path starts at or near `current` and contains at least 3 values.
- `pattern.decision_zone` is the generic confirmation band. `pattern.neckline` remains accepted for backward compatibility. Triangles, flags, wedges and channels should add `structure_lines` with at least two dated points per line.
- `assessment.score` is a 0–100 structure-quality score, never a probability. Its components follow [pattern-taxonomy.md](pattern-taxonomy.md); missing evidence scores zero and is listed explicitly.
- Record at least one plausible alternative in `assessment.alternatives` when quality is below `high`.
- `reminders` contains at most 3 entries. `direction` is `PRICE_UP` or `PRICE_DOWN`; `note` is at most 20 characters.
- Use `观察仓`, not unconditional `买入`, unless the corresponding timing Skill has confirmed the market, trend and retest gates.
- `timing_overlay` is required only when the user asks what to do, whether to buy/sell, or how to manage a position. Validate it with `scripts/validate_timing_overlay.py` and follow [timing-overlay-schema.md](timing-overlay-schema.md).
- Keep `assessment.score` and `timing_overlay.decision` independent: pattern quality cannot override an unconfirmed signal, broken trend, overheated position, defensive market gate, or market-specific execution constraint.
