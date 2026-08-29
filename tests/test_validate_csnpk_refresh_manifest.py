import tempfile
import unittest
from pathlib import Path

from scripts.validate_csnpk_refresh_manifest import retired_redirect_conflicts


class RetiredRedirectConflictsTest(unittest.TestCase):
    def test_detects_exact_slash_and_wildcard_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            redirects = Path(directory) / "_redirects"
            redirects.write_text(
                "/retired / 301\n"
                "/retired/ / 301\n"
                "/retired/* / 301\n"
                "/live/ /elsewhere/ 301\n",
                encoding="utf-8",
            )

            conflicts = retired_redirect_conflicts(redirects, ["/retired/"])

        self.assertEqual(
            conflicts,
            [
                (1, "/retired", "/retired/"),
                (2, "/retired/", "/retired/"),
                (3, "/retired/*", "/retired/"),
            ],
        )

    def test_ignores_comments_blank_lines_and_live_routes(self):
        with tempfile.TemporaryDirectory() as directory:
            redirects = Path(directory) / "_redirects"
            redirects.write_text(
                "# /retired/ / 301\n\n/live/ /elsewhere/ 301\n",
                encoding="utf-8",
            )

            conflicts = retired_redirect_conflicts(redirects, ["/retired/"])

        self.assertEqual(conflicts, [])


if __name__ == "__main__":
    unittest.main()
