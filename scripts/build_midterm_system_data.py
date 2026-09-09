#!/usr/bin/env python3
"""Export only the stock-list sections explicitly delivered by the source task."""
import argparse, hashlib, json, re
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--source',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
raw=a.source.read_bytes(); report=raw.decode()
def section(title):
    parts=report.split('**'+title+'**',1)
    if len(parts)!=2: raise SystemExit('Missing list section: '+title)
    return parts[1].split('\n**',1)[0]
def rows(title):
    result=[]
    for line in section(title).splitlines():
        if line.startswith('|') and not re.fullmatch(r'[| :\-]+',line):
            result.append([v.strip() for v in line.strip('|').split('|')])
    if len(result)<2: raise SystemExit('Empty stock table: '+title)
    return result
names=rows('先定名单'); actions=rows('最新价格与下一步')
if any(len(r)!=5 for r in names) or any(len(r)!=4 for r in actions):raise SystemExit('Review changed table schema')
identities=[re.search(r'([^ ]+)\s+(\d{6})',r[1]) for r in names[1:]]
if not all(identities):raise SystemExit('Stock identity missing')
if [m[1] for m in identities]!=[r[0] for r in actions[1:]]:raise SystemExit('List/action identity mismatch')
date=re.search(r'截至(\d{4}-\d{2}-\d{2}) 15:00完整收盘',report)
if not date:raise SystemExit('Source date missing')
body='## 核心与事件候选\n角色|股票|产业环节|合格建仓后复核\n'
body+='\n'.join('|'.join(r[i] for i in [0,1,2,4]) for r in names[1:])
body+='\n## 当前状态与下一步\n'+'\n'.join('|'.join(r) for r in actions)
body+='\n## 替补名单\n'
# Preserve source wording only for explicitly named backup entries.
backups=[line[2:] for line in section('备选与暂不优先').splitlines() if line.startswith('- ') and re.search(r'\d{6}',line)]
if not backups:raise SystemExit('Backup source missing')
body+='\n'.join(backups)
if a.source.read_bytes()!=raw:raise SystemExit('Source changed while reading')
d={'schema_version':1,'source_title':'中线交易系统规划','as_of':date[1]+'T15:00:00+08:00','status':'源报告收盘 · 候选名单','source_digest':hashlib.sha256(raw).hexdigest(),'source_file':a.source.name,'body':body}
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
print('Exported',len(identities),'candidates and',len(backups),'backups; source',date[1])
