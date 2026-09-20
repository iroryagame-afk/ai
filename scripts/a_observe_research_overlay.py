"""Public research supplement; never alters accepted watchlist snapshot."""
import html,json,re
from pathlib import Path

def apply(directory):
 directory=Path(directory);data=json.loads((directory/'data.json').read_text());r=data.get('research_review')
 if not r or data.get('data_date','')>r['market_asof']:return
 p=directory/'index.html';doc=p.read_text()
 doc=re.sub(r'<!-- research:start -->.*?<!-- research:end -->','',doc,flags=re.S)
 def fmt(s):return re.sub(r'\*\*(.*?)\*\*',r'<strong>\1</strong>',html.escape(s))
 headers=['股票','类别','当前阶段','量比','周一观察重点','JEV复核结论']
 rows=''.join('<tr>'+''.join('<td data-label="'+h+'">'+fmt(c)+'</td>' for h,c in zip(headers,row))+'</tr>' for row in r['rows'])
 style='''#research-review{margin:0 0 30px}#research-review h2{font-size:23px}#research-review p{max-width:100%;font-size:13px}#research-review table{table-layout:fixed;width:100%;font-size:13px;line-height:1.65}#research-review th,#research-review td{padding:12px 10px;white-space:normal;overflow-wrap:anywhere}#research-review th{position:sticky;top:0;z-index:2;cursor:default}#research-review th:nth-child(1){width:17%}#research-review th:nth-child(2){width:5%}#research-review th:nth-child(3){width:21%}#research-review th:nth-child(4){width:7%}#research-review th:nth-child(5){width:26%}#research-review th:nth-child(6){width:24%}#research-review td:nth-child(2){font-weight:400;color:inherit}.wrap{overflow:visible} @media(max-width:900px){#research-review table{display:block}#research-review td{grid-template-columns:85px minmax(0,1fr);font-size:13px}#research-review td:nth-child(1){font-size:15px;font-weight:700}#research-review th{width:auto}#research-review tr{margin:10px 0}#research-review td{padding:6px}}'''
 block='<!-- research:start --><section id="research-review"><style>'+style+'</style><h2>周一候选 · 2026-09-21</h2><p>技术数据：2026-09-18完整收盘 · 研究核验：2026-09-20 · 量比＝9月18日/9月17日成交量。当前可执行买入0只。</p><table><thead><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+rows+'</tbody></table><p>JEV：jev-1.13.0，10只、53个命题有实际回执；结论为JEV命题响应结合原文复核后的研究判断，非模型直接买卖评级。〔深入〕为另完成深入研究；ETF仅代表成分抽核。原技术排序保留。</p><p>A：关K及板块资格。B：日线回落转稳、MACD/KDJ及30分钟配合。C：独立主升延续/平台。'+('富途A观察已同步10只，独立回读通过；未发送通知。' if r.get('watchlist_synced') else '新研究未写入富途页卡，未发送通知。')+'</p><details><summary>公开复核来源</summary><ul>'+''.join('<li><a href="'+html.escape(u,quote=True)+'" target="_blank" rel="noopener noreferrer">'+html.escape(n)+'</a></li>' for n,u in r['sources'])+'</ul></details></section><!-- research:end -->'
 doc=doc.replace('<main>','<main>'+block,1)
 doc=doc.replace('A观察 · 2026-09-18</h1>','原已验收候选池 · 数据截至2026-09-17</h1>')
 # Legacy controls operate only on original table, not the independent research supplement.
 doc=doc.replace("document.querySelectorAll('th')","document.querySelectorAll('.wrap th')").replace("document.querySelector('tbody').appendChild(r)","document.querySelector('.wrap tbody').appendChild(r)")
 doc=doc.replace("document.querySelectorAll('tbody tr')", "document.querySelectorAll('.wrap tbody tr')")
 p.write_text(doc)

if __name__=='__main__':
 import sys;apply(sys.argv[1])
