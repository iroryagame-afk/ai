import importlib.util
import json
from pathlib import Path
import unittest
from html.parser import HTMLParser
import subprocess

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('near_term', ROOT/'scripts/render_near_term_macro.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MacroOverlayTests(unittest.TestCase):
    def test_evidence_and_pending_results(self):
        data = json.loads((ROOT/'macro-event-radar/data.json').read_text())['near_term']
        self.assertEqual(len(data['events']), 7)
        self.assertEqual(len({x['id'] for x in data['events']}), 7)
        for item in data['events']:
            self.assertIn('status', item['result'])
            self.assertIn('verified_at', item['result'])
        output = module.render_block(data)
        self.assertIn('不是官方目标或市场一致预期', output)
        self.assertIn('缺WI时明确未核验', output)
        self.assertIn('不代表已完成结果跟踪', output)

    def test_static_sections(self):
        for target in module.TARGETS:
            page = (ROOT/target).read_text()
            self.assertEqual(page.count('id="near-term-macro"'), 1)
            self.assertIn('100美元已盘中触及', page)
            self.assertLess(page.index('<h1'), page.index('id="near-term-macro"'))

    def test_escape(self):
        self.assertEqual(module.esc('<script>'), '&lt;script&gt;')

    def test_html_and_inline_javascript(self):
        class Parser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.ids, self.scripts, self.current = [], [], None
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if 'id' in attrs:
                    self.ids.append(attrs['id'])
                if tag == 'script' and 'src' not in attrs and attrs.get('type') != 'application/json':
                    self.current = ''
            def handle_data(self, text):
                if self.current is not None:
                    self.current += text
            def handle_endtag(self, tag):
                if tag == 'script' and self.current is not None:
                    self.scripts.append(self.current)
                    self.current = None
        for target in module.TARGETS:
            parser = Parser()
            parser.feed((ROOT/target).read_text())
            self.assertEqual(len(parser.ids), len(set(parser.ids)), target)
            for script in parser.scripts:
                result = subprocess.run(['node', '--check'], input=script, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
