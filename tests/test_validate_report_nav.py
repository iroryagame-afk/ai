import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_report_nav import validate_manifest


class ValidateReportNavTests(unittest.TestCase):
    def write_repo(self, entries):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "nav").mkdir()
        (root / "nav" / "reports.json").write_text(
            json.dumps(entries, ensure_ascii=False), encoding="utf-8"
        )
        return temp, root

    def valid_entry(self):
        return {
            "id": "cxl",
            "date": "2026-06-25",
            "title": "CXL 综合分析报告",
            "url": "../cxl/",
            "category": "行业研究",
            "tags": ["CXL", "内存墙"],
        }

    def test_accepts_valid_public_report(self):
        temp, root = self.write_repo([self.valid_entry()])
        self.addCleanup(temp.cleanup)
        (root / "cxl").mkdir()
        (root / "cxl" / "index.html").write_text("ok", encoding="utf-8")

        self.assertEqual(validate_manifest(root), [])

    def test_rejects_daily_page_and_duplicate_identity(self):
        first = self.valid_entry()
        second = self.valid_entry() | {"url": "../csn/"}
        temp, root = self.write_repo([first, second])
        self.addCleanup(temp.cleanup)

        errors = validate_manifest(root)

        self.assertTrue(any("duplicate id" in error for error in errors))
        self.assertTrue(any("forbidden URL" in error for error in errors))

    def test_rejects_invalid_fields_category_and_missing_target(self):
        entry = self.valid_entry() | {
            "date": "06/25/2026",
            "category": "每日更新",
            "tags": [],
        }
        temp, root = self.write_repo([entry])
        self.addCleanup(temp.cleanup)

        errors = validate_manifest(root)

        self.assertTrue(any("invalid date" in error for error in errors))
        self.assertTrue(any("invalid category" in error for error in errors))
        self.assertTrue(any("non-empty tags" in error for error in errors))
        self.assertTrue(any("target does not exist" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
