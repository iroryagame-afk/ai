"""Count completed daily bars after current effective B pivot, pivot bar = 0."""
import json
from pathlib import Path

def b_age(row,run,asof):
 b=row.get('B',{})
 if not (row.get('B_pass') or b.get('eligible')):return ''
 labels=[x for x in b.get('active_round_labels',[]) if 'B' in x.get('label','') and x.get('pivot_date') and x.get('first_known') and x['first_known']<=asof]
 if not labels:return '本轮无有效B标记（不以底分型代替）'
 p=Path(run)/(row['code']+'.json')
 if not p.exists():return '距B点日K根数未核验'
 data=json.loads(p.read_text())
 if not isinstance(data,list):return '距B点日K根数未核验'
 dates=sorted({x['time_key'][:10] for x in data if x.get('time_key') and x['time_key'][:10]<=asof})
 x=max(labels,key=lambda x:(x['pivot_date'],x['first_known']))
 if asof not in dates or x['pivot_date'] not in dates or x['first_known'] not in dates:return '距B点日K根数未核验'
 n=sum(x['pivot_date']<d<=asof for d in dates);k=sum(x['first_known']<d<=asof for d in dates)
 return f"距{x['label']}点{n}根日K（底日{x['pivot_date'][5:]}；首次可知{x['first_known'][5:]}后{k}根）"
