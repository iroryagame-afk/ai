#!/usr/bin/env python3
"""Validate the CSNPK refresh contract against a publish checkout."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def nested(data: object, field: str) -> object:
    value = data
    for part in field.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(field)
        value = value[part]
    return value


def route_dir(root: Path, route: str) -> Path:
    return root if route == "/" else root / route.strip("/")


def retired_redirect_conflicts(path: Path, retired: list[str]) -> list[tuple[int, str, str]]:
    if not path.is_file():
        return []
    conflicts: list[tuple[int, str, str]] = []
    retired_sources = {
        source: route
        for route in retired
        for source in (route.rstrip("/"), route, route.rstrip("/") + "/*")
    }
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        source = line.split()[0]
        if source in retired_sources:
            conflicts.append((line_number, source, retired_sources[source]))
    return conflicts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    root = args.site_root.resolve()
    manifest_path = args.manifest or root / "docs/csnpk-refresh-manifest.json"
    contract = read_json(manifest_path)
    errors: list[str] = []

    pages = contract.get("pages", [])
    routes = [page.get("route") for page in pages]
    retired = contract.get("retiredRoutes", [])
    if len(routes) != len(set(routes)):
        errors.append("duplicate live routes in manifest")
    if len(retired) != len(set(retired)):
        errors.append("duplicate retired routes in manifest")
    overlap = sorted(set(routes) & set(retired))
    if overlap:
        errors.append(f"live/retired overlap: {overlap}")

    for page in pages:
        route = page["route"]
        base = route_dir(root, route)
        for relative in page.get("files", []):
            target = base / relative
            if not target.is_file():
                errors.append(f"missing {route}{relative}: {target}")
        freshness = page.get("freshness")
        if freshness:
            source = base / freshness["file"]
            if source.is_file():
                try:
                    value = nested(read_json(source), freshness["field"])
                    if value in (None, "", [], {}):
                        errors.append("empty freshness " + route + " " + freshness["field"])
                except (json.JSONDecodeError, KeyError) as exc:
                    errors.append(f"invalid freshness {route}: {exc}")

    for route in retired:
        target = route_dir(root, route)
        if target.exists():
            errors.append(f"retired route still exists: {route} -> {target}")

    for line_number, source, route in retired_redirect_conflicts(root / "_redirects", retired):
        errors.append(
            f"retired route still redirected: {route} via _redirects:{line_number} ({source})"
        )

    registry_path = root / contract["registry"]
    if not registry_path.is_file():
        errors.append(f"missing registry: {registry_path}")
    else:
        registry = registry_path.read_text(encoding="utf-8")
        table_routes = set(re.findall(r"\|[^\n]*\x60(/[^\x60]+/)\x60[^\n]*\|", registry))
        covered = set(routes) | set(retired)
        missing = sorted(table_routes - covered)
        if missing:
            errors.append(f"registry routes missing from manifest: {missing}")

    result = {
        "status": "PASS" if not errors else "FAIL",
        "siteRoot": str(root),
        "livePages": len(routes),
        "retiredRoutes": len(retired),
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
