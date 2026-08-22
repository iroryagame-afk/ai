import importlib.util
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
        expected = ["首页", "宏观", "A股", "美股", "选股器", "代码库", "行业调研"]
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
        self.assertIn("全球注意力雷达", macro)
        self.assertNotIn("政策导航", macro)

    def test_market_page_no_longer_embeds_attention_radar(self):
        text = (ROOT / "us-market/index.html").read_text(encoding="utf-8")
        body = text.split("</nav>", 1)[1]
        self.assertNotIn("全球股票注意力雷达", body)
        self.assertNotIn('href="./x-consensus/"', body)

    def test_picker_owns_bingshen_and_no_top_level_bingshen(self):
        sample = SITE_NAV.nav("index.html")
        picker = re.search(r'data-group="picker".*?</div></div>', sample, re.S).group(0)
        self.assertIn('href="./bingshen/"', picker)
        self.assertEqual(sample.count(">冰神分享<"), 1)

    def test_shared_css_preserves_baseline_type_size(self):
        css = (ROOT / "assets/csnpk-nav.css").read_text(encoding="utf-8")
        self.assertIn("font: 600 14px/1", css)
        self.assertIn("padding: 0 16px", css)
        self.assertIn("font-size: 13px", css)
        self.assertIn("font-size: 9px", css)


if __name__ == "__main__":
    unittest.main()
