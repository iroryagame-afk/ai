import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def latest_us_event_page() -> Path:
    pages = sorted(ROOT.glob("weekly-event-transmission-*/us/index.html"))
    if not pages:
        raise AssertionError("missing weekly U.S. event page")
    return pages[-1]


class WeeklyUsEventPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = latest_us_event_page().read_text(encoding="utf-8")

    def test_estimate_count_and_beat_probability_are_explained(self):
        self.assertIn("分析师预测样本数", self.html)
        self.assertIn("参与EPS共识的预测数量", self.html)
        self.assertIn("Beat概率（条件式研究）", self.html)
        self.assertIn("不是 Nasdaq 原始字段", self.html)
        self.assertNotIn("待补充核验", self.html)
        self.assertNotIn("暂不量化", self.html)
        probability_cells = re.findall(
            r'<span class="prob"><strong>(\d+)%</strong><span class="prob-range">区间 (\d+)%—(\d+)%</span>',
            self.html,
        )
        self.assertEqual(len(probability_cells), 11)
        for midpoint, low, high in probability_cells:
            self.assertLess(int(low), int(midpoint))
            self.assertLess(int(midpoint), int(high))

    def test_previous_earnings_and_post_earnings_performance_are_complete(self):
        self.assertIn("上次财报", self.html)
        self.assertIn("财报后表现", self.html)
        previous_dates = re.findall(
            r'class="source-link"[^>]*>(2026-\d{2}-\d{2})</a>', self.html
        )
        reactions = re.findall(
            r'<span class="reaction (?:up|down)">首日 [^<]+</span><span class="reaction (?:up|down)">T\+5 [^<]+</span>',
            self.html,
        )
        self.assertEqual(len(previous_dates), 11)
        self.assertEqual(len(reactions), 11)
        self.assertIn("Futu OpenD（K_DAY、QFQ", self.html)

    def test_rows_are_sorted_by_date_then_session(self):
        self.assertIn("先按日期升序；同一日期内，盘前排在盘后前面", self.html)
        pattern = re.compile(
            r'(\d+)月(\d+)日 \d+:\d+<br><span class="tag">(盘前|盘后)</span>'
        )
        rows = pattern.findall(self.html)
        self.assertTrue(rows)
        keys = [
            (int(month), int(day), 0 if session == "盘前" else 1)
            for month, day, session in rows
        ]
        self.assertEqual(keys, sorted(keys))


if __name__ == "__main__":
    unittest.main()
