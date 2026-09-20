#!/usr/bin/env python3
"""Render the full independently verified A/B/C pool and A观察 top ten."""
from __future__ import annotations
import argparse
import hashlib
import html
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "outputs/a_trend_candidates_page"
DEFAULT_FUTU_TABS = ROOT / "config/a_trend_candidate_futu_tabs.json"
DEFAULT_TAXONOMY = ROOT / "config/a_trend_industry_taxonomy.json"
DEFAULT_SHORTAGE = ROOT / "outputs/a_observe_shortage/20260916/full_inventory.json"
FUTU_TAB_ORDER = ("半导体", "光", "PCB")

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def esc(value):
    return html.escape(str(value), quote=True)

def price(value):
    return "—" if value is None else f"{float(value):.2f}"

def classes_for(row):
    return (["A"] if row["A_confirmed"] or row.get("A_observation") else []) + (["B"] if row["B"]["eligible"] else []) + (["C"] if row["C"]["candidate"] else [])

def technology_for(row):
    sector = row.get("source_sector")
    return "科技" if row["technology"] else "已核验非科技" if row["kind"] == "股票" and sector not in (None, "", "未分类") else "未分类/ETF"

def taxonomy_index(path=DEFAULT_TAXONOMY):
    path = Path(path)
    source = read(path)
    assert source["schema_version"] == "a_trend_industry_taxonomy_v1", "产业分类版本不匹配"
    mapping = source["industry_to_broad"]
    order = source["broad_order"]
    assert set(mapping.values()).issubset(set(order)), "产业大类未登记排序"
    return source, mapping

def classification_fields(row, mapping):
    industry = row["industry"][1]
    broad = "ETF/未分类" if row["kind"] != "股票" else mapping.get(industry)
    assert broad, f"行业未配置两级分类：{industry}"
    return {"broad_category": broad, "industry": industry, "classification_path": f"{broad} → {industry}"}

def shortage_index(path=DEFAULT_SHORTAGE):
    path = Path(path)
    rows = read(path)
    assert len(rows) == 23, "缺货线索类别数量不是23"
    index = {}
    for row in rows:
        assert row.get("url", "").startswith("https://github.com/"), f"缺少原文链接：{row['theme']}"
        for name in row["names"]:
            index.setdefault(name, []).append({
                "theme": row["theme"], "summary": row["summary"], "url": row["url"], "source_date": row["source_date"]
            })
    assert len(index) == 55, "缺货线索公司数量不是55"
    return rows, index

def futu_tab_index(path=DEFAULT_FUTU_TABS):
    path = Path(path)
    source = read(path)
    assert source["schema_version"] == "codex_history_futu_tabs_v1", "富途页卡元数据版本不匹配"
    assert tuple(source["groups"]) == FUTU_TAB_ORDER, "富途页卡顺序或名称不匹配"
    index = {}
    group_counts = {}
    for group in FUTU_TAB_ORDER:
        members = source["groups"][group]["members"]
        codes = [row["code"] for row in members]
        assert len(codes) == len(set(codes)), f"{group}页卡成员重复"
        group_counts[group] = len(members)
        for member in members:
            entry = index.setdefault(member["code"], {"name": member["name"], "tabs": [], "notes": []})
            assert entry["name"] == member["name"], f"页卡证券名称冲突：{member['code']}"
            entry["tabs"].append(group)
            note = member.get("note", "").strip()
            if note and note not in entry["notes"]:
                entry["notes"].append(note)
    for entry in index.values():
        entry["note"] = "；".join(entry.pop("notes")) or "历史对话仅确认页卡归属，未找到独立个股备注。"
    return source, index, group_counts

def theme_fields(code, index):
    entry = index.get(code)
    if not entry:
        return {"futu_tabs": [], "futu_tab_label": "未归入三页卡", "conversation_note": "—"}
    return {"futu_tabs": entry["tabs"], "futu_tab_label": " / ".join(entry["tabs"]), "conversation_note": entry["note"]}

