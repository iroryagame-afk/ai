#!/usr/bin/env python3
"""Read existing US research; publish only allowlisted fields. No scan or broker calls."""
import argparse
import json
from pathlib import Path

def read(p):
    return json.loads(p.read_text())

def build(root, runtime):
    m = read(root/'outputs/us_daily_abc/latest.json')
    assert m['final_readback_ok'] and m['opend_connected'] and m['session'] == 'RTH'
    assert len(m['selected']) <= 10
    rows = []
    for code in list(m['selected']) + [c for c in m['candidates'] if c not in m['selected']]:
        r = m['candidates'][code]
        if not code.startswith('US.') or r.get('unknown') or not r.get('identity_verified'):
            continue
        lanes = r.get('lanes', {})
        if r['sources'] == ['C'] and '位置偏远' in lanes.get('C', {}).get('stage', ''):
            continue
        stages = [lanes[x].get('status', lanes[x].get('stage', '')) for x in r['sources'] if x in lanes]
        a = lanes.get('A', {})
        rows.append(dict(code=code, name=r['name'], in_futu=code in m['selected'], category=' / '.join(r['sources']), stage=' · '.join(dict.fromkeys(filter(None, stages))), key_date=a.get('key_date') if 'A' in r['sources'] else None, volume_ratio=a.get('volume_ratio_raw') if 'A' in r['sources'] else None))
    t = read(root/'outputs/us_daily_abc/tonight/latest.json')
    assert t['scope'] == 'M观察' and t['daily_as_of'] == m['as_of']
    fields = ('code','name','quote','quote_session','action','first_observation','buy_confirmation','maximum_acceptable','invalidation','first_reduce','final_target','initial_position_pct','intraday_confirmation')
    tonight = {k:t[k] for k in ('generated_at_bj','daily_as_of','market_gate_closed')}
    tonight['candidates'] = [{k:r.get(k) for k in fields} for r in t['candidates']]
    assert all(r['code'] in m['selected'] for r in tonight['candidates'])
    state = read(runtime/'state.json')
    assert state['formula_sha256'] == '2b14f16e047413b4d2d58e5f70c3f840690c495293b6b31311fc7b3018c3f491'
    events = {}
    for page in state.get('outbox', []):
        if page.get('market') != 'US':
            continue
        for e in page.get('events', []):
            if not str(e.get('code', '')).startswith('US.'):
                continue
            r = {k:e.get(k) for k in ('code','name','label','kind','pivot_time','bar_end','price','detected_at')}
            r['detected_at'] = r['detected_at'] or page.get('created_at')
            r['replacement'] = e.get('replacement') if isinstance(e.get('replacement'), str) else None
            key = tuple(str(r[k]) for k in ('code','label','kind','pivot_time','detected_at'))
            events[key] = r
    clrows = sorted(events.values(), key=lambda r:r['detected_at'] or '', reverse=True)[:300]
    scan = read(root/'outputs/us_30m_changes/scan_latest.json')
    result = read(root/'outputs/us_30m_changes/latest_result.json')
    aligned = bool(scan.get('structure_asof') and scan.get('structure_asof') == result.get('structure_asof'))
    ready = bool(scan.get('verified') and scan.get('benchmark_verified') and scan.get('earnings_calendar_verified') and aligned)
    changes = []
    if ready and scan.get('structure_asof') == result.get('structure_asof'):
        for e in result.get('changes', []):
            if e.get('entity_type') != 'stock' or not e.get('code','').startswith('US.'):
                continue
            r = e.get('row', {})
            changes.append(dict(code=e['code'], name=r.get('name'), change=e.get('change'), asof=e.get('asof'), board_name=r.get('board_name')))
    close = []
    for code, p in m.get('trading_system', {}).get('plans', {}).items():
        if code not in m['selected']:
            continue
        close.append(dict(code=code,name=p['name'],status=p['status'],close=p['latest_close'],confirmation=p['entry'].get('confirmation_price'),invalidation=p['exit'].get('invalidation_price'),reduce=p['exit'].get('reduce_price'),target=p['exit'].get('final_target_price'),review=p['holding'].get('review_trading_day')))
    return dict(schema_version=1,m=dict(date=m['as_of'],rows=rows),tonight=tonight,cl20=dict(latest_event_at=clrows[0]['detected_at'] if clrows else None,rows=clrows),structure=dict(asof=scan.get('structure_asof'),ready=ready,status='已核验' if ready else '个股通道冻结：财报日历未核验' if not scan.get('earnings_calendar_verified') else '个股通道待核验',rows=changes),post=dict(date=m['as_of'],rows=close))

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--runtime', type=Path, default=Path.home()/'Library/Application Support/CodexCL20/outputs/cl20_watchlist_trial')
    p.add_argument('--output', type=Path, default=Path('us-share-workbench/data.json'))
    a=p.parse_args(); data=build(a.source_root,a.runtime)
    raw=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
    if a.output.exists() and a.output.read_text()==raw:
        print('UNCHANGED');return
    a.output.with_suffix('.tmp').write_text(raw);a.output.with_suffix('.tmp').replace(a.output)
    print('UPDATED',len(data['m']['rows']),len(data['cl20']['rows']))

if __name__=='__main__':main()
