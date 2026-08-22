#!/usr/bin/env python3
"""Generate three focused A-share industry-map pages from the audited master page."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_HTML = ROOT / "a-share-t1-focus/index.html"
SOURCE_DATA = ROOT / "a-share-t1-focus/data.json"

PAGES = (
    {
        "slug": "a-share-domestic-compute",
        "mainline": "国产算力",
        "matrix": "国产算力核心矩阵",
        "title": "国产算力产业链图谱",
        "eyebrow": "A-SHARE · DOMESTIC COMPUTE · EVIDENCE MAP",
        "description": "聚焦国产AI芯片、服务器、交换网络、内存互连、EDA、AIDC与算力服务的产业链映射。",
        "core_key": "domestic_compute_core",
    },
    {
        "slug": "a-share-supply-tightness",
        "mainline": "AI供需紧张",
        "matrix": "AI供需紧张矩阵",
        "title": "供需紧张产业链图谱",
        "eyebrow": "A-SHARE · SUPPLY TIGHTNESS · EVIDENCE MAP",
        "description": "聚焦AI服务器、存储、先进封装、PCB、半导体材料、晶圆制造与数据中心电力的供需环节。",
        "core_key": "ai_supply_tightness_core",
    },
    {
        "slug": "a-share-next-generation",
        "mainline": "下一代技术",
        "matrix": "下一代技术矩阵",
        "title": "下一代技术产业链图谱",
        "eyebrow": "A-SHARE · NEXT GENERATION · EVIDENCE MAP",
        "description": "聚焦800G/1.6T、NPO/CPO、硅光测试、高速连接、薄膜铌酸锂与液冷等下一代技术。",
        "core_key": "next_generation_core",
    },
)


def matrix_block(source: str, heading: str) -> str:
    match = re.search(
        rf"    <h3>{re.escape(heading)}</h3>.*?(?=\n    <h3>|\n  </section>)",
        source,
        re.S,
    )
    if not match:
        raise SystemExit(f"matrix not found: {heading}")
    return match.group(0)


def unique_stocks(rows: list[dict[str, str]]) -> list[str]:
    names: list[str] = []
    for row in rows:
        raw = re.sub(r"(?:观察|验证)：", "", row["stocks"])
        for name in re.split(r"[、；]", raw):
            clean = re.sub(r"（.*?）", "", name).strip()
            if clean and clean not in names:
                names.append(clean)
    return names


def render_page(source: str, data: dict, spec: dict[str, str]) -> tuple[str, dict]:
    rows = [row for row in data["industry_map"] if row["mainline"] == spec["mainline"]]
    names = unique_stocks(rows)
    core_count = len(data["classification"][spec["core_key"]])
    matrix = matrix_block(source, spec["matrix"])
    universe = (
        '  <section class="section" id="universe"><div class="head"><h2>产业环节与股票映射</h2>'
        f'<span>{len(rows)} SEGMENTS · {len(names)} NAMES</span></div>'
        '<p class="lead">证据状态分三类：绿色为公司公告/年报已核验；黄色为官方证据与本地情报交叉后仍需跟踪兑现；红色为只有情报线索或关键说法未获官方确认。</p>\n'
        f'    <div class="countbar"><div class="countbox"><b>{len(rows)}</b><span>产业环节</span></div>'
        f'<div class="countbox"><b>{core_count}</b><span>主线核心</span></div>'
        f'<div class="countbox"><b>{len(names)}</b><span>页面涉及公司</span></div></div>\n'
        f"{matrix}\n  </section>"
    )
    page = re.sub(r'  <section class="section" id="universe">.*?\n  </section>', universe, source, count=1, flags=re.S)
    page = re.sub(r'\n  <section class="section" id="related">.*?</section>', "", page, count=1, flags=re.S)
    page = re.sub(
        r'<meta name="description"[^>]*><meta property="og:title"[^>]*>',
        f'<meta name="description" content="{spec["description"]}"><meta property="og:title" content="{spec["title"]}｜CSN投研">',
        page,
        count=1,
    )
    page = re.sub(r'<title>.*?</title>', f'<title>{spec["title"]}｜CSN投研</title>', page, count=1)
    page = re.sub(
        r'  <header class="hero">.*?</header>',
        f'  <header class="hero"><div class="eyebrow">{spec["eyebrow"]}</div><h1>{spec["title"]}</h1><p>{spec["description"]} 按“产业环节 → 供需逻辑 → 对应公司 → 证据状态”展示，不提供当日买入排序。</p><div class="pills"><span class="pill">审计日：{data["research_date"]}</span><span class="pill">公司公告/年报优先</span><span class="pill">冲突项降级为待证真</span></div></header>',
        page,
        count=1,
        flags=re.S,
    )
    links = "".join(
        f'<a href="../{item["slug"]}/">{item["title"]}</a>' for item in PAGES
    )
    page = re.sub(
        r'  <aside class="card toc">.*?</aside>',
        f'  <aside class="card toc"><nav>{links}<a href="#sources">来源与边界</a></nav></aside>',
        page,
        count=1,
        flags=re.S,
    )
    page = page.replace(
        '机器可读映射见 <a href="./data.json">data.json</a>',
        '本页机器可读映射见 <a href="./data.json">data.json</a>；全量主表见 <a href="../a-share-t1-focus/data.json">原始 data.json</a>',
    )
    page = re.sub(
        r'<p class="footer">.*?</p>',
        f'<p class="footer">CSN投研 · {spec["title"]}，不构成投资建议</p>',
        page,
        count=1,
    )
    focused_data = {
        "version": data["version"],
        "research_date": data["research_date"],
        "page_scope": "single_mainline_industry_map",
        "mainline": spec["mainline"],
        "source_route": "/a-share-t1-focus/",
        "counts": {"segments": len(rows), "core": core_count, "unique_names": len(names)},
        "core_stocks": data["classification"][spec["core_key"]],
        "industry_map": rows,
        "evidence_policy": data["evidence_policy"],
        "primary_sources": data["primary_sources"],
        "obsidian_sources": data["obsidian_sources"],
    }
    return page, focused_data


def main() -> None:
    source = SOURCE_HTML.read_text(encoding="utf-8")
    data = json.loads(SOURCE_DATA.read_text(encoding="utf-8"))
    for spec in PAGES:
        page, focused_data = render_page(source, data, spec)
        output = ROOT / spec["slug"]
        output.mkdir(parents=True, exist_ok=True)
        (output / "index.html").write_text(page, encoding="utf-8")
        (output / "data.json").write_text(
            json.dumps(focused_data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print("generated 3 focused A-share industry-map pages")


if __name__ == "__main__":
    main()
