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
        self.assertIn("不是Nasdaq提供的数据", self.html)
        self.assertRegex(self.html, r"待补充核验|暂不量化")

    def test_premarket_section_precedes_after_hours_section(self):
        premarket = self.html.index("盘前｜按北京时间升序")
        after_hours = self.html.index("盘后｜按北京时间升序")
        self.assertLess(premarket, after_hours)

        premarket_html = self.html[premarket:after_hours]
        after_hours_html = self.html[after_hours:]
        self.assertNotIn('<span class="tag">盘后</span>', premarket_html)
        self.assertNotIn('<span class="tag">盘前</span>', after_hours_html)

    def test_each_session_is_sorted_by_beijing_placeholder(self):
        premarket, after_hours = self.html.split(
            '<tr class="session-row"><th colspan="6">盘后｜按北京时间升序</th></tr>',
            maxsplit=1,
        )
        pattern = re.compile(r"(\d+)月(\d+)日 (\d+):(\d+)")
        for section in (premarket.split("盘前｜按北京时间升序", maxsplit=1)[1], after_hours):
            times = [tuple(map(int, match.groups())) for match in pattern.finditer(section)]
            self.assertEqual(times, sorted(times))


if __name__ == "__main__":
    unittest.main()