def public_data(run, futu_tabs_path=DEFAULT_FUTU_TABS, taxonomy_path=DEFAULT_TAXONOMY, shortage_path=DEFAULT_SHORTAGE):
    run = Path(run).resolve()
    paths = [run / name for name in ("result.json", "sync.json", "trade_plan.json")]
    result, sync, plan = map(read, paths)
    theme_source, theme_index, theme_group_counts = futu_tab_index(futu_tabs_path)
    taxonomy_source, taxonomy = taxonomy_index(taxonomy_path)
    shortage_rows, shortage = shortage_index(shortage_path)
    assert result["asof"] == sync["asof"] == plan["asof"], "信号日期不一致"
    assert result["next_session"] == sync["next_session"] == plan["next_session"], "次日日期不一致"
    assert result.get("C_source_verified") is True, "C类当日来源未验收"
    assert sync.get("final_readback_ok") and plan.get("watchlist_sync_ok"), "A观察独立回读未通过"
    top = result["top"]
    assert 0 < len(top) <= 10, "名单为空或超限"
    target = {row["code"]: row["name"] for row in top}
    assert len(target) == len(top) and sync["target"] == target, "目标名单不一致"
    assert {row["code"]: row["name"] for row in sync["independent_after"]} == target, "独立回读不一致"
    plans = {row["code"]: row for row in plan["stocks"]}
    assert set(plans) == set(target), "点位与名单不一致"
    source_count = int(result["source_count"])
    covered = len(result["rows"])
    assert source_count and covered / source_count >= .9, "行情覆盖不足90%"
    stocks = []
    for rank, row in enumerate(top, 1):
        classes = classes_for(row)
        assert classes and row["eligible"], "入选资格与类别不一致"
        b, c, p = row["B"], row["C"], plans[row["code"]]
        technology = technology_for(row)
        classification = classification_fields(row, taxonomy)
        shortage_refs = shortage.get(row["name"], [])
        stocks.append({
            "rank": rank, "code": row["code"], "name": row["name"], "kind": row["kind"], "origin": row["origin"],
            "classes": classes, "technology": technology, **classification, "technology_evidence": row.get("technology_evidence"),
            "shortage_flag": bool(shortage_refs), "shortage_themes": [x["theme"] for x in shortage_refs], "shortage_refs": shortage_refs,
            "A": {"key_date": row["A"]["key_date"], "day": row["A"]["day"], "invalid": row["A"]["invalid"], "confirmed": bool(row["A_confirmed"]), "pending_conditions": row.get("A_pending_conditions", [])} if row["A_confirmed"] or row.get("A_observation") else None,
            "B": {"shape": row["shape"], "state": b["state"], "bottom_date": b["bottom_date"], "invalid": b["invalid"],
                  "macd_cross": b.get("macd_cross"), "kdj_cross": b.get("kdj_cross"), "volume_previous": row["volume_ratio_previous"]} if b["eligible"] else None,
            "C": {"setups": c["setups"], "stage": c["stage"], "momentum": c["momentum"]["stage"],
                  "volume_previous5": c.get("volume_vs_previous5"), "research_invalid": c["research_invalid_below"]} if c["candidate"] else None,
            "points": {key: p.get(key) for key in ("close", "observation", "confirmation", "maximum_acceptable", "invalid", "first_reduce", "final_target")},
            "point_status": p["execution_status"], "market_gate": p["market_gate"],
            **theme_fields(row["code"], theme_index),
        })
    counts = {key: sum(key in row["classes"] for row in stocks) for key in "ABC"}
    nontech = sum(row["technology"] == "已核验非科技" for row in stocks)
    quota_max = result.get("selection_policy", {}).get("nontechnology_stock_quota_max", 4)
    if quota_max is not None:
        assert nontech <= quota_max, "非科技数量不符合本轮记录的历史规则"
    ranked = result["ranked"]
    assert ranked and len({row["code"] for row in ranked}) == len(ranked), "完整备选为空或重复"
    assert set(target).issubset({row["code"] for row in ranked}), "前10未包含于完整备选"
    assert {row["code"] for row in ranked} == {row["code"] for row in result["rows"] if row["eligible"] and row["industry"]}, "完整备选缺漏"
    candidates = []
    for rank, row in enumerate(ranked, 1):
        classes = classes_for(row)
        assert classes and row["eligible"], "备选资格与类别不一致"
        b, c, a = row["B"], row["C"], row["A"]
        stage = (row["shape"] + "／" + b["state"]) if b["eligible"] else c["stage"] if c["candidate"] else "关K回调第%d日" % a["day"]
        if c["candidate"] and b["eligible"]:
            stage += "；C·" + "、".join(c["setups"]) + "／" + c["stage"]
        if row.get("A_observation"):stage += "；A·板块2/3观察，待补：" + "；".join(row["A_pending_conditions"])
        crosses = [label + "金叉 " + b[key] for label, key in (("MACD", "macd_cross"), ("KDJ", "kdj_cross")) if b["eligible"] and b.get(key)]
        invalid = b["invalid"] if b["eligible"] else c["research_invalid_below"] if c["candidate"] else a["invalid"]
        bottom_date = b["bottom_date"] if b["eligible"] else c.get("episode", {}).get("trough_date") if c["candidate"] else a["key_date"]
        classification = classification_fields(row, taxonomy)
        shortage_refs = shortage.get(row["name"], [])
        candidates.append({
            "rank": rank, "code": row["code"], "name": row["name"], "kind": row["kind"], "origin": row["origin"],
            "classes": classes, "top10": row["code"] in target, "technology": technology_for(row), **classification,
            "shortage_flag": bool(shortage_refs), "shortage_themes": [x["theme"] for x in shortage_refs], "shortage_refs": shortage_refs,
            "stage": stage, "close": row["close"], "volume_previous": row["volume_ratio_previous"] if b["eligible"] else None,
            "volume_previous5": c.get("volume_vs_previous5") if c["candidate"] else None,
            "bottom_date": bottom_date, "invalid": invalid, "crosses": crosses,
            "momentum": c["momentum"]["stage"] if c["candidate"] else b.get("macd_status",b["state"]) if b["eligible"] else "板块2/3待补观察" if row.get("A_observation") else "A类独立入选",
            "A_confirmed": bool(row["A_confirmed"]), "A_observation": bool(row.get("A_observation")), "A_pending_conditions": row.get("A_pending_conditions", []),
            **theme_fields(row["code"], theme_index),
        })
    from a_observe_daily.group_notes import load_notes
    group_notes, group_notes_at = load_notes(run)
    for item in candidates + stocks:
        item['other_groups'] = group_notes.get(item['code'], [])
        if item['other_groups']:
            item['conversation_note'] = '主题备注：' + '、'.join(item['other_groups'])
    from a_observe_daily.b_age import b_age
    original_rows = {x['code']: x for x in result['rows']}
    for item in candidates:
        age = b_age(original_rows[item['code']], run, result['asof'])
        if age:item['stage'] += '；' + age
    candidate_counts = {key: sum(key in row["classes"] for row in candidates) for key in "ABC"}
    matched_tab_counts = {key: sum(key in row["futu_tabs"] for row in candidates) for key in FUTU_TAB_ORDER}
    broad_counts = {key: sum(row["broad_category"] == key for row in candidates) for key in taxonomy_source["broad_order"]}
    industry_counts = dict(sorted(__import__("collections").Counter(row["industry"] for row in candidates).items()))
    shortage_candidate_count = sum(row["shortage_flag"] for row in candidates)
    return {
        "schema_version": "a_observe_abc_full_v4", "data_date": result["asof"], "next_session": result["next_session"],
        "generated_at_bj": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "source_count": source_count, "covered_count": covered, "coverage_ratio": round(covered / source_count, 4),
        "C_pool_count": sum(bool(row["C"]["candidate"]) for row in result["rows"]),
        "selected_count": len(stocks), "class_counts": counts, "verified_nontechnology_count": nontech,
        "candidate_count": len(candidates), "candidate_class_counts": candidate_counts, "candidates": candidates,
        "taxonomy_snapshot": {"asof": taxonomy_source["asof"], "source": taxonomy_source["source"],
                              "broad_order": taxonomy_source["broad_order"], "broad_counts": broad_counts,
                              "industry_counts": industry_counts},
        "shortage_snapshot": {"asof": max(row["source_date"] for row in shortage_rows), "theme_count": len(shortage_rows),
                               "company_count": len(shortage), "matched_candidate_count": shortage_candidate_count,
                               "page": "../a-share-shortage-watch/"},
        "futu_tab_snapshot": {"asof": theme_source["asof"], "source": theme_source["source"], "group_counts": theme_group_counts,
                              "matched_candidate_counts": matched_tab_counts},
        "watchlist_readback_ok": True, "C_source_verified": True, "execution_ready": bool(plan["execution_ready"]),
        "price_plan_complete": bool(plan["price_plan_complete"]), "selection_policy": result["selection_policy"],
        "stocks": stocks, "evidence": {**dict(zip(("result_sha256", "sync_sha256", "trade_plan_sha256"), map(digest, paths))),
                                        "futu_tabs_sha256": digest(Path(futu_tabs_path)),
                                        "taxonomy_sha256": digest(Path(taxonomy_path)),
                                        "shortage_inventory_sha256": digest(Path(shortage_path))},
    }

