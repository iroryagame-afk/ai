"""Publish verified AB delivery without relabelling it as a complete ABC run."""
import json,html,hashlib,argparse
from a_observe_daily.group_notes import load_notes
from a_observe_daily.b_age import b_age
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def esc(v):return html.escape(str(v),quote=True)
def compact(x):
 a=x['A_pass']
 return {'code':x['code'],'name':x['name'],'classes':x['source'],'industry':x['industry'],'stage':x['stage'],'change_pct':x['change_pct'],'volume_ratio':x['A']['current_ratio'] if a else x['volume_previous'],'volume_basis':'关K日' if a else '前一交易日','structure_date':x['A']['key_date'] if a else x['B']['fractal_date'],'pullback_days':[{'date':v['date'],'change_pct':v['change_pct'],'volume_vs_key':v['volume_vs_key']} for v in x.get('pullback_rows',[])],'m30_status':x['m30']['status'],'b_age_note':x.get('b_age_note',''),'theme_groups':x.get('other_groups',[])}
def build(run,out):
 r=json.loads((run/'result.json').read_text());s=json.loads((run/'sync.json').read_text())
 assert s['final_readback_ok'] and r['coverage']>=.9
 target={x['code']:x['name'] for x in r['top']};assert target==s['target']=={x['code']:x['name'] for x in s['independent_after']}
 notes,notes_at=load_notes(run)
 for x in r['rows']+r['top']:
  x['other_groups']=notes.get(x['code'],[])
  x['b_age_note']=b_age(x,run,r['asof'])
 top={x['code']:i+1 for i,x in enumerate(r['top'])};rows=sorted(r['rows'],key=lambda x:(0,top[x['code']]) if x['code'] in top else (1,x['ranking']))
 def tr(x,i):
  a=x['A_pass'];node=('关K '+x['A']['key_date']) if a else ('底分型 '+x['B']['fractal_date'])
  volume=f"关K量的{x['A']['current_ratio']:.0%}" if a else f"前日量的{x['volume_previous']:.0%}"
  daily='；'.join(f"第{j}日 {v['date']}：{v['change_pct']:+.2f}%／关K量{v['volume_vs_key']:.0%}" for j,v in enumerate(x['pullback_rows'],1)) if a else ''
  vals=[str(i),x['name']+' '+x['code'],x['source']+' · '+x['industry'],node,'截至'+r['asof']+'收盘：'+x['stage']+('；'+x['b_age_note'] if x.get('b_age_note') else ''),f"{x['change_pct']:+.2f}%",volume,x['m30']['status'],daily or '暂无已发生回调记录' if a else x['B'].get('macd_status',''), '重点'+str(top[x['code']]) if x['code'] in top else '备选']
  heads=['排序','股票','类别／方向','结构节点','当前阶段','当日涨跌','量能比较','30分钟辅助','逐日量价／动能','跟踪']
  cells=[]
  for h,v in zip(heads,vals):
   value=esc(v)
   if h=='股票':
    value='<div class="stock-name">'+esc(x['name'])+'</div><small class="stock-code">'+esc(x['code'])+'</small>'
    if x.get('other_groups'):value+='<small class="group-note">主题：'+esc('、'.join(x['other_groups']))+'</small>'
   elif h=='结构节点':value=esc(node.replace(r['asof'][:4]+'-',''))
   elif h=='当前阶段':
    value='<span class="stage-main">'+esc(x['stage'])+'</span>'
    age=x.get('b_age_note','')
    if '（' in age:
     short,detail=age.split('（',1)
     value+='<details class="b-detail"><summary>'+esc(short)+'</summary><span>'+esc(detail.rstrip('）'))+'</span></details>'
    elif age:value+='<small class="asof">'+esc(age)+'</small>'
   elif h=='逐日量价／动能':
    value='<br>'.join(esc(v.replace(r['asof'][:4]+'-','')) for v in v.split('；'))
   cells.append('<td data-label="'+esc(h)+'"><div class="cell-content">'+value+'</div></td>')
  return '<tr data-top="'+str(x['code'] in top).lower()+'" data-search="'+esc(' '.join(vals)+' '+' '.join(x.get('other_groups',[])))+'">'+''.join(cells)+'</tr>' 
 heads=['排序','股票','类别／方向','结构节点','当前阶段','当日涨跌','量能比较','30分钟辅助','逐日量价／动能','跟踪']
 body=''.join(tr(x,i) for i,x in enumerate(rows,1))
 css='''.group-note{display:block;grid-column:2;color:#a24923;font-size:12px;font-weight:600;margin-top:5px}*{box-sizing:border-box}body{margin:0;background:#f5f2e9;color:#202735;font:14px/1.6 system-ui}main{max-width:1500px;margin:auto;padding:28px 20px}h1{font-size:30px}p{color:#626b77}.notice{padding:14px;background:#f9e8dd;border-left:4px solid #b44732}.controls{display:flex;gap:12px;margin:18px 0}input,select{padding:10px;border:1px solid #ddd6c7;border-radius:6px;max-width:100%}.wrap{overflow:auto}table{width:100%;border-collapse:collapse;background:#fffdf7;font-size:13px}th,td{text-align:left;padding:12px 9px;border-bottom:1px solid #e5dfd2;vertical-align:top}th{background:#e9e4d8;cursor:pointer}tr[data-top=true]{background:#f0f6eb}td:nth-child(2){font-weight:700;color:#183b5d}tr[hidden]{display:none}details{margin:24px 0}a{color:#183b5d}@media(max-width:650px){main{padding:16px 12px}.controls{flex-wrap:wrap}table,tbody{display:block}thead{display:none}tr{display:block;border:1px solid #ddd6c7;border-radius:10px;margin:12px 0;padding:8px}td{display:grid;grid-template-columns:95px 1fr;overflow-wrap:anywhere;padding:7px;font-size:13px}td:before{content:attr(data-label);color:#626b77;font-weight:500}.wrap{overflow:visible}h1{font-size:25px}}'''
 css += """
main{max-width:1640px;padding:24px 16px}table{table-layout:fixed;font-size:12px;line-height:1.5}th,td{padding:9px 8px}th{white-space:nowrap;font-size:12px}th:nth-child(1){width:4%}th:nth-child(2){width:12%}th:nth-child(3){width:10%}th:nth-child(4){width:10%}th:nth-child(5){width:22%}th:nth-child(6){width:7%}th:nth-child(7){width:8%}th:nth-child(8){width:7%}th:nth-child(9){width:15%}th:nth-child(10){width:5%}.cell-content{min-width:0;overflow-wrap:anywhere}.stock-name{font-size:13px;font-weight:700}.stock-code,.asof{display:block;font-size:11px;color:#626b77;font-weight:400}.stage-main{font-weight:600}.group-note{font-size:11px;margin-top:4px;color:#8b421e}.b-detail{margin:4px 0 0;font-size:11px}.b-detail summary{cursor:pointer;color:#183b5d;font-weight:600}.b-detail span{display:block;margin-top:4px;color:#626b77}td:nth-child(1),td:nth-child(6),td:nth-child(7),td:nth-child(10){font-variant-numeric:tabular-nums}td:nth-child(6){white-space:nowrap}td:nth-child(10){white-space:nowrap}summary:focus-visible,input:focus-visible,select:focus-visible,th:focus-visible{outline:2px solid #183b5d;outline-offset:3px}::selection{background:#e0d5b8;color:#202735}table th{vertical-align:middle}.controls input{flex:0 1 300px}details summary{min-height:24px}
@media(min-width:901px){.wrap{overflow:visible}}
@media(max-width:900px){table,tbody{display:block}thead{display:none}.wrap{overflow:visible}tr{display:block;border:1px solid #ddd6c7;border-radius:10px;margin:12px 0;padding:8px}td{display:grid;grid-template-columns:100px minmax(0,1fr);gap:8px;padding:7px;font-size:13px;white-space:normal!important}td:before{content:attr(data-label);color:#626b77;font-weight:500}.stock-name{font-size:14px}.stock-code,.asof,.group-note,.b-detail{font-size:12px}.b-detail summary{min-height:30px}main{padding:16px 12px}.controls{flex-wrap:wrap}.controls input{flex:1 1 200px}}
"""
 css += """
main{max-width:1460px}.wrap{max-width:1428px}th,td{padding:8px 7px}th:nth-child(1){width:4%}th:nth-child(2){width:12%}th:nth-child(3){width:10%}th:nth-child(4){width:9%}th:nth-child(5){width:18%}th:nth-child(6){width:7%}th:nth-child(7){width:9%}th:nth-child(8){width:8%}th:nth-child(9){width:18%}th:nth-child(10){width:5%}.stage-main{display:inline}.header-date{font-size:10px;font-weight:400;color:#626b77;margin-left:6px}.b-detail{display:inline-block;margin:0 0 0 8px;vertical-align:top}.b-detail summary{min-height:0;line-height:1.5}.b-detail[open]{display:block;margin:4px 0 0}.b-detail span{max-width:240px}.stock-code{line-height:1.35}.group-note{margin-top:2px}.asof{margin-top:2px}td{vertical-align:middle}
@media(max-width:900px){.b-detail{margin-left:6px}.b-detail summary{min-height:28px}.cell-content{align-self:center}td{padding:6px}.header-date{display:none}}
"""
 js='''const rows=[...document.querySelectorAll('tbody tr')],q=document.querySelector('#q'),mode=document.querySelector('#mode');function filter(){let n=0;for(const r of rows){r.hidden=!(r.dataset.search.toLowerCase().includes(q.value.toLowerCase())&&(mode.value==='all'||r.dataset.top==='true'));if(!r.hidden)n++}document.querySelector('#count').textContent='显示 '+n+' / '+rows.length+' 只'}q.oninput=mode.onchange=filter;filter();document.querySelectorAll('th').forEach((th,i)=>{let asc=true;th.onclick=()=>{rows.sort((a,b)=>a.cells[i].textContent.localeCompare(b.cells[i].textContent,'zh-CN',{numeric:true})*(asc?1:-1));asc=!asc;rows.forEach(r=>document.querySelector('tbody').appendChild(r));}});'''
 text=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>A观察 · CSN投研</title><link rel="stylesheet" href="../assets/csnpk-nav.css" data-csnpk-nav-style><script src="../assets/csnpk-nav.js" defer data-csnpk-nav-script></script><style>{css}</style></head><body><main><h1>A观察 · {esc(r['next_session'])}</h1><p>依据 {esc(r['asof'])} 完整收盘数据 · 重点10只 · 本轮完整A/B备选{len(rows)}只</p><div class="notice">本页同步本任务已给出的观察名单，A观察页卡已独立回读。C类本轮未重评；买卖点位与公告风险尚未完整核验，当前仅作条件观察。A核已在名单生成后调整为90只，本名单尚未按新核心池重排。未重新发送微信或App。</div><div class="controls"><input id="q" placeholder="搜索股票、行业或阶段" aria-label="搜索"><select id="mode" aria-label="名单范围"><option value="top">重点观察10只</option><option value="all">全部本轮备选</option></select></div><p id="count"></p><div class="wrap"><table><thead><tr>{''.join('<th>'+esc(x)+('<small class="header-date">'+esc(r['asof'][5:])+' 收盘</small>' if x=='当前阶段' else '')+'</th>' for x in heads)}</tr></thead><tbody>{body}</tbody></table></div><details><summary>筛选与使用说明</summary><p>A：板块与个股关K共振，标注回调第几日及逐日涨跌、占关K量。B：先按自选行业ETF的CL20位置，再核验对应指数成分与个股结构、MACD及KDJ；30分钟仅辅助。</p><p>{esc(r['ranking'])}</p><p>价格变化相对前一交易日收盘；A量能以关K日为基准，B以此前一日为基准。未发生的第2日不补造。第2日10%建仓是有条件计划，非无条件买入；A股新买当日不可卖。</p></details><p><a href="data.json">完整结构数据</a> · <a href="report.md">本轮报告</a></p></main><script>{js}</script></body></html>'''
 data={'schema_version':'a_observe_ab_delivery_v1','data_date':r['asof'],'next_session':r['next_session'],'scope':r['scope'],'candidate_count':len(rows),'selected_count':len(top),'stocks':[compact(x) for x in r['top']],'candidates':[compact(x) for x in rows],'group_notes_verified_at':notes_at,'watchlist_readback_ok':True,'C_source_verified':False,'price_plan_complete':False,'execution_ready':False,'evidence':{'result_sha256':hashlib.sha256((run/'result.json').read_bytes()).hexdigest()}}
 out.mkdir(parents=True,exist_ok=True);(out/'index.html').write_text(text);(out/'data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2));(out/'report.md').write_text((run/'report.md').read_text())
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();build(a.run,a.output_dir)
