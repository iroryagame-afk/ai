#!/usr/bin/env python3
"""Export public research fields only. Never trigger scans or broker writes."""
import argparse, json, pathlib, hashlib

def read(p): return json.loads(p.read_text())
def build(root, runtime):
    pointer=read(root/'outputs/a_observe_daily/latest.json')
    run=pathlib.Path(pointer['run']); a=read(run/'result.json'); sync=read(run/'sync.json')
    assert pointer['final_readback_ok'] and sync['final_readback_ok'], 'A readback failed'
    assert {r['code'] for r in a['top']}==set(sync['target']), 'A target mismatch'
    assert {r['code'] for r in sync['independent_after']}==set(sync['target']), 'A independent mismatch'
    assert len(a['top'])<=10
    ar=[]
    for r in a['ranked']:
        key=r.get('A',{}); confirmed=r.get('A_confirmed',False)
        ar.append(dict(in_futu=r['code'] in sync['target'],code=r['code'],name=r['name'],category='A' if confirmed else 'B',key_date=key.get('key_date') if confirmed else None,volume_ratio=key.get('key_ratio') if confirmed else None,current_ratio=key.get('current_ratio') if confirmed else None,stage=r.get('B',{}).get('state','') if not confirmed else '关K回调',shape=r.get('shape','')))
    m=read(root/'outputs/us_daily_abc/latest.json')
    assert m['final_readback_ok'] and m['opend_connected'] and m['session']=='RTH', 'M readback failed'
    assert len(m['selected'])<=10
    mr=[]
    ordered=list(m['selected'])+[c for c in m['candidates'] if c not in m['selected']]
    for code in ordered:
        r=m['candidates'][code]
        if r.get('unknown') or not r.get('identity_verified'): continue
        if r['sources']==['C'] and '位置偏远' in r.get('lanes',{}).get('C',{}).get('stage',''): continue
        lanes=r.get('lanes',{}); sources=r['sources']; k=lanes.get('A',{})
        stages=[lanes[x].get('status',lanes[x].get('stage','')) for x in sources if x in lanes]
        mr.append(dict(in_futu=code in m['selected'],code=code,name=r['name'],category=' / '.join(sources),key_date=k.get('key_date') if 'A' in sources else None,volume_ratio=k.get('volume_ratio_raw') if 'A' in sources else None,current_ratio=None,stage=' · '.join(dict.fromkeys(filter(None,stages))),shape=''))
    latest=read(runtime/'latest.json'); state=read(runtime/'state.json')
    assert state['formula_sha256']=='2b14f16e047413b4d2d58e5f70c3f840690c495293b6b31311fc7b3018c3f491','Unexpected CL20 formula'
    events={}
    for page in state.get('outbox',[]):
        for e in page.get('events',[]):
            if page.get('market') not in ('CN','US','HK'): continue
            row={k:e.get(k) for k in ('code','name','label','kind','pivot_time','bar_end','price','detected_at')}
            row['market']=page['market']
            row['detected_at']=row['detected_at'] or page.get('created_at')
            row['replacement']=e.get('replacement') if isinstance(e.get('replacement'),str) else None
            channels=page.get('channels',{})
            row['delivery']='Server酱已接收' if channels.get('serverchan3',{}).get('status')=='accepted' else '待确认'
            key=tuple(str(row[k]) for k in ('code','label','kind','pivot_time','detected_at'))
            events[key]=row
    rows=sorted(events.values(),key=lambda e:e['detected_at'] or '',reverse=True)[:300]
    return dict(schema_version=1,a=dict(date=pointer['asof'],next_session=pointer['next_session'],verified=True,rows=ar),m=dict(date=m['as_of'],verified=True,rows=mr),cl20=dict(updated_at=latest.get('finished_at'),status=latest.get('status'),verified=len(latest.get('verified',[])),attempted=latest.get('attempted'),failed=len(latest.get('failures',[])),rows=rows))

def main():
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=pathlib.Path,required=True);p.add_argument('--runtime',type=pathlib.Path,default=pathlib.Path.home()/'Library/Application Support/CodexCL20/outputs/cl20_watchlist_trial');p.add_argument('--output',type=pathlib.Path,default=pathlib.Path('a-share-workbench/observation-feeds.json'));args=p.parse_args()
    payload=build(args.source_root,args.runtime);raw=(json.dumps(payload,ensure_ascii=False,indent=2)+'\n').encode()
    if args.output.exists():
        old=read(args.output); comparable=json.loads(json.dumps(payload))
        comparable['cl20']['updated_at']=old.get('cl20',{}).get('updated_at')
        if old==comparable: print('UNCHANGED');return
    tmp=args.output.with_suffix('.tmp');tmp.write_bytes(raw);tmp.replace(args.output)
    print('UPDATED',len(payload['a']['rows']),len(payload['m']['rows']),len(payload['cl20']['rows']),hashlib.sha256(raw).hexdigest())
if __name__=='__main__':main()