def render_stock(row):
    tags = "".join('<span class="pill pill-%s">%s</span>' % (key, key) for key in row["classes"])
    b, c, a, p = row["B"], row["C"], row["A"], row["points"]
    stage = (b["shape"] + "／" + b["state"]) if b else c["stage"] if c else "关K回调第%d日" % a["day"]
    evidence = []
    if row.get('other_groups'):evidence.append('主题备注：'+'、'.join(row['other_groups']))
    if a:
        if a.get("pending_conditions"):evidence.append("A·板块2/3待补观察：" + "；".join(a["pending_conditions"]))
        evidence.append("A｜关K回调第%d日；关K %s；结构失效参考 %s。" % (a["day"], a["key_date"], price(a["invalid"])))
    if b:
        crosses = "、".join(x for x in (("MACD金叉 " + b["macd_cross"]) if b["macd_cross"] else None,
                                       ("KDJ金叉 " + b["kdj_cross"]) if b["kdj_cross"] else None) if x) or "金叉前动能酝酿"
        evidence.append("B｜%s／%s；本轮底 %s（%s）；%s；最新/前日量 %.2f倍。" %
                        (b["shape"], b["state"], b["bottom_date"], price(b["invalid"]), crosses, b["volume_previous"]))
    if c:
        volume = "；最新/前5日均量 %.2f倍" % c["volume_previous5"] if c["volume_previous5"] is not None else ""
        evidence.append("C｜%s；%s；%s；研究失效参考 %s%s。" %
                        ("、".join(c["setups"]), c["stage"], c["momentum"], price(c["research_invalid"]), volume))
    points = []
    for key, label in (("observation", "第一观察"), ("confirmation", "收盘确认"), ("invalid", "结构失效"),
                       ("maximum_acceptable", "最高接受"), ("first_reduce", "第一减仓参考"), ("final_target", "最终目标参考")):
        if p[key] is not None:
            points.append('<div class="point"><span>%s</span><strong>%s</strong></div>' % (label, price(p[key])))
    if p["maximum_acceptable"] is None:
        points.append('<p class="no-price">暂无有效最高接受价；等待结构改善，暂不执行。</p>')
    search = " ".join((row["code"], row["name"], row["broad_category"], row["industry"], stage, *row["classes"], *row["shortage_themes"])).lower()
    shortage = ('<a class="shortage-tag" href="../a-share-shortage-watch/">供给线索 · %s</a>' % esc(" / ".join(row["shortage_themes"]))) if row["shortage_flag"] else ""
    return ('<article class="stock" data-search="%s" data-classes="%s" data-category="%s" data-industry="%s">'
            '<div class="stock-head"><span class="rank">%02d</span><div><h2>%s <small>%s</small></h2>'
            '<p class="sector">%s · %s</p>%s</div><div class="tags">%s</div></div>'
            '<p class="stage">%s</p><p class="status">%s · 市场闸门：%s · 最新完整日K收盘 %s</p>'
            '<div class="points">%s</div><details><summary>结构与动能依据</summary>%s</details></article>' %
            (esc(search), esc(" ".join(row["classes"])), esc(row["broad_category"]), esc(row["industry"]), row["rank"], esc(row["name"]), esc(row["code"]),
             esc(row["classification_path"]), esc(row["origin"]), shortage, tags, esc(stage), esc(row["point_status"]),
             esc(row["market_gate"]), price(p["close"]), "".join(points),
             "".join("<p>%s</p>" % esc(line) for line in evidence)))

