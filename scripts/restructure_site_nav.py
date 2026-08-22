#!/usr/bin/env python3
"""Apply the canonical CSNPK navigation to the active public pages."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

def prefix_for(relative: str) -> str:
    depth = len(Path(relative).parts) - 1
    return "./" if depth == 0 else "../" * depth


def link(prefix: str, path: str, title: str, note: str, current: str) -> str:
    css = ' class="current"' if current == path else ""
    return f'<a{css} href="{prefix}{path}"><b>{title}</b><small>{note}</small></a>'


def nav(relative: str) -> str:
    prefix = prefix_for(relative)
    current = str(Path(relative).parent).replace(".", "")
    current = f"{current}/" if current else ""
    home = prefix
    groups = [
        (
            "a-tools",
            "A股",
            [
                ("a-share-t1-focus/", "A股 T+1 条件关注", "产业主线 · 多周期 · 次日预案"),
                ("a-share-software-deleveraging/", "A股软件走势总结", "去杠杆 · 二次确认 · 个股分化"),
                ("a-share-hardware-deleveraging/", "A股AI硬件走势总结", "算力硬件 · 二次确认 · 个股分化"),
            ],
        ),
        (
            "us-tools",
            "美股",
            [
                ("rs-thrust/", "美股相对强度加速图", "找正在加速的强势股"),
                ("rotation/", "美股轮动加速度雷达", "看顶部衰竭与底部修复"),
                ("ai-software-security-shovels/", "AI 软件与安全监控台", "固定股票池 · 轮动 · 量价"),
                ("ai-hardware-shovels/", "AI 硬件铲子监控台", "SPY基准 · 轮动 · 盘后动作"),
                ("us-skew/", "美股期权风险分布图", "保护需求与风险温度"),
            ],
        ),
        (
            "market",
            "大盘观察",
            [
                ("us-market/", "美股大盘观察", "指数状态 · 风险温度 · 风格轮动"),
                ("macro-fiscal-risk/", "财政风险溢价监控", "长端 · 美元 · 股债 · 信用扩散"),
                ("ai-decision/", "中韩美市场进度", "回调出清 · 去杠杆 · 技术广度"),
            ],
        ),
    ]
    parts = [
        '<nav class="csn-topnav" aria-label="全站导航" data-nav-version="ia-20260822">',
        '<div class="csn-topnav-inner">',
        f'<a class="csn-brand" href="{home}"><span class="csn-brand-seal">研</span><span><span class="csn-brand-name">CSN 投研</span><span class="csn-brand-sub">Research Desk</span></span></a>',
        '<div class="csn-menu">',
    ]
    for key, title, items in groups:
        parts.append(f'<div class="csn-item" data-group="{key}"><button type="button" aria-haspopup="true" aria-expanded="false">{title} <span class="csn-caret">▼</span></button><div class="csn-drop">')
        for path, item_title, note in items:
            parts.append(link(prefix, path, item_title, note, current))
        parts.append("</div></div>")
    parts.extend(
        [
            '<div class="csn-item" data-group="picker"><button type="button" aria-haspopup="true" aria-expanded="false">选股器 <span class="csn-caret">▼</span></button><div class="csn-drop">',
            '<a href="https://docs.google.com/spreadsheets/d/1XEVPTz6SOFWj_Krcp0evHJJU8e28LJ_oCdP6Y0_6-vw/edit" target="_blank" rel="noopener"><b>A股猎龙者信号表</b><small>板块ETF · 自选股 · 机会与风险</small></a>',
            '<a href="https://docs.google.com/spreadsheets/d/1q4SiVx25txwXNZhLwmuU9BQFJ_WVUGau4FjBzvIzXjw/edit" target="_blank" rel="noopener"><b>美股猎龙者信号表</b><small>机会 · 风险警报 · 历史信号</small></a>',
            "</div></div>",
            f'<div class="csn-item" data-group="code"><a href="{prefix}code/" data-key="code">代码库</a></div>',
            f'<div class="csn-item" data-group="bingshen"><a href="{prefix}bingshen/" data-key="bingshen">冰神分享</a></div>',
            f'<div class="csn-item" data-group="research"><a href="{prefix}nav/" data-key="nav">行业调研</a></div>',
            "</div></div></nav>",
        ]
    )
    return "".join(parts)


def main() -> None:
    pattern = re.compile(r'<nav class="csn-topnav".*?</nav>', re.S)
    pages = []
    for path in ROOT.rglob("index.html"):
        text = path.read_text(encoding="utf-8")
        if '<nav class="csn-topnav"' in text:
            pages.append((str(path.relative_to(ROOT)), path, text))
    for relative, path, text in pages:
        updated, count = pattern.subn(nav(relative), text, count=1)
        if count != 1:
            raise SystemExit(f"expected one canonical nav in {relative}, found {count}")
        path.write_text(updated, encoding="utf-8")

    # Remove the two retired-from-navigation stock destinations from bespoke
    # historical report headers, and point the old code entry at the new hub.
    for path in ROOT.rglob("index.html"):
        text = path.read_text(encoding="utf-8")
        updated = text.replace('href="/csn/"', 'href="/#stock-trends"')
        updated = updated.replace('href="/csn/hot/"', 'href="/#stock-trends"')
        updated = updated.replace('href="/futu-indicators/"', 'href="/code/"')
        updated = re.sub(r'<aside class="us-research-path".*?</aside>', '', updated, flags=re.S)
        if updated != text:
            path.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()
