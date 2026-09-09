#!/usr/bin/env python3
"""Export allowlisted research snapshots only; never scan or mutate accounts."""
import argparse,json
from pathlib import Path
from datetime import datetime,timezone
p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--out',type=Path,default=Path(__file__).resolve().parents[1]/'a-share-workbench/data.json');a=p.parse_args()
review=json.loads((a.workspace/'outputs/a_observe_model_review_20260909/review.json').read_text())
rows=[]
for r in review['rows']:
 k=r.get('key',{});post=k.get('post_key_k_pullback') or {}
 rows.append(dict(code=r['code'],name=r['name'],decision=r['decision'],reason=r['reason'],priority=r.get('P','—'),key_date=k.get('key_k_date'),days=post.get('day_number'),date=r.get('date','')[:10]))
run=json.loads((a.workspace/'outputs/a30_key_nodes/latest_run.json').read_text())
# Status fields only: no account IDs, raw holdings, cookies, receipts or credentials.
monitor={k:run.get(k) for k in ['status','bar','scope','verified_total','universe','fresh_coverage','active_count','event_count','table']}
scan=json.loads((a.workspace/'outputs/a30_key_nodes/scan.json').read_text())
state=json.loads((a.workspace/'outputs/a30_key_nodes/state.json').read_text())
monitor['rows']=[]
if scan.get('opend_status')=='OpenD已连接' and state.get('last_bar')==run.get('bar'):
 for r in scan.get('chanlun_push_candidates',[]):
  if r.get('code') not in state.get('active',{}) or r.get('thirty_bar_close')!=run.get('bar'): continue
  k=r.get('chanlun_rebound',{})
  monitor['rows'].append({key:r.get(key) for key in ['code','name','current_state']}|{key:k.get(key) for key in ['phase','priority','bottom_time']}|{'macd':k.get('macd',{}).get('label'),'kdj':k.get('kdj',{}).get('label')})
monitor['scope_label']='仅个股信号'
monitor['source']='outputs/a30_key_nodes/scan.json'
data=dict(schema_version=1,published_snapshot_at=datetime.now(timezone.utc).isoformat(),content_date='2026-09-09',mode='published_snapshot',observe=dict(model=review['model'],captured_at=review.get('validated_at',review.get('finished')),data_date=rows[0]['date'],scope='该次复核的A观察成员；不是全A扫描或当前账户回读',rows=rows),monitor=monitor)
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print('Exported allowlisted snapshot:',len(rows),'rows')
