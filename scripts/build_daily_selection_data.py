#!/usr/bin/env python3
"""Publish only the delivered daily trend candidate list, without account data."""
import argparse,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
raw=a.source.read_bytes();x=json.loads(raw)
if x['version']!='1.0.0' or x['watchlist_changed_during_scan'] or x['snapshot_errors']:raise SystemExit('Source validation failed')
rows=x['candidates']
if len({r['code'] for r in rows})!=len(rows):raise SystemExit('Duplicate candidates')
if any(r['as_of']!=x['as_of'] or not r['snapshot_verified'] for r in rows):raise SystemExit('Candidate date/snapshot mismatch')
body=''
for title,subset in [('观察名单',[r for r in rows if '位置偏远' not in r['stage']]),('位置偏远 · 暂不追',[r for r in rows if '位置偏远' in r['stage']])]:
 body+='## '+title+' · '+str(len(subset))+'只\n股票|形态|动能|收盘|状态\n'
 body+='\n'.join('|'.join([r['name']+' '+r['code'],' / '.join(r['setups']),r['momentum']['stage'],f"{r['close']:.2f}",r['stage']]) for r in subset)+'\n'
body+='## 核验范围\n自选'+str(x['universe_count'])+'只 · 有效'+str(len(x['rows']))+'只 · 未核验'+str(len(x['failures']))+'项\n仅日线主升延续；板块、公告未核验。\n'
d={'schema_version':1,'source_title':'整合逻辑推送每日A股选股','as_of':x['as_of']+'T15:00:00+08:00','status':'日线主升延续 · 观察名单','body':body,'source_digest':hashlib.sha256(raw).hexdigest()}
if a.source.read_bytes()!=raw:raise SystemExit('Source changed')
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');print('Exported',len(rows),'candidates')
