"""Read-only custom-watchlist membership notes; never affects eligibility/rank."""
import json,time
from pathlib import Path
from datetime import datetime

THEME_GROUPS = ('缺货','X','高弹','PCB','光','元器件','材料','半导体','国算','金融','PFTE')

def load_notes(run):
 p=Path(run)/'group_notes.json'
 if not p.exists():return {},None
 d=json.loads(p.read_text())
 if not d.get('complete'):return {},None
 r=json.loads((Path(run)/'result.json').read_text())
 if d.get('asof')!=r.get('asof'):return {},None
 return {c:[g for g in THEME_GROUPS if g in groups] for c,groups in d['notes'].items() if any(g in THEME_GROUPS for g in groups)},d['verified_at']

def collect(run):
 from futu import OpenQuoteContext,RET_OK
 run=Path(run);r=json.loads((run/'result.json').read_text());wanted={x['code'] for x in r['rows']};notes={};audit={'complete':False,'notes':notes}
 q=OpenQuoteContext(host='127.0.0.1',port=11111)
 try:
  rc,groups=q.get_user_security_group();assert rc==RET_OK,groups
  time.sleep(30)  # Leave the preceding watchlist-sync rate-limit window.
  names=[x['group_name'] for x in groups.to_dict('records') if x['group_type']=='CUSTOM' and x['group_name'].strip() in THEME_GROUPS]
  audit['groups']=names
  for name in names:
   time.sleep(4)
   rc,d=q.get_user_security(name);assert rc==RET_OK,d
   for c in set(d.code)&wanted:notes.setdefault(c,[]).append(name.strip())
   print(name,len(set(d.code)&wanted),flush=True)
  audit.update(complete=True,verified_at=datetime.now().isoformat(),asof=r['asof'])
 finally:
  q.close();(run/'group_notes.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
if __name__=='__main__':
 import sys
 collect(sys.argv[1])
