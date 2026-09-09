#!/usr/bin/env python3
"""Render the evidence-labelled macro overlay without advancing close-model dates.

Run after page generators and before publication. The radar JSON is the sole
source; static HTML deliberately remains readable when JavaScript is unavailable.
"""
import html
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ('macro-event-radar/index.html', 'macro-fiscal-risk/index.html',
           'weekly-event-transmission-2026w37/us/index.html')
START = '<!-- NEAR-TERM-MACRO:START -->'
END = '<!-- NEAR-TERM-MACRO:END -->'


def esc(value):
    return html.escape(str(value), quote=True)


def render_block(data):
    cards = []
    for event in data['events']:
        result = event['result']
        links = ' · '.join(f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">来源 {i+1}</a>'
                           for i, url in enumerate(event['sources']))
        actual = '未回填' if result['actual'] is None else json.dumps(result['actual'], ensure_ascii=False)
        consensus = '未核验' if result['consensus'] is None else json.dumps(result['consensus'], ensure_ascii=False)
        reaction = '未核验' if result['market_reaction'] is None else json.dumps(result['market_reaction'], ensure_ascii=False)
        result_link = (f'<a href="{esc(result["source"])}" target="_blank" rel="noopener noreferrer">结果原件</a>'
                       if result['source'] else '结果原件：未回填')
        cards.append(f'''<article class="nt-card"><small>{esc(event['status'])}</small>
<h3>{esc(event['title'])}</h3><p><b>{esc(event['time'])}</b></p><p>{esc(event['check'])}</p>
<details><summary>结果验收 · {esc(result['status'])}</summary><p>{esc(event['acceptance'])}</p>
<p>实际：{esc(actual)}；事前共识：{esc(consensus)}；市场反应：{esc(reaction)}</p>
<p>结果核验时间：{esc(result['verified_at'] or '未回填')} · {result_link}</p></details><p>{links or '准确议程来源待取得'}</p></article>''')
    oil = data['brent']
    return f'''{START}
<style>.nt-macro{{margin:24px 0;padding:20px;border:1px solid #b8c9d4;border-radius:14px;background:#f3f7fa;color:#18202b;overflow-wrap:anywhere}}.nt-macro h2{{margin:0 0 8px;font-size:25px}}.nt-macro p{{font-size:13px;line-height:1.7}}.nt-macro a{{color:#174c78}}.nt-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}.nt-card{{min-width:0;padding:16px;border:1px solid #d8dfe4;border-radius:10px;background:#fff}}.nt-card h3{{margin:8px 0;font-size:18px}}.nt-card small{{color:#7b4d13}}.nt-card details{{font-size:13px}}.nt-card summary{{cursor:pointer}}@media(max-width:700px){{.nt-grid{{grid-template-columns:1fr}}.nt-macro{{padding:14px}}}}</style>
<section class="nt-macro" id="near-term-macro" aria-labelledby="nt-title">
<h2 id="nt-title">近两日宏观日历与本周通胀验收</h2>
<p>补充核验：{esc(data['as_of'])} · 以下均为北京时间。{esc(data['scope'])}</p>
<p><b>Brent 100美元已盘中触及。</b>{esc(oil['observed_at'])}：${esc(oil['value'])}/桶。{esc(oil['note'])} <a href="{esc(oil['source'])}" target="_blank" rel="noopener noreferrer">Reuters报道</a></p>
<p><b>口径优先级：</b>盘中油价以本栏带时间戳报道为准；下方原有财政风险数值、阈值状态及图表仍是各自日期的历史快照，并非当前实时判断。财报部分保留原核验日期。</p>
<div class="nt-grid">{''.join(cards)}</div>
<p>验收流程：公告/数据原件 → 同口径实际与事前共识 → 市场反应 → 下一检查点。这里只建立回填栏位，不代表已完成结果跟踪，也未启动额外通知或定时任务。</p>
</section>
{END}'''


def main():
    radar = json.loads((ROOT/'macro-event-radar/data.json').read_text())
    block = render_block(radar['near_term'])
    for target in TARGETS:
        path = ROOT/target
        page = path.read_text()
        page = re.sub(re.escape(START)+'.*?'+re.escape(END)+r'\n?', '', page, flags=re.S)
        main_pos = page.index('<main')
        if target.startswith('macro-fiscal-risk'):
            insert_pos = page.index('</p>', page.index('<p class="lede"', main_pos)) + 4
        else:
            insert_pos = page.index('</header>', main_pos) + len('</header>')
        local_block = block
        if target.startswith('macro-fiscal-risk'):
            local_block = re.sub(r'<div class="nt-grid">.*?</div>',
                '<p><a href="../macro-event-radar/#near-term-macro">查看回购、拍卖、讲话线索、PPI、初请与CPI完整日历和结果验收栏位 →</a></p>',
                block, flags=re.S)
        page = page[:insert_pos]+'\n'+local_block+page[insert_pos:]
        if target.startswith('macro-event-radar'):
            page = re.sub(r'(?:真实|核心)事件快照 · \d{4}-\d{2}-\d{2}[^<]*',
                          '核心事件快照 · '+radar['generated_at'][:10]+'；宏观补充见专栏', page)
            # Do not put a false error message in unexecuted HTML/search extracts.
            page = page.replace('数据加载失败。页面不会用空值冒充已经完成的信息核验。', '')
            page = page.replace("document.getElementById('error').classList.add('show');",
                                "document.getElementById('error').textContent='核心事件加载失败；上方宏观静态快照仍可读取。';document.getElementById('error').classList.add('show');") if "上方宏观静态快照仍可读取。" not in page else page
            payload = json.dumps(radar, ensure_ascii=False, indent=2).replace('</','<\\/')
            page = re.sub(r'(<script id="macro-event-radar-data" type="application/json">).*?(</script>)',
                          lambda m: m[1]+'\n'+payload+'\n  '+m[2], page, flags=re.S)
        if target.startswith('weekly-event'):
            page = page.replace('下周美股财报事件传导', '本周美股宏观与财报事件传导')
        path.write_text(page)
    print('Rendered macro overlay into three scoped pages; close-model dates unchanged.')


if __name__ == '__main__':
    main()
