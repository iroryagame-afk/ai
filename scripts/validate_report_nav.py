#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


REQUIRED = {"id", "date", "title", "url", "category", "tags"}
ALLOWED_CATEGORIES = {"行业研究", "主题策略", "公司研究"}
FORBIDDEN_PREFIXES = (
    "../csn/",
    "../csn2/",
    "../a-share-flow/",
    "../us-sector-flow/",
    "../futu-indicators/",
    "../skill-packages/",
    "../summer-classics/",
)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_manifest(root: Path) -> list[str]:
    manifest = root / "nav" / "reports.json"
    if not manifest.exists():
        return ["nav/reports.json does not exist"]

    try:
        entries = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"nav/reports.json is not valid JSON: {exc}"]

    if not isinstance(entries, list):
        return ["nav/reports.json must contain a JSON array"]

    errors: list[str] = []
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    root_resolved = root.resolve()

    for index, entry in enumerate(entries):
        label = f"entry {index + 1}"
        if not isinstance(entry, dict):
            errors.append(f"{label}: must be an object")
            continue

        missing = REQUIRED - set(entry)
        if missing:
            errors.append(f"{label}: missing fields {', '.join(sorted(missing))}")
            continue

        entry_id = entry["id"]
        url = entry["url"]
        if not isinstance(entry_id, str) or not entry_id.strip():
            errors.append(f"{label}: id must be a non-empty string")
        elif entry_id in seen_ids:
            errors.append(f"{label}: duplicate id {entry_id}")
        seen_ids.add(entry_id)

        if not isinstance(url, str) or not url.strip():
            errors.append(f"{label}: url must be a non-empty string")
            continue
        if url in seen_urls:
            errors.append(f"{label}: duplicate URL {url}")
        seen_urls.add(url)

        if url.startswith(FORBIDDEN_PREFIXES):
            errors.append(f"{label}: forbidden URL {url}")

        date = entry["date"]
        if not isinstance(date, str) or not DATE_RE.fullmatch(date):
            errors.append(f"{label}: invalid date {date!r}")

        category = entry["category"]
        if category not in ALLOWED_CATEGORIES:
            errors.append(f"{label}: invalid category {category!r}")

        title = entry["title"]
        if not isinstance(title, str) or not title.strip():
            errors.append(f"{label}: title must be a non-empty string")

        tags = entry["tags"]
        if not isinstance(tags, list) or not tags or not all(
            isinstance(tag, str) and tag.strip() for tag in tags
        ):
            errors.append(f"{label}: tags must be a non-empty tags array")

        parsed = urlparse(url)
        if parsed.scheme or parsed.netloc or not url.startswith("../"):
            errors.append(f"{label}: URL must be a relative ../ path")
            continue
        target = (root / "nav" / parsed.path / "index.html").resolve()
        try:
            target.relative_to(root_resolved)
        except ValueError:
            errors.append(f"{label}: URL escapes repository root")
            continue
        if not target.is_file():
            errors.append(f"{label}: target does not exist for {url}")

    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = validate_manifest(root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    count = len(json.loads((root / "nav" / "reports.json").read_text(encoding="utf-8")))
    print(f"OK: {count} report entries validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
