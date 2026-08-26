#!/usr/bin/env python3
"""Apply one shared CSNPK navigation to every active public page."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NAV_VERSION = "ia-20260823g"
ACTIVE_DYNAMIC = {
    "index.html",
    "a-share-software-deleveraging/index.html",
    "a-share-hardware-deleveraging/index.html",
    "a-share-biotech-trend/index.html",
    "a-share-dividend-defense/index.html",
    "a-share-trend-candidates/index.html",
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
    "us-trend-candidates/index.html",
    "us-skew/index.html",
    "us-market/index.html",
    "macro-fiscal-risk/index.html",
    "macro-event-radar/index.html",
    "code/index.html",
    "bingshen/index.html",
    "csn/index.html",
    "csn/hot/index.html",
    "nav/index.html",
}
RETIRED_REPORT_IDS = {"futu-indicators"}

# Per-page content refresh dates. These are deliberately independent from the
# navigation build time so a shared-nav release never makes every page look new.
PAGE_REFRESH_DATES = {
    "us-market/": "2026-08-25",
    "macro-fiscal-risk/": "2026-08-24",
    "macro-event-radar/": "2026-08-23",
    "us-market/x-consensus/": "2026-08-23",
    "weekly-event-transmission-2026w35/us/": "2026-08-23",
    "weekly-event-transmission-2026w35/a-share/": "2026-08-23",
    "a-share-trend-candidates/": "2026-08-25",
    "a-share-domestic-compute/": "2026-08-23",
    "a-share-supply-tightness/": "2026-08-23",
    "a-share-next-generation/": "2026-08-23",
    "bingshen/": "2026-08-22",
    "a-share-software-deleveraging/": "2026-08-25",
    "a-share-hardware-deleveraging/": "2026-08-25",
    "a-share-biotech-trend/": "2026-08-25",
    "a-share-dividend-defense/": "2026-08-25",
    "us-trend-candidates/": "2026-08-25",
    "rotation/": "2026-08-25",
    "rs-thrust/": "2026-08-25",
    "us-skew/": "2026-08-25",
    "ai-software-security-shovels/": "2026-08-25",
    "ai-hardware-shovels/": "2026-08-25",
    "ai-infrastructure-deleveraging/": "2026-08-25",
}

PICKER_REFRESH_DATES = {
    "A股猎龙者信号表": "2026-08-23",
    "美股猎龙者信号表": "2026-08-23",
}


def current_event_route() -> str:
    event_roots = [
        path for path in ROOT.glob("weekly-event-transmission-*")
        if path.is_dir() and (path / "us/index.html").is_file() and (path / "a-share/index.html").is_file()
    ]
    if not event_roots:
        raise SystemExit("no complete weekly event page set")
    return max(event_roots, key=lambda path: path.name).name + "/"


def active_pages() -> list[str]:
    pages = set(ACTIVE_DYNAMIC)
    event_root = ROOT / current_event_route()
    pages.update(str(path.relative_to(ROOT)) for path in event_root.rglob("index.html"))
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
    refresh = PAGE_REFRESH_DATES.get(path)
    refresh_html = refresh_label(refresh) if refresh else ""
    return f'<a{css} href="{prefix}{path}"><b>{title}{refresh_html}</b><small>{note}</small></a>'


def refresh_label(refresh: str) -> str:
    short = refresh[5:]
    return f' <time class="csn-nav-refresh" datetime="{refresh}" title="内容刷新日期：{refresh}">{short} 更新</time>'


def group(
    prefix: str,
    key: str,
    title: str,
    items: list[tuple[str | None, str, str]],
    current: str,
    active_prefixes: tuple[str, ...] = (),
) -> str:
    paths = {path for path, _, _ in items if path}
    active = " active" if current in paths or any(current.startswith(path) for path in active_prefixes) else ""
    out = [
        f'<div class="csn-item{active}" data-group="{key}">',
        f'<button type="button" aria-haspopup="true" aria-expanded="false">{title} <span class="csn-caret" aria-hidden="true">▼</span></button>',
        '<div class="csn-drop">',
    ]
    for path, label, note in items:
        if path is None:
            out.append('<div class="csn-drop-separator" role="separator" aria-label="栏目分隔线"></div>')
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
            ("macro-event-radar/", "全球核心事件雷达", "政策 · 加密 · AI · 事件传导"),
            ("us-market/x-consensus/", "全球注意力雷达", "中文X · 多语种长文 · Reddit · 作者原图"),
        ]),
        ("a-tools", "A股", [
            ("a-share-trend-candidates/", "趋势候选", "主升 · 回调 · 反转 · T+1"),
            ("a-share-domestic-compute/", "国产算力", "芯片 · 服务器 · 网络 · AIDC"),
            ("a-share-supply-tightness/", "供需紧张", "存储 · PCB · 材料 · 制造"),
            ("a-share-next-generation/", "下一代技术", "光互连 · CPO · 液冷 · 连接"),
            ("bingshen/", "冰神分享", "A股观察池 · 名单与代码文件"),
            (None, "", ""),
            ("a-share-software-deleveraging/", "软件股", "相对强弱 · 趋势结构 · 风险边界"),
            ("a-share-hardware-deleveraging/", "硬件股", "算力硬件 · 趋势结构 · 细分轮动"),
            ("a-share-biotech-trend/", "生物科技", "医药生物 · 相对强弱 · 趋势结构"),
            ("a-share-dividend-defense/", "红利防守", "银行 · 公用事业 · 稳定现金流"),
        ]),
        ("us-tools", "美股", [
            ("us-trend-candidates/", "趋势候选", "硬件 · 软件 · AI4S · 加密"),
            ("rotation/", "轮动加速度", "看顶部衰竭与底部修复"),
            ("rs-thrust/", "相对强度", "找正在加速的强势股"),
            ("us-skew/", "期权风险", "保护需求与风险温度"),
            (None, "", ""),
            ("ai-software-security-shovels/", "软件股", "固定股票池 · 轮动 · 量价"),
            ("ai-hardware-shovels/", "硬件股", "SPY基准 · 轮动 · 盘后动作"),
            ("ai-infrastructure-deleveraging/", "AI基础设施", "SOXX · 光通信 · 设备 · 算力"),
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
            parts.append(group(prefix, "event", "事件", [
                (f"{event_route}us/", "美股事件", "重大事件 · 财报 · 宏观传导"),
                (f"{event_route}a-share/", "A股财报", "预约披露 · 预期管理 · 行业映射"),
            ], current, active_prefixes=(event_route,)))
    code_active = " active" if current == "code/" else ""
    code_current = ' aria-current="page"' if current == "code/" else ""
    research_active = " active" if current == "nav/" else ""
    research_current = ' aria-current="page"' if current == "nav/" else ""
    parts.extend([
        '<div class="csn-item" data-group="picker"><button type="button" aria-haspopup="true" aria-expanded="false">选股器 <span class="csn-caret" aria-hidden="true">▼</span></button><div class="csn-drop">',
        f'<a href="https://docs.google.com/spreadsheets/d/1XEVPTz6SOFWj_Krcp0evHJJU8e28LJ_oCdP6Y0_6-vw/edit" target="_blank" rel="noopener"><b>A股猎龙者信号表{refresh_label(PICKER_REFRESH_DATES["A股猎龙者信号表"])}</b><small>板块ETF · 自选股 · 机会与风险</small></a>',
        f'<a href="https://docs.google.com/spreadsheets/d/1q4SiVx25txwXNZhLwmuU9BQFJ_WVUGau4FjBzvIzXjw/edit" target="_blank" rel="noopener"><b>美股猎龙者信号表{refresh_label(PICKER_REFRESH_DATES["美股猎龙者信号表"])}</b><small>机会 · 风险警报 · 历史信号</small></a>',
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


def ensure_external_link_safety(text: str) -> str:
    anchor = re.compile(r'<a\b[^>]*\btarget=["\']_blank["\'][^>]*>', re.I)

    def repair(match: re.Match[str]) -> str:
        tag = match.group(0)
        rel_match = re.search(r'\brel=(["\'])(.*?)\1', tag, re.I)
        if rel_match:
            values = rel_match.group(2).split()
            for value in ("noopener", "noreferrer"):
                if value not in values:
                    values.append(value)
            replacement = f'rel={rel_match.group(1)}{" ".join(values)}{rel_match.group(1)}'
            return tag[:rel_match.start()] + replacement + tag[rel_match.end():]
        return tag[:-1] + ' rel="noopener noreferrer">'

    return anchor.sub(repair, text)


def main() -> None:
    pages = active_pages()
    for relative in pages:
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        updated = ensure_external_link_safety(
            ensure_asset_tags(replace_or_insert_nav(text, relative), relative)
        )
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