def render_candidate(row):
    tags = "".join('<span class="pill pill-%s">%s</span>' % (key, key) for key in row["classes"])
    volume = []
    if row["volume_previous"] is not None:
        volume.append("前日 %.2f倍" % row["volume_previous"])
    if row["volume_previous5"] is not None and "C" in row["classes"]:
        volume.append("前5日均量 %.2f倍" % row["volume_previous5"])
    volume_text = "；".join(volume) or "量比未核验"
    cross_text = "、".join(row["crosses"]) or row["momentum"]
    invalid_label = "研究失效参考" if row["classes"] == ["C"] else "结构底/失效"
    invalid_text = "%s %s" % (invalid_label, price(row["invalid"]))
    bottom = (row["bottom_date"] + " · ") if row["bottom_date"] else ""
    tabs = " ".join(row["futu_tabs"])
    shortage_text = " / ".join(row["shortage_themes"])
    shortage_cell = ('<a class="shortage-tag" href="../a-share-shortage-watch/">%s</a>' % esc(shortage_text)) if shortage_text else "—"
    search = " ".join((row["code"], row["name"], row["industry"], row["stage"], row["broad_category"],
                       row["futu_tab_label"], row["conversation_note"], shortage_text, *row["classes"])).lower()
    return ('<tr data-search="%s" data-classes="%s" data-category="%s" data-industry="%s" data-shortage="%s" data-futu-tabs="%s" data-top="%s" data-rank="%d" '
            'data-name="%s" data-futu-tab="%s" data-note="%s" data-stage="%s" data-crosses="%s" data-invalid="%.5f" data-close="%.5f" data-volume="%.5f"%s>'
            '<td data-label="排序" class="num">%d</td><td data-label="股票" class="identity"><b>%s</b><small>%s</small></td>'
            '<td data-label="类别">%s</td>'
            '<td data-label="当前阶段" class="stage-cell">%s</td><td data-label="收盘" class="num">%.2f</td>'
            '<td data-label="量能">%s</td><td data-label="结构底/失效">%s</td><td data-label="动能">%s</td>'
            '<td data-label="产业分类" class="classify-cell">%s</td><td data-label="缺货/供给线索" class="shortage-cell">%s</td><td data-label="对话备注" class="note-cell">%s</td>'
            '<td data-label="跟踪">%s</td></tr>' %
            (esc(search), esc(" ".join(row["classes"])), esc(row["broad_category"]), esc(row["industry"]), "yes" if row["shortage_flag"] else "no", esc(tabs), "yes" if row["top10"] else "no",
             row["rank"], esc(row["name"]), esc(row["futu_tab_label"]), esc(row["conversation_note"]), esc(row["stage"]), esc(cross_text), row["invalid"], row["close"],
             row["volume_previous"] if row["volume_previous"] is not None else row["volume_previous5"] if row["volume_previous5"] is not None else -1,
             ' class="priority-row"' if row["top10"] else "", row["rank"], esc(row["name"]), esc(row["code"]),
             tags, esc(row["stage"]), row["close"], esc(volume_text), esc(bottom + invalid_text), esc(cross_text),
             esc(row["classification_path"]), shortage_cell, esc(row["conversation_note"]),
             '<b class="focus">重点前10</b>' if row["top10"] else "完整备选"))

