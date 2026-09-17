#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


renderer = load_module("pattern_renderer", ROOT / "scripts" / "render_pattern_chart.py")
syncer = load_module("pattern_syncer", ROOT / "scripts" / "sync_pattern_reminders.py")
scorer = load_module("pattern_scorer", ROOT / "scripts" / "score_pattern_evidence.py")
fetcher = load_module("pattern_fetcher", ROOT / "scripts" / "fetch_pattern_data.py")
timing_validator = load_module("timing_validator", ROOT / "scripts" / "validate_timing_overlay.py")


class PatternSkillTest(unittest.TestCase):
    def setUp(self):
        self.plan_path = ROOT / "tests" / "fixture_pltr_plan.json"
        self.plan = json.loads(self.plan_path.read_text(encoding="utf-8"))

    def test_fixture_validates(self):
        renderer.validate_plan(self.plan)
        plans = syncer.load_plans([self.plan_path])
        self.assertEqual(plans[0]["code"], "US.PLTR")

    def test_renderer_contains_operational_levels(self):
        svg = renderer.render_svg(self.plan)
        self.assertIn(f"{self.plan['name']}（{self.plan['code']}）", svg)
        self.assertIn("颈线 136–139", svg)
        self.assertIn("结构质量 中 68/100（非胜率）", svg)
        self.assertIn("肩部支撑线", svg)
        self.assertIn("执行：候选突破，等收盘确认", svg)
        self.assertIn("A 有效突破", svg)
        self.assertIn("B 区间整理", svg)
        self.assertIn("C 形态失效", svg)
        self.assertIn('data-scenario-label="A"', svg)
        self.assertIn(renderer.TEXT_COLORS["bullish"], svg)
        self.assertIn(renderer.TEXT_COLORS["range"], svg)
        self.assertIn(renderer.TEXT_COLORS["bearish"], svg)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "chart.html"
            output.write_text(renderer.standalone_html(svg), encoding="utf-8")
            self.assertGreater(output.stat().st_size, 5000)

    def test_bearish_primary_path_is_supported(self):
        path = ROOT / "tests" / "fixture_bearish_top_plan.json"
        plan = json.loads(path.read_text(encoding="utf-8"))
        renderer.validate_plan(plan)
        svg = renderer.render_svg(plan)
        self.assertIn("A 有效跌破", svg)
        self.assertIn("C 顶部失效", svg)

    def test_scenario_c_must_oppose_a(self):
        broken = json.loads(json.dumps(self.plan, ensure_ascii=False))
        broken["scenarios"][2]["kind"] = "bullish"
        with self.assertRaises(ValueError):
            renderer.validate_plan(broken)

    def test_scenario_labels_follow_endpoint_order_without_overlap(self):
        blocks = [
            {"id": "A", "height": 72, "desired_center": 410},
            {"id": "B", "height": 72, "desired_center": 280},
            {"id": "C", "height": 72, "desired_center": 160},
        ]
        tops = renderer.resolve_label_tops(blocks, top=100, bottom=450, gap=8)
        self.assertLess(tops["C"], tops["B"])
        self.assertLess(tops["B"], tops["A"])
        self.assertGreaterEqual(tops["B"], tops["C"] + 80)
        self.assertGreaterEqual(tops["A"], tops["B"] + 80)
        self.assertGreaterEqual(min(tops.values()), 100)
        self.assertLessEqual(max(tops.values()) + 72, 450)

    def test_chart_status_rejects_negative_pattern_labels(self):
        broken = json.loads(json.dumps(self.plan, ensure_ascii=False))
        broken["status"] = "高位复合顶部破位；非头肩底"
        with self.assertRaises(ValueError):
            renderer.validate_plan(broken)

    def test_evidence_score_is_auditable_not_probability(self):
        result = scorer.score_assessment(self.plan["assessment"])
        self.assertEqual(result["score"], 68)
        self.assertEqual(result["quality"], "medium")
        self.assertFalse(result["score_is_probability"])

    def test_us_pending_close_overlay_is_valid(self):
        result = timing_validator.validate_overlay(self.plan["timing_overlay"])
        self.assertEqual(result["status"], "VALID")
        self.assertEqual(result["source_skill"], "stock-position-timing")

    def test_unconfirmed_us_signal_cannot_execute(self):
        overlay = json.loads(json.dumps(self.plan["timing_overlay"], ensure_ascii=False))
        overlay["decision"] = "execute_small"
        overlay["execution"]["session"] = "regular_confirmed"
        overlay["execution"]["intraday_trigger"] = "站上首15分钟高点"
        with self.assertRaises(ValueError):
            timing_validator.validate_overlay(overlay)

    def test_us_premarket_cannot_execute(self):
        overlay = json.loads(json.dumps(self.plan["timing_overlay"], ensure_ascii=False))
        overlay["signal_state"] = "confirmed"
        overlay["decision"] = "execute_small"
        overlay["execution"]["session"] = "premarket"
        overlay["execution"]["intraday_trigger"] = "突破盘前高点"
        with self.assertRaises(ValueError):
            timing_validator.validate_overlay(overlay)

    def test_a_share_t1_overlay_enforces_date_order_and_no_same_day_exit(self):
        overlay = {
            "market": "A_SHARE",
            "source_skill": "a-stock-position-timing",
            "data_status": "VERIFIED_FUTU_OPEND",
            "trend_state": "healthy",
            "heat_state": "normal",
            "market_gate": "neutral",
            "signal_state": "confirmed",
            "position_state": "flat",
            "decision": "candidate",
            "summary": "T日确认，列入T+1观察",
            "confirmation": {"required": ["收盘突破箱体"], "met": ["收盘突破箱体"]},
            "execution": {
                "signal_date": "2026-07-16",
                "earliest_entry_date": "2026-07-17",
                "earliest_sell_date_if_filled": "2026-07-20",
                "same_day_exit_allowed": False,
                "t1_scenarios": {
                    "flat_or_small_gap": "承接成立才观察仓",
                    "large_gap_up": "不追，等回踩",
                    "large_gap_down": "跌破风险线取消",
                },
                "tradability_checks": ["停牌", "涨跌停", "一字板", "证券属性", "公告风险"],
            },
        }
        result = timing_validator.validate_overlay(overlay)
        self.assertEqual(result["market"], "A_SHARE")
        broken = json.loads(json.dumps(overlay, ensure_ascii=False))
        broken["execution"]["same_day_exit_allowed"] = True
        with self.assertRaises(ValueError):
            timing_validator.validate_overlay(broken)

    def test_indicator_enrichment_supports_confluence(self):
        rows = []
        for index in range(90):
            close = 100 + index * 0.2
            rows.append({"open": close - 0.2, "high": close + 1, "low": close - 1, "close": close, "volume": 1000 + index})
        enriched = fetcher.enrich(pd.DataFrame(rows), 4)
        for column in ("rsi14", "macd_hist", "volume_ratio20", "bb_width_pct", "return_60d"):
            self.assertIn(column, enriched.columns)
            self.assertFalse(pd.isna(enriched.iloc[-1][column]))

    def test_a_share_bar_is_complete_at_market_close(self):
        snapshot = {"update_time": "2026-07-16 15:00:00"}
        self.assertFalse(fetcher.is_live_daily_bar("SH.688008", "2026-07-16", snapshot, "2026-07-16"))
        intraday = {"update_time": "2026-07-16 14:59:59"}
        self.assertTrue(fetcher.is_live_daily_bar("SH.688008", "2026-07-16", intraday, "2026-07-16"))

    def test_preview_never_writes(self):
        result = syncer.preview([self.plan])
        self.assertEqual(result["status"], "DRY_RUN_NO_FUTU_WRITE")
        self.assertEqual(len(result["stocks"]["US.PLTR"]), 3)
        self.assertTrue(all(row["freq"] == "ALWAYS" for row in result["stocks"]["US.PLTR"]))
        self.assertEqual(result["stocks"]["US.PLTR"][0]["price"], 139.0)

    def test_new_price_field_and_legacy_value_field_are_both_supported(self):
        modern = json.loads(json.dumps(self.plan, ensure_ascii=False))
        for reminder in modern["reminders"]:
            reminder["price"] = reminder.pop("value")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "modern.json"
            path.write_text(json.dumps(modern, ensure_ascii=False), encoding="utf-8")
            loaded = syncer.load_plans([path])
        self.assertEqual(syncer.reminder_price(loaded[0]["reminders"][0]), 139.0)
        self.assertEqual(syncer.reminder_price(self.plan["reminders"][0]), 139.0)

    def test_chart_reminder_write_requires_exact_same_turn_authorization(self):
        self.assertFalse(renderer.authorize_reminder_write(False, ""))
        with self.assertRaises(ValueError):
            renderer.authorize_reminder_write(True, "yes")
        self.assertTrue(renderer.authorize_reminder_write(True, "WRITE_FUTU_PATTERN_REMINDERS"))

    def test_long_note_rejected(self):
        broken = json.loads(json.dumps(self.plan, ensure_ascii=False))
        broken["reminders"][0]["note"] = "这是一条明显超过二十个字符并且不应该写入富途的提醒备注"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.json"
            path.write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(ValueError):
                syncer.load_plans([path])


if __name__ == "__main__":
    unittest.main()
