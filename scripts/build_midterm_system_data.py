#!/usr/bin/env python3
"""Read-only, allowlisted publication of the current trading-system research."""
import argparse,hashlib,json,re
from pathlib import Path
from datetime import datetime,timezone
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
names=['system_contract.json','优化结果.md','runtime/system_status.json','final_risk15_results.json','verification_summary.json']
raw={n:(a.source/n).read_bytes() for n in names}
c=json.loads(raw['system_contract.json']);status=json.loads(raw['runtime/system_status.json']);v=json.loads(raw['verification_summary.json']);result=json.loads(raw['final_risk15_results.json']);report=raw['优化结果.md'].decode()
if status.get('risk_policy',{}).get('version')!=c['version']:raise SystemExit('Source version mismatch; retain published snapshot')
if c['version']!='A-EXEC-2.0.0-research':raise SystemExit('New contract: review renderer before publication')
# Only explicitly chosen research tables; never publish accounts, raw ledgers or plans.
def table(section):
 part=report.split('## '+section,1)[1].split('\n## ',1)[0]
 lines=[x.strip().strip('|').strip() for x in part.splitlines() if x.startswith('|') and not re.fullmatch(r'[| :\-]+',x)]
 return '\n'.join(x.replace('**','').replace('`','') for x in lines)
plan_raw=a.plan.read_bytes();plan=plan_raw.decode()
def plan_table(section):
 part=plan.split('**'+section+'**',1)[1].split('\n**',1)[0]
 rows=[x.strip().strip('|').strip() for x in part.splitlines() if x.startswith('|') and not re.fullmatch(r'[| :\-]+',x)]
 if not rows:raise SystemExit('Planning source section missing')
 return '\n'.join(rows)
checks=c['validation_policy'];budget=c['research_budgets'];stats=result['statistics']
body='## 仓位与回撤\n'+table('现在采用的研究基线')+'\n开仓上限约束新增买入；被动上涨不自动再平衡。15%是风控目标，不是回撤保证。\n'
body+='## 买入与分批\n完整A模型资格＋板块开放＋风险预算＋有效价格计划，才形成正式买单。第二底分型只作优选；过期关键K不能靠MACD/KDJ改善重新生效。\n每笔分批重新核验资格和剩余风险；自动加仓关闭，未成交部分单独保留。\n'
body+='## 持有与退出\n'+table('拿、买、卖如何分开')+'\n'
body+='## 事件路线\n路线|入场要求\nMODEL_ONLY|完整A模型独立形成计划\nMODEL_EVENT|模型合格＋事件事实及公司受益证据；主选1只、备选最多1只\nEVENT_PILOT|实验观察，不生成正式买单\n'
body+='## 历史研究对照\n已见开发样本 · 2023-01-03—2026-09-09 · 96只股票 · 非样本外业绩\n'+table('实际回测结论')+'\n候选历史仅触发8%降档；12%和15%规则尚无该候选历史触发验证。核心仓、真实账户及完整历史模型资格未纳入。\n'
body+='## 当前进度\n项目|结果\n正式买入计划|'+str(status['formal_buy_plans'])+'\n事件线索|'+str(status['unique_clues'])+'\n已核验公司映射|'+str(status['stock_mappings_verified'])+'\n工程检查|'+str(v['passing_tests'])+'通过 / '+str(v['expected_failures_in_frozen_historical_interfaces'])+'项预期失败 / '+str(v['unexpected_failures'])+'项意外失败\n前瞻跟踪|'+('已启动' if checks['prospective_started'] else '未启动')+'\n实盘下单|'+('源系统已开启' if status['orders_enabled'] else '未开启')+'\n买卖推送|'+('源系统已开启' if status['delivery_enabled'] else '未开启')+'\n'
body='## 工作台模块\n'+plan_table('一、工作台应汇总的内容')+'\n## 更新时间 · 待启用\n'+plan_table('二、五个逻辑任务')+'\n## 计划字段\n'+plan_table('五、计划记录与推送格式')+'\n## 接入顺序\n计划台账 → 模型与事件 → 静默运行 → 实际持仓与成交 → 页面与GPT提醒 → 富途点位提醒。\n持有第3—5、10、20个交易日复核，不是强制卖出日。\n'+body
if a.plan.read_bytes()!=plan_raw:raise SystemExit('Plan changed while reading')
# Detect a concurrent source write; retry on a later tick instead of mixing revisions.
if any((a.source/n).read_bytes()!=b for n,b in raw.items()):raise SystemExit('Source changed while reading')
d={'schema_version':1,'version':c['version'],'selection_model':c['selection_model'],'status':'研究基线','as_of':status['as_of'],'source_digest':hashlib.sha256(b''.join(n.encode()+raw[n] for n in names)+plan_raw).hexdigest(),'source_files':names+[a.plan.name],'scheduling_status':'PLANNED_NOT_ENABLED','body':body}
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');print('Exported research rules; digest',d['source_digest'])