def render_table(data):
    rows = "\n".join(render_candidate(row) for row in data["candidates"])
    buttons = [("rank", "排序"), ("name", "股票"), ("classes", "类别"), ("stage", "当前阶段"),
               ("close", "收盘"), ("volume", "量能"), ("invalid", "结构底/失效"), ("crosses", "动能"),
               ("category", "产业分类"), ("shortage", "缺货/供给线索"), ("note", "对话备注"), ("top", "跟踪")]
    heads = "".join('<th><button type="button" data-sort="%s">%s</button></th>' % (key, label) for key, label in buttons)
    return ('<section class="pool"><div class="pool-head"><h2>完整条件候选（含待补观察）</h2><p>本轮 %d 只，A %d · B %d · C %d（重叠计数）；前10在表内标为“重点前10”，其余股票未生成买卖点位。</p></div>'
            '<div class="pool-toolbar"><input id="poolSearch" type="search" placeholder="搜索代码、名称、行业、阶段或备注" aria-label="搜索完整备选">'
            '<select id="poolClass" aria-label="备选类别"><option value="">全部类别</option><option value="A">A 关K回调</option><option value="B">B 回落转稳</option><option value="C">C 主升延续</option></select>'
            '<select id="poolFutuTab" aria-label="富途页卡分类"><option value="">全部页卡</option><option value="半导体">半导体</option><option value="光">光</option><option value="PCB">PCB</option><option value="none">未归入三页卡</option></select>'
            '<select id="poolCategory" aria-label="一级产业分类"><option value="">全部大类</option>%s</select>'
            '<select id="poolIndustry" aria-label="二级行业分类"><option value="">全部细分行业</option>%s</select>'
            '<select id="poolShortage" aria-label="缺货或供给线索"><option value="">全部供给状态</option><option value="yes">有缺货/供给线索</option><option value="no">无相关线索</option></select>'
            '<select id="poolTop" aria-label="重点观察"><option value="">全部候选</option><option value="yes">重点前10</option><option value="no">其余备选</option></select>'
            '<button id="poolReset" type="button">重置</button></div><p class="result" id="poolCount">显示 %d / %d 只 · 点击表头排序</p>'
            '<div class="table-wrap"><table id="candidateTable"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div></section>' %
            (data["candidate_count"], data["candidate_class_counts"]["A"], data["candidate_class_counts"]["B"],
             data["candidate_class_counts"]["C"],
             "".join('<option value="%s">%s（%d）</option>' % (esc(key), esc(key), data["taxonomy_snapshot"]["broad_counts"][key]) for key in data["taxonomy_snapshot"]["broad_order"] if data["taxonomy_snapshot"]["broad_counts"][key]),
             "".join('<option value="%s">%s（%d）</option>' % (esc(key), esc(key), value) for key, value in data["taxonomy_snapshot"]["industry_counts"].items()),
             data["candidate_count"], data["candidate_count"], heads, rows))

