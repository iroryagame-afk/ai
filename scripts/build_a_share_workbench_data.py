#!/usr/bin/env python3
"""Export source-verified observation lists; never scan or write accounts."""
import argparse,json
from pathlib import Path
from datetime import datetime,timezone
p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--observe',default='outputs/a_observe_ab_20260910');p.add_argument('--monitor',default='outputs/a30_key_nodes/corrected_20260910_1430.json');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
root=a.workspace/a.observe
scan=json.loads((root/'scan.json').read_text());board=json.loads((root/'board_review/result.json').read_text());audit=json.loads((root/'board_review/write_audit.json').read_text())
if not audit['final_readback_ok'] or {r['code'] for r in audit['independent_after']}!=set(board['target']):raise SystemExit('Observation readback mismatch')
bycode={r['code']:r for r in scan['rows']};ar={r['code']:r for r in board['A_results']};rows=[]
for code,name in board['target'].items():
 r=bycode.get(code,{});k=r.get('A',{});b=r.get('B',{});pending=code in board['pending_retained'];reason=('未核验暂留' if pending else 'B·'+b.get('state','未核验'))
 if code in ar:reason+='；A板块'+ar[code]['A_board_status']
 rows.append(dict(code=code,name=name,decision='KEEP_UNVERIFIED' if pending else 'KEEP_B',reason=reason,priority=b.get('state','—'),key_date=k.get('key_date'),days=k.get('day'),date=scan['asof']))
raw=json.loads((a.workspace/a.monitor).read_text());mr=[]
if raw['opend_status']!='OpenD已连接':raise SystemExit('Monitor source not verified')
for r in raw['chanlun_push_candidates']:
 k=r['chanlun_rebound'];mr.append(dict(code=r['code'],name=r['name'],current_state=r['current_state'],priority=k.get('priority','P1' if k.get('confirmation_status')=='confirmed_pullback' else 'P2'),phase='第'+str(k['pullback_pen_number'])+'笔 · '+k['phase'],bottom_time=k['bottom_time'],macd=k.get('macd',{}).get('label','—'),kdj=k.get('kdj',{}).get('label','—')))
bars={r['thirty_bar_close'] for r in raw['chanlun_push_candidates']}
if len(bars)!=1:raise SystemExit('Monitor dates differ')
d=dict(schema_version=1,published_snapshot_at=datetime.now(timezone.utc).isoformat(),content_date=scan['asof'],mode='published_snapshot',observe=dict(model=board['model'],captured_at=audit['time'],data_date=scan['asof'],scope='源任务已核验A观察名单',rows=rows),monitor=dict(bar=bars.pop(),rows=mr,scope_label='更正名单 · 仅个股信号',source=a.monitor,verified_total=raw['verified_total'],universe=raw['watchlist_stock_total'],event_count=0,status='CORRECTED_SOURCE_NOT_SENT'))
a.out.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');print('Observe',len(rows),'monitor',len(mr))
