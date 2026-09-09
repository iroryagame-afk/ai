# 中线系统研究同步

用户已于2026-09-09授权将中线系统研究内容写入 iroryagame-afk/ai，并发布到无需登录的 CSNPK 工作台及定期更新。

## 范围

入口 /a-share-workbench/#midterm，左侧栏目内直接阅读，不加入首页或公共导航。
每日北京时间17:40检查研究源；有内容变化才发布，无变化静默。该同步只更新现有研究，不启动五类交易任务、不扫描市场、不发送交易消息、不写账户或提醒。
规划中的09:10、盘中每5分钟、17:40、22:30、周日10:00分别保留规划状态，不把研究同步误称为完整交易系统上线。

## 来源和导出

从行业分析工作区 docs/a-trading-system-current.md 定位现行研究目录。现行为 outputs/a_trading_system_v2_20260909，规划为 docs/a-share-workbench-scheduling-plan-v1.md。
执行 scripts/build_midterm_system_data.py --source <现行研究目录> --plan <规划稿> --out <临时输出>/midterm.json。
导出器只读契约、已选研究表和汇总计数；不公开真实资金、成本、持仓数量、成交或私人计划。规划字段表只是规范，不是账户台账。
源版本改变时先复核映射；不可绕过导出器版本门禁。源文件并发变化则保留旧版，下轮重试。
比较导出内容与 origin/main 的 a-share-workbench/midterm.json；相同则不发布。保留源 as_of，不用同步时间冒充行情时间。

## 发布验收

遵守 docs/csnpk_refresh_runbook.md；从最新 origin/main 创建干净隔离工作树。常规只允许变更 a-share-workbench/midterm.json，必要的导出器适配单独说明。
检查公开字段、脚本语法和页面渲染；复用单一浏览器检查桌面及390px移动端。推送分支、PR合并后，从合并提交干净工作树单次部署，并用缓存穿透URL核对公开JSON/页面及SHA-256。
失败保留上一版，不修改其他栏目，不恢复退役页，不重复已有Server酱扫描。