CSS = """
:root{--paper:#f5f2e9;--panel:#fffdf7;--ink:#202735;--muted:#626b77;--line:#ddd6c7;--navy:#183b5d;--red:#b44732;--gold:#997129;--serif:"Songti SC","STSong","SimSun",serif;--sans:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.5}main{max-width:1480px;margin:auto;padding:24px 18px 48px}
h1{font:700 clamp(29px,4vw,42px)/1.18 var(--serif);margin:7px 0 9px}.kicker{font:700 11px monospace;letter-spacing:.14em;color:var(--gold)}.lede{max-width:920px;color:#505866;margin:0}
.facts{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0}.fact{background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:8px 11px;font-size:12px}.fact strong{font-size:16px;color:var(--navy)}
.boundary{border-left:4px solid var(--red);background:#f8eae5;color:#7d3528;padding:10px 13px;margin:15px 0 20px}
.toolbar{display:flex;flex-wrap:wrap;gap:8px;margin:22px 0 12px}.toolbar input,.toolbar select{border:1px solid var(--line);background:var(--panel);border-radius:8px;min-height:40px;padding:0 11px;font:600 13px var(--sans);color:var(--ink)}.toolbar input{flex:2 1 240px}.toolbar select{flex:1 1 145px}.result{font-size:12px;color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px}.stock{background:var(--panel);border:1px solid var(--line);border-radius:11px;padding:15px;min-width:0}.stock[hidden]{display:none}
.stock-head{display:flex;align-items:flex-start;gap:10px}.rank{background:var(--navy);color:white;border-radius:6px;padding:3px 7px;font:700 13px monospace}h2{font:700 22px/1.2 var(--serif);margin:0}h2 small{font:600 12px monospace;color:var(--muted);white-space:nowrap}.sector{font-size:11px;color:var(--muted);margin:4px 0}.tags{display:flex;gap:4px;margin-left:auto}
.pill{font:700 11px monospace;border-radius:99px;padding:4px 8px;background:#ede8dc;color:var(--navy)}.pill-A{background:#f5e4de;color:#873a30}.pill-B{background:#e5edf3;color:#214e70}.pill-C{background:#e4efe5;color:#275d3d}.shortage-tag{display:inline-block;margin-top:3px;border-radius:99px;padding:3px 7px;background:#f7e6d7;color:#8a3c26;font-size:10px;font-weight:700;text-decoration:none}.shortage-tag:hover{text-decoration:underline}
.stage{font-weight:700;font-size:14px;margin:12px 0 4px}.status{color:var(--muted);font-size:11px;margin:0 0 11px}.points{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}.point{border:1px solid #e7e0d1;background:#faf8f2;border-radius:7px;padding:6px 8px;min-width:0}.point span{display:block;color:var(--muted);font-size:10px}.point strong{font:700 15px monospace;color:var(--navy)}.no-price{grid-column:1/-1;margin:3px 0;color:#8e3928;font-size:11px}
details{margin-top:11px;border-top:1px solid var(--line)}summary{cursor:pointer;padding-top:8px;font-weight:700;color:var(--navy);font-size:12px}details p{font-size:11px;color:#4f5664;margin:8px 0}.method{margin-top:25px;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:15px}.method h2{font-size:21px}.method p{margin:7px 0;font-size:12px}footer{font-size:11px;color:var(--muted);margin-top:16px;overflow-wrap:anywhere}
@media(max-width:760px){main{padding:16px 10px 32px}.grid{grid-template-columns:1fr}.points{grid-template-columns:repeat(2,minmax(0,1fr))}h2{font-size:20px}}
.pool{margin:20px 0 24px}.pool-head{display:flex;align-items:baseline;justify-content:space-between;gap:12px;flex-wrap:wrap}.pool-head h2{font:700 23px var(--serif);margin:0}.pool-head p{font-size:12px;color:var(--muted);margin:0}.pool-toolbar{display:grid;grid-template-columns:minmax(210px,2fr) repeat(7,minmax(118px,1fr)) auto;gap:8px;margin:12px 0 7px}.pool-toolbar input,.pool-toolbar select,.pool-toolbar button{height:38px;border:1px solid var(--line);border-radius:7px;background:var(--panel);color:var(--ink);font:600 12px var(--sans);padding:0 10px}.pool-toolbar button{cursor:pointer;background:#ebe7dc}.table-wrap{border:1px solid var(--line);border-radius:10px;background:var(--panel);max-height:72vh;overflow:auto}#candidateTable{border-collapse:separate;border-spacing:0;width:100%;min-width:1840px;font-size:11px}#candidateTable thead{position:sticky;top:0;z-index:2;background:#e9e4d8}#candidateTable th{padding:0;text-align:left;border-bottom:1px solid #cfc6b5;white-space:nowrap}#candidateTable th button{display:flex;align-items:center;width:100%;padding:9px 8px;border:0;background:transparent;color:var(--ink);font:700 11px var(--sans);cursor:pointer}#candidateTable th button::after{content:"↕";color:#9a927f;margin-left:5px}#candidateTable td{padding:8px;border-bottom:1px solid #ece6da;vertical-align:top}#candidateTable tbody tr:hover{background:#f4f0e6}#candidateTable tbody tr[hidden]{display:none}#candidateTable .priority-row{background:#f3f8ee}#candidateTable .identity{white-space:nowrap;color:var(--navy)}#candidateTable .identity b{font-size:12px}#candidateTable small{display:block;color:var(--muted);font-size:10px}#candidateTable .num{white-space:nowrap;font-variant-numeric:tabular-nums}#candidateTable .stage-cell{min-width:250px;max-width:350px}#candidateTable .futu-cell{min-width:95px;font-weight:700;color:var(--red)}#candidateTable .classify-cell{min-width:145px;font-weight:700;color:var(--navy)}#candidateTable .shortage-cell{min-width:150px;max-width:220px}#candidateTable .note-cell{min-width:280px;max-width:380px;white-space:normal}#candidateTable .focus{color:#246444;white-space:nowrap}.top-panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px}.top-panel>summary{font:700 20px var(--serif);cursor:pointer}.top-panel>p{font-size:12px;color:var(--muted)}.top-panel .grid{margin-top:13px}
@media(max-width:900px){.pool-head{display:block}.pool-toolbar{grid-template-columns:1fr 1fr}.pool-toolbar input{grid-column:1/-1}.pool-toolbar button{grid-column:1/-1}.table-wrap{max-height:none;overflow:visible;border:0;background:transparent}#candidateTable{display:block;min-width:0}#candidateTable thead{display:none}#candidateTable tbody{display:grid;gap:10px}#candidateTable tr{display:grid;grid-template-columns:1fr 1fr;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:9px}#candidateTable td{display:grid;grid-template-columns:102px minmax(0,1fr);gap:8px;padding:6px;border-bottom:1px solid #eee8dc;overflow-wrap:anywhere}#candidateTable td::before{content:attr(data-label);font-weight:700;color:var(--muted)}#candidateTable .identity,#candidateTable .num{white-space:normal}#candidateTable .stage-cell,#candidateTable .futu-cell,#candidateTable .classify-cell,#candidateTable .shortage-cell,#candidateTable .note-cell{min-width:0;max-width:none}#candidateTable td:nth-child(n+3){grid-column:1/-1}#candidateTable td:last-child{border-bottom:0}}
"""

