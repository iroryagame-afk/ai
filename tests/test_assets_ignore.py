import unittest
from pathlib import Path


class AssetsIgnoreTests(unittest.TestCase):
    def test_internal_files_are_excluded_from_public_assets(self):
        root = Path(__file__).resolve().parents[1]
        patterns = {
            line.strip()
            for line in (root / ".assetsignore").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }

        required = {
            "/.git/",
            "/.wrangler/",
            "/.github/",
            "/AGENTS.md",
            "/docs/",
            "/scripts/",
            "/tests/",
            "/wrangler.jsonc",
            "**/__pycache__/",
            "**/*.py[cod]",
        }
        self.assertTrue(required <= patterns, required - patterns)


if __name__ == "__main__":
    unittest.main()
