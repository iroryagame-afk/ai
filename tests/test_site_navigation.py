import importlib.util
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("site_nav", ROOT / "scripts/restructure_site_nav.py")
SITE_NAV = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(SITE_NAV)


class SiteNavigationTests(unittest.TestCase):
    def test_every_active_page_uses_one_shared_navigation(self):
        for relative in SITE_NAV.active_pages():
            with self.subTest(page=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                self.assertEqual(text.count('class="csn-topnav"'), 1)
                self.assertEqual(text.count("data-csnpk-nav-style"), 1)
                self.assertEqual(text.count("data-csnpk-nav-script"), 1)
                self.assertIn(f'data-nav-version="{SITE_NAV.NAV_VERSION}"', text)

    def test_top_level_order_and_labels_are_identical(self):
        expected = ["首页", "宏观", "事件", "A股", "美股", "选股器", "代码库", "行业调研"]
        for relative in SITE_NAV.active_pages():
            with self.subTest(page=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                nav = re.search(r'<nav class="csn-topnav".*?</nav>', text, re.S).group(0)
                menu = re.search(r'<div class="csn-menu">(.*)</div></div></nav>', nav, re.S).group(1)
                labels = re.findall(r'<div class="csn-item(?: active)?(?: csn-home)?"[^>]*>(?:<a[^>]*>|<button[^>]*>)([^<]+)', menu)
                self.assertEqual([label.strip() for label in labels], expected)

    def test_macro_has_real_routes_and_no_policy_placeholder(self):
        sample = SITE_NAV.nav("index.html")
        macro = re.search(r'data-group="macro".*?</div></div>', sample, re.S).group(0)
        self.assertIn('href="./us-market/"', macro)
        self.assertIn('href="./macro-fiscal-risk/"', macro)
        self.assertIn('href="./us-market/x-consensus/"', macro)
        self.assertIn('href="./macro-event-radar/"', macro)
        self.assertIn("全球注意力雷达", macro)
        self.assertNotIn("政策导航", macro)

    def test_market_page_no_longer_embeds_attention_radar(self):
        text = (ROOT / "us-market/index.html").read_text(encoding="utf-8")
        body = text.split("</nav>", 1)[1]
        self.assertNotIn("全球股票注意力雷达", body)
        self.assertNotIn('href="./x-consensus/"', body)

    def test_event_is_directly_after_macro_and_uses_latest_registered_page(self):
        sample = SITE_NAV.nav("index.html")
        event_route = SITE_NAV.current_event_route()
        event = re.search(r'data-group="event".*?</div></div>', sample, re.S).group(0)
        self.assertIn(f'href="./{event_route}us/"', event)
        self.assertIn(f'href="./{event_route}a-share/"', event)
        self.assertEqual([label.strip() for label in re.findall(r"<b>([^<]+)", event)], ["美股事件", "A股财报"])
        self.assertEqual(event_route, "weekly-event-transmission-2026w35/")

    def test_a_share_owns_split_pages_and_bingshen(self):
        sample = SITE_NAV.nav("index.html")
        a_share = re.search(r'data-group="a-tools".*?</div></div>', sample, re.S).group(0)
        picker = re.search(r'data-group="picker".*?</div></div>', sample, re.S).group(0)
        self.assertIn('href="./a-share-domestic-compute/"', a_share)
        self.assertIn('href="./a-share-supply-tightness/"', a_share)
        self.assertIn('href="./a-share-next-generation/"', a_share)
        self.assertIn('href="./bingshen/"', a_share)
        self.assertNotIn('href="./bingshen/"', picker)
        self.assertEqual(a_share.count('class="csn-drop-separator"'), 1)
        self.assertEqual(sample.count("<b>冰神分享 "), 1)

    def test_trend_candidate_pages_live_under_their_market_navigation(self):
        sample = SITE_NAV.nav("index.html")
        a_share = re.search(r'data-group="a-tools".*?</div></div>', sample, re.S).group(0)
        us_share = re.search(r'data-group="us-tools".*?</div></div>', sample, re.S).group(0)
        picker = re.search(r'data-group="picker".*?</div></div>', sample, re.S).group(0)
        self.assertIn('href="./a-share-trend-candidates/"', a_share)
        self.assertIn('href="./us-trend-candidates/"', us_share)
        self.assertNotIn("trend-candidates", picker)
        self.assertEqual(picker.count("docs.google.com/spreadsheets"), 2)

    def test_split_pages_only_publish_their_own_mainline(self):
        expected = {
            "a-share-domestic-compute": ("国产算力", "国产算力核心矩阵"),
            "a-share-supply-tightness": ("AI供需紧张", "行业弹性矩阵"),
            "a-share-next-generation": ("下一代技术", "下一代技术矩阵"),
        }
        all_headings = {heading for _, heading in expected.values()}
        for slug, (mainline, heading) in expected.items():
            with self.subTest(page=slug):
                text = (ROOT / slug / "index.html").read_text(encoding="utf-8")
                data = json.loads((ROOT / slug / "data.json").read_text(encoding="utf-8"))
                self.assertRegex(text, rf"<h[23]>{re.escape(heading)}</h[23]>")
                for other_heading in all_headings - {heading}:
                    self.assertNotIn(other_heading, text)
                self.assertEqual({row["mainline"] for row in data["industry_map"]}, {mainline})

    def test_homepage_promotes_macro_and_has_a_verified_update_note(self):
        text = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('id="stock-trends"', text)
        self.assertIn('<section aria-label="宏观" id="market-overview">', text)
        self.assertLess(text.index('id="market-overview"'), text.index('id="a-share-tools"'))
        self.assertIn('class="verified">已核验</span>', text)
        self.assertIn("全球核心事件雷达、AI基础设施走势、A股与美股趋势候选", text)
        self.assertIn('href="./macro-event-radar/"', text)
        self.assertIn('href="./ai-infrastructure-deleveraging/"', text)

    def test_new_pages_are_grouped_under_macro_and_us(self):
        sample = SITE_NAV.nav("index.html")
        macro = re.search(r'data-group="macro".*?</div></div>', sample, re.S).group(0)
        us = re.search(r'data-group="us-tools".*?</div></div>', sample, re.S).group(0)
        self.assertIn('href="./macro-event-radar/"', macro)
        self.assertIn('href="./ai-infrastructure-deleveraging/"', us)

    def test_homepage_metrics_are_driven_by_navigation_and_report_registry(self):
        text = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("股票走势总结</span>", text)
        self.assertNotIn("独立决策入口</span>", text)
        self.assertIn('id="topNavCount">–</b><span>顶层导航栏目</span>', text)
        self.assertIn('id="internalPageCount">–</b><span>站内页面入口</span>', text)
        self.assertIn('data-metric-source="nav/reports.json"', text)
        self.assertIn("querySelectorAll(':scope > .csn-item')", text)
        self.assertIn("internalRoutes.size", text)
        self.assertIn("entries.length", text)

    def test_shared_css_preserves_baseline_type_size(self):
        css = (ROOT / "assets/csnpk-nav.css").read_text(encoding="utf-8")
        self.assertIn("font: 600 14px/1", css)
        self.assertIn("padding: 0 16px", css)
        self.assertIn("font-size: 13px", css)
        self.assertIn("font-size: 9px", css)

    def test_refresh_dates_follow_dropdown_titles(self):
        sample = SITE_NAV.nav("index.html")
        self.assertIn('轮动加速度 <time class="csn-nav-refresh"', sample)
        self.assertIn('08-22 更新</time>', sample)
        self.assertIn('趋势候选 <time class="csn-nav-refresh"', sample)
        self.assertNotIn('class="csn-nav-refresh"', re.search(r'<div class="csn-menu">(.*?)data-group="macro"', sample, re.S).group(1))


if __name__ == "__main__":
    unittest.main()