def render(data):
    quota_max = data.get("selection_policy", {}).get("nontechnology_stock_quota_max", 4)
    quota_note = "所有合格候选统一竞争前10，非科技不预留名额、不设专属数量上限" if quota_max is None else "该名单依据当时规则为合格非科技预留最多%d席" % quota_max
    counts = data["class_counts"]
    facts = ('<div class="fact">最新完整收盘 <strong>%s</strong></div><div class="fact">观察交易日 <strong>%s</strong></div>'
             '<div class="fact">完整备选 <strong>%d</strong></div><div class="fact">富途重点 <strong>%d</strong></div><div class="fact">前10命中 A %d · B %d · C %d（重叠计数）</div>'
             '<div class="fact">行情覆盖 %d/%d · C备选 %d</div><div class="fact">已核验非科技 %d只</div>' %
             (esc(data["data_date"]), esc(data["next_session"]), data["candidate_count"], data["selected_count"], counts["A"], counts["B"], counts["C"],
              data["covered_count"], data["source_count"], data["C_pool_count"], data["verified_nontechnology_count"]))
    cards = "\n".join(render_stock(row) for row in data["stocks"])
    content = ('<div class="kicker">A-SHARE · VERIFIED DAILY ABC WATCHLIST</div><h1>A股 A/B/C 候选全表</h1>'
               '<p class="lede">基于已完成日K，独立筛选A类关K回调、B类回落转稳和C类主升延续，合并去重后完整展示。候选按“一级产业 → 二级行业”细分，并把本机资料中的缺货/供给约束线索单独标注；富途A观察重点前10仍按价格阶段与多类共振优选。</p>'
               '<div class="facts">%s</div>' % facts +
               '<p class="boundary">全表为条件技术候选，未进前10不等于模型不合格；A观察重点前10已独立回读。点位只对重点前10生成，取自%s完整日K，盘中触价不等于收盘确认。当前执行就绪：%s。A股新买当日不可卖（T+1）；ETF交易制度逐只核验。</p>' %
               (esc(data["data_date"]), "是" if data["execution_ready"] else "否") +
               render_table(data) +
               '<details class="top-panel"><summary>重点前10与条件点位（展开）</summary><p>本节对应富途A观察页卡。结构点位不是直接买入指令；没有有效最高接受价的股票维持等待。</p>' +
               '<div class="toolbar"><input id="search" type="search" placeholder="搜索股票、代码、行业或阶段" aria-label="搜索股票">'
               '<select id="classFilter" aria-label="按类别筛选"><option value="">全部类别</option><option value="A">A 关K回调</option><option value="B">B 回落转稳</option><option value="C">C 主升延续</option></select>'
               '<select id="categoryFilter" aria-label="按一级产业筛选"><option value="">全部大类</option>%s</select>'
               '<select id="industryFilter" aria-label="按二级行业筛选"><option value="">全部细分行业</option>%s</select></div>'
               '<p class="result" id="resultCount">显示 %d / %d 只</p><section class="grid" id="stockGrid" aria-label="A股观察名单">%s</section>' %
               ("".join('<option value="%s">%s</option>' % (esc(key), esc(key)) for key in data["taxonomy_snapshot"]["broad_order"] if data["taxonomy_snapshot"]["broad_counts"][key]),
                "".join('<option value="%s">%s</option>' % (esc(key), esc(key)) for key in data["taxonomy_snapshot"]["industry_counts"]),
                data["selected_count"], data["selected_count"], cards) + '</details>' +
               '<section class="method"><h2>类别与排序说明</h2>'
               '<p><b>A：</b>A核个股关K后第1—3个完整交易日缩量回调，并且本轮板块复核通过为确认；板块仅满足2/3可列待补条件观察，逐项注明缺口，不算正式准入。</p>'
               '<p><b>B：</b>A核普通股或指定ETF的日线回落结构仍有效；MACD/KDJ从金叉前酝酿、单金叉到双金叉逐步确认。跌破本轮结构底退出该轮。</p>'
               '<p><b>C：</b>独立日线主升延续的趋势回踩或强势平台；纳入当日已验收“三类 A”页卡，板块、公告及下一交易日可交易性仍须复核。</p>'
               '<p><b>富途页卡：</b>半导体、光、PCB三类来自本机Codex历史对话及其已验收页卡回读（截至%s），用于分类筛选，不代表本轮实时OpenD清单。说明列只复用历史对话中明确给过的个股备注；仅有页卡归属证据时会明确标注，不补写成历史备注。</p>' % esc(data["futu_tab_snapshot"]["asof"]) +
               '<p><b>产业分类：</b>一级大类是展示层归组，二级行业保留本轮已核验行业字段，例如“科技 → 半导体”。分类只帮助检索，不改变A/B/C资格、排序或富途前10。</p>'
               '<p><b>缺货/供给线索：</b>当前完整候选命中%d只；独立页完整列出23类、55家公司和逐项原文链接。线索包括供需偏紧、扩展映射、旧资料及可能受损项，不统一解释为利好或公告确认。<a href="../a-share-shortage-watch/">打开缺货名单</a>。</p>' % data["shortage_snapshot"]["matched_candidate_count"] +
               '<p>完整表收录本轮全部独立达标且行业身份已核验的候选，不受A观察前10容量限制。前10先比较价格阶段和A/B/C命中数；同等条件科技优先；%s，同一富途主要行业最多3只。最高接受价缺失时保持等待；非前10仅有技术观察证据，没有逐股交易计划。</p></section>' % esc(quota_note) +
               '<footer>数据日 %s · 生成 %s · 来源覆盖 %.1f%% · A观察独立回读通过 · <a href="data.json">公共数据</a> · 结果证据 SHA-256 %s…</footer>' %
               (esc(data["data_date"]), esc(data["generated_at_bj"]), data["coverage_ratio"] * 100, data["evidence"]["result_sha256"][:16]))
    script = """const cards=[...document.querySelectorAll('.stock')],search=document.getElementById('search'),classFilter=document.getElementById('classFilter'),categoryFilter=document.getElementById('categoryFilter'),industryFilter=document.getElementById('industryFilter'),result=document.getElementById('resultCount');function filter(){const q=search.value.trim().toLowerCase(),c=classFilter.value,g=categoryFilter.value,i=industryFilter.value;let n=0;for(const card of cards){const visible=(!q||card.dataset.search.includes(q))&&(!c||card.dataset.classes.split(' ').includes(c))&&(!g||card.dataset.category===g)&&(!i||card.dataset.industry===i);card.hidden=!visible;if(visible)n++}result.textContent='显示 '+n+' / '+cards.length+' 只'}for(const input of [search,classFilter,categoryFilter,industryFilter])input.addEventListener('input',filter);
const poolRows=[...document.querySelectorAll('#candidateTable tbody tr')],poolSearch=document.querySelector('#poolSearch'),poolClass=document.querySelector('#poolClass'),poolFutuTab=document.querySelector('#poolFutuTab'),poolCategory=document.querySelector('#poolCategory'),poolIndustry=document.querySelector('#poolIndustry'),poolShortage=document.querySelector('#poolShortage'),poolTop=document.querySelector('#poolTop'),poolCount=document.querySelector('#poolCount'),poolBody=document.querySelector('#candidateTable tbody');function filterPool(){const q=poolSearch.value.trim().toLowerCase(),c=poolClass.value,tab=poolFutuTab.value,g=poolCategory.value,i=poolIndustry.value,s=poolShortage.value,top=poolTop.value;let n=0;for(const row of poolRows){const tabs=row.dataset.futuTabs.split(' ').filter(Boolean),tabMatch=!tab||(tab==='none'?tabs.length===0:tabs.includes(tab));const show=(!q||row.dataset.search.includes(q))&&(!c||row.dataset.classes.split(' ').includes(c))&&tabMatch&&(!g||row.dataset.category===g)&&(!i||row.dataset.industry===i)&&(!s||row.dataset.shortage===s)&&(!top||row.dataset.top===top);row.hidden=!show;if(show)n++}poolCount.textContent='显示 '+n+' / '+poolRows.length+' 只 · 点击表头排序'}for(const el of [poolSearch,poolClass,poolFutuTab,poolCategory,poolIndustry,poolShortage,poolTop])el.addEventListener('input',filterPool);document.querySelector('#poolReset').addEventListener('click',()=>{for(const el of [poolSearch,poolClass,poolFutuTab,poolCategory,poolIndustry,poolShortage,poolTop])el.value='';filterPool();sortPool('rank',true)});
let sortKey='rank',sortAscending=true;function sortPool(key,forceAscending=false){sortAscending=forceAscending||key!==sortKey?true:!sortAscending;sortKey=key;const numeric=['rank','close','volume','invalid'].includes(key);poolRows.sort((a,b)=>{const x=a.dataset[key]||'',y=b.dataset[key]||'';const value=numeric?(Number(x)-Number(y)):x.localeCompare(y,'zh-CN');return sortAscending?value:-value});for(const row of poolRows)poolBody.appendChild(row);for(const button of document.querySelectorAll('#candidateTable th button'))button.removeAttribute('data-direction');document.querySelector('#candidateTable th button[data-sort="'+key+'"]').dataset.direction=sortAscending?'asc':'desc'}for(const button of document.querySelectorAll('#candidateTable th button'))button.addEventListener('click',()=>sortPool(button.dataset.sort));"""
    return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="description" content="A股A/B/C日线候选全表：关K回调、日线回落转稳、主升延续；重点前10附条件点位与失效参考。"><meta http-equiv="Cache-Control" content="no-store">'
            '<title>A股 A/B/C 候选全表 · CSN投研</title><link rel="stylesheet" href="../assets/csnpk-nav.css" data-csnpk-nav-style>'
            '<script src="../assets/csnpk-nav.js" defer data-csnpk-nav-script></script><style>%s</style></head><body><main>%s</main><script>%s</script></body></html>' %
            (CSS, content, script))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, help="已验收A观察本轮目录；默认读取latest.json")
    parser.add_argument("--futu-tabs", type=Path, default=DEFAULT_FUTU_TABS, help="本机Codex历史页卡分类与备注")
    parser.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY, help="两级产业分类配置")
    parser.add_argument("--shortage-inventory", type=Path, default=DEFAULT_SHORTAGE, help="23类55家公司缺货/供给线索")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    primary = read(ROOT / "outputs/a_observe_daily/latest.json")
    ab_pointer = ROOT / "outputs/a_observe_daily/latest_ab.json"
    ab = read(ab_pointer) if ab_pointer.exists() else {}
    if not args.run and ab.get("final_readback_ok") and ab.get("asof", "") > primary.get("asof", ""):
        from render_a_observe_ab_page import build
        supplement_file = args.output_dir / "data.json"
        supplement = read(supplement_file).get("research_review") if supplement_file.exists() else None
        build(Path(ab["run"]), args.output_dir)
        if supplement and ab["asof"] <= supplement["market_asof"]:
            generated = read(supplement_file)
            generated["research_review"] = supplement
            supplement_file.write_text(json.dumps(generated, ensure_ascii=False, indent=2) + "\n")
            from a_observe_research_overlay import apply
            apply(args.output_dir)
        print(json.dumps({"data_date": ab["asof"], "scope": ab["scope"], "output_dir": str(args.output_dir)}, ensure_ascii=False))
        return
    run = args.run or Path(primary["run"])
    data = public_data(run, args.futu_tabs, args.taxonomy, args.shortage_inventory)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    old_file = args.output_dir / "data.json"
    if old_file.exists():
        prior = read(old_file).get("research_review")
        if prior and data.get("data_date", "") <= prior["market_asof"]:
            data["research_review"] = prior
    (args.output_dir / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "index.html").write_text(render(data), encoding="utf-8")
    from a_observe_research_overlay import apply
    apply(args.output_dir)
    print(json.dumps({"output_dir": str(args.output_dir), "data_date": data["data_date"], "rows": data["candidate_count"], "focus": data["selected_count"]}, ensure_ascii=False))

if __name__ == "__main__":
    main()
