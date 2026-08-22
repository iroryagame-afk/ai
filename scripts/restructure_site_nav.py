#!/usr/bin/env python3
"""Apply one shared CSNPK navigation to every active public page."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NAV_VERSION = "ia-20260823c"
ACTIVE_DYNAMIC = {
    "index.html",
    "a-share-software-deleveraging/index.html",
    "a-share-hardware-deleveraging/index.html",
    "ai-infrastructure-deleveraging/index.html",
    "us-software-deleveraging/index.html",
    "a-share-t1-focus/index.html",
    "a-share-domestic-compute/index.html",
    "a-share-supply-tightness/index.html",
    "a-share-next-generation/index.html",
    "us-market/x-consensus/index.html",
    "rs-thrust/index.html",
    "rotation/index.html",
    "ai-software-security-shovels/index.html",
    "ai-hardware-shovels/index.html",
    "us-skew/index.html",
    "us-market/index.html",
    "macro-fiscal-risk/index.html",
    "code/index.html",
    "bingshen/index.html",
    "csn/index.html",
    "csn/hot/index.html",
    "nav/index.html",
}
RETIRED_REPORT_IDS = {"futu-indicators"}


def current_event_route() -> str:
    reports = json.loads((ROOT / "nav/reports.json").read_text(encoding="utf-8"))
    events = [report for report in reports if report["id"].startswith("weekly-event-transmission-")]
    if not events:
        raise SystemExit("no registered weekly event page")
    latest = max(events, key=lambda report: (report["date"], report["id"]))
    return latest["url"].removeprefix("../").strip("/") + "/"


def active_pages() -> list[str]:
    pages = set(ACTIVE_DYNAMIC)
    reports = json.loads((ROOT / "nav/reports.json").read_text(encoding="utf-8"))
    for report in reports:
        if report["id"] in RETIRED_REPORT_IDS:
            continue
        route = report["url"].removeprefix("../").strip("/")
        report_root = ROOT / route
        pages.update(str(path.relative_to(ROOT)) for path in report_root.rglob("index.html"))
    missing = sorted(page for page in pages if not (ROOT / page).is_file())
    if missing:
        raise SystemExit(f"registered active pages missing: {', '.join(missing)}")
    return sorted(pages)


def prefix_for(relative: str) -> str:
    depth = len(Path(relative).parts) - 1
    return "./" if depth == 0 else "../" * depth


def current_route(relative: str) -> str:
    parent = str(Path(relative).parent).replace(".", "")
    return f"{parent}/" if parent else ""


def item_link(prefix: str, path: str, title: str, note: str, current: str) -> str:
    css = ' class="current" aria-current="page"' if current == path else ""
    return f'<a{css} href="{prefix}{path}"><b>{title}</b><small>{note}</small></a>'


def group(prefix: str, key: str, title: str, items: list[tuple[str | None, str, str]], current: str) -> str:
    paths = {path for path, _, _ in items if path}
    active = " active" if current in paths else ""
    out = [
        f'<div class="csn-item{active}" data-group="{key}">',
        f'<button type="button" aria-haspopup="true" aria-expanded="false">{title} <span class="csn-caret" aria-hidden="true">▼</span></button>',
        '<div class="csn-drop">',
    ]
    for path, label, note in items:
        if path is None:
            out.append('<div class="csn-drop-separator" role="separator" aria-label="软件股与硬件股"></div>')
        else:
            out.append(item_link(prefix, path, label, note, current))
    out.append("</div></div>")
    return "".join(out)


def nav(relative: str) -> str:
    prefix = prefix_for(relative)
    current = current_route(relative)
    home_current = ' aria-current="page"' if current == "" else ""
    groups = [
        ("macro", "宏观", [
            ("us-market/", "大盘观察", "指数状态 · 风险温度 · 风格轮动"),
            ("macro-fiscal-risk/", "财政风险溢价监控", "长端 · 美元 · 股债 · 信用扩散"),
            ("us-market/x-consensus/", "全球注意力雷达", "中文X · 多语种长文 · Reddit · 作者原图"),
        ]),
        ("a-tools", "A股", [
            ("a-share-domestic-compute/", "国产算力", "芯片 · 服务器 · 网络 · AIDC"),
            ("a-share-supply-tightness/", "供需紧张", "存储 · PCB · 材料 · 制造"),
            ("a-share-next-generation/", "下一代技术", "光互连 · CPO · 液冷 · 连接"),
            ("bingshen/", "冰神分享", "A股观察池 · 名单与代码文件"),
            ("a-share-software-deleveraging/", "软件股", "去杠杆 · 二次确认 · 个股分化"),
            ("a-share-hardware-deleveraging/", "硬件股", "算力硬件 · 二次确认 · 个股分化"),
        ]),
        ("us-tools", "美股", [
            ("rotation/", "轮动加速度", "看顶部衰竭与底部修复"),
            ("rs-thrust/", "相对强度", "找正在加速的强势股"),
            ("us-skew/", "期权风险", "保护需求与风险温度"),
            (None, "", ""),
            ("ai-software-security-shovels/", "软件股", "固定股票池 · 轮动 · 量价"),
            ("ai-hardware-shovels/", "硬件股", "SPY基准 · 轮动 · 盘后动作"),
        ]),
    ]
    parts = [
        f'<nav class="csn-topnav" aria-label="全站导航" data-nav-version="{NAV_VERSION}">',
        '<div class="csn-topnav-inner">',
        f'<a class="csn-brand" href="{prefix}" aria-label="CSN 投研首页"><span class="csn-brand-seal">研</span><span><span class="csn-brand-name">CSN 投研</span><span class="csn-brand-sub">Research Desk</span></span></a>',
        '<div class="csn-menu">',
        f'<div class="csn-item csn-home"><a href="{prefix}"{home_current}>首页</a></div>',
    ]
    for key, title, items in groups:
        parts.append(group(prefix, key, title, items, current))
        if key == "macro":
            event_route = current_event_route()
            event_active = " active" if current == event_route or current.startswith(event_route) else ""
            event_current = ' aria-current="page"' if event_active else ""
            parts.append(f'<div class="csn-item{event_active}" data-group="event"><a href="{prefix}{event_route}"{event_current}>事件</a></div>')
    code_active = " active" if current == "code/" else ""
    code_current = ' aria-current="page"' if current == "code/" else ""
    research_active = " active" if current == "nav/" else ""
    research_current = ' aria-current="page"' if current == "nav/" else ""
    parts.extend([
        '<div class="csn-item" data-group="picker"><button type="button" aria-haspopup="true" aria-expanded="false">选股器 <span class="csn-caret" aria-hidden="true">▼</span></button><div class="csn-drop">',
        '<a href="https://docs.google.com/spreadsheets/d/1XEVPTz6SOFWj_Krcp0evHJJU8e28LJ_oCdP6Y0_6-vw/edit" target="_blank" rel="noopener"><b>A股猎龙者信号表</b><small>板块ETF · 自选股 · 机会与风险</small></a>',
        '<a href="https://docs.google.com/spreadsheets/d/1q4SiVx25txwXNZhLwmuU9BQFJ_WVUGau4FjBzvIzXjw/edit" target="_blank" rel="noopener"><b>美股猎龙者信号表</b><small>机会 · 风险警报 · 历史信号</small></a>',
        "</div></div>",
        f'<div class="csn-item{code_active}" data-group="code"><a href="{prefix}code/"{code_current}>代码库</a></div>',
        f'<div class="csn-item{research_active}" data-group="research"><a href="{prefix}nav/"{research_current}>行业调研</a></div>',
        "</div></div></nav>",
    ])
    return "".join(parts)


def ensure_asset_tags(text: str, relative: str) -> str:
    prefix = prefix_for(relative)
    style = f'<link rel="stylesheet" href="{prefix}assets/csnpk-nav.css" data-csnpk-nav-style>'
    script = f'<script src="{prefix}assets/csnpk-nav.js" defer data-csnpk-nav-script></script>'
    text = re.sub(r'\s*<link[^>]+data-csnpk-nav-style[^>]*>', "", text)
    text = re.sub(r'\s*<script[^>]+data-csnpk-nav-script[^>]*></script>', "", text)
    if "</head>" not in text:
        raise SystemExit(f"missing </head> in {relative}")
    return text.replace("</head>", f"{style}\n{script}\n</head>", 1)


def replace_or_insert_nav(text: str, relative: str) -> str:
    canonical = re.compile(r'<nav class="csn-topnav".*?</nav>', re.S)
    if canonical.search(text):
        return canonical.sub(nav(relative), text, count=1)
    body = re.search(r"<body[^>]*>", text, re.I)
    if not body:
        raise SystemExit(f"missing <body> in {relative}")
    start = body.end()
    lead = text[start : start + 5000]
    legacy_header = re.match(r'(\s*<header class="top">.*?</header>)', lead, re.S)
    if legacy_header and "nav" in legacy_header.group(1):
        end = start + legacy_header.end()
        return text[:start] + "\n" + nav(relative) + text[end:]
    legacy_nav = re.match(r'(\s*(?:<!--.*?-->\s*)*<nav\b[^>]*>.*?</nav>)', lead, re.S)
    if legacy_nav:
        candidate = legacy_nav.group(1)
        if any(marker in candidate for marker in ("主导航", "CSNPK", "CSN 投研", 'class="brand"', 'class="nav-brand"')):
            end = start + legacy_nav.end()
            return text[:start] + "\n" + nav(relative) + text[end:]
    return text[:start] + "\n" + nav(relative) + text[start:]


def main() -> None:
    pages = active_pages()
    for relative in pages:
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        updated = ensure_asset_tags(replace_or_insert_nav(text, relative), relative)
        path.write_text(updated, encoding="utf-8")
    for relative in pages:
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        updated = text.replace('href="/csn/"', 'href="/#stock-trends"')
        updated = updated.replace('href="/csn/hot/"', 'href="/#stock-trends"')
        updated = updated.replace('href="/futu-indicators/"', 'href="/code/"')
        updated = re.sub(r'<aside class="us-research-path".*?</aside>', '', updated, flags=re.S)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
    print(f"updated {len(pages)} active pages with navigation {NAV_VERSION}")


if __name__ == "__main__":
    main()
