# 美股工作台同步

独立公开入口 `/us-share-workbench/`；无需登录，不加入首页、nav或其他公共导航。

## 来源
- 今晚计划：股票工作区 `outputs/us_daily_abc/tonight/latest.json`，仅M观察实际10只的最多3只执行候选。
- 盘前情报：只读对话 `6a9a7dcb-1e38-83ea-84db-ac72c475766d`《20点：美股情报与候选股》，取最新完整盘前报告，保留原日期、冻结时点、原文和来源链接。不可用时保留旧报告，不用对话updatedAt替代报告日期。
- M观察与收盘复盘：`outputs/us_daily_abc/latest.json`。只用完整RTH日线，selected最多10只，扩展候选独立显示；收盘复盘为模型计划快照，不冒充独立云端收盘报告。
- CL20：`~/Library/Application Support/CodexCL20/outputs/cl20_watchlist_trial/state.json`，先过滤US，再取最近300条，保留撤销/修订、B?/S?与拐点时间。检测时间显示北京、拐点显示纽约。
- 半小时结构：`outputs/us_30m_changes/scan_latest.json` 和 `latest_result.json`；个股行情、QQQ/SPY、财报日历同时有效且扫描水位一致才显示个股变化。板块不作为单独股票名单。

## 执行
在origin/main干净隔离worktree运行：
`python3 scripts/build_us_workbench.py --source-root '/Users/lingliang/Documents/Codex/股票分析'`

页面同步只读取研究产物；不得触发扫描、下单、富途名单/提醒/备注写入、Server酱发送或CL20 ack。原任务各自生成内容。任一来源缺失或验证失败则不覆盖已发布数据，报告具体故障。原始账户字段与消息凭据禁止复制进公开仓库。

## 调度
北京时间工作日20:15至23:45及00:15至05:45每30分钟检查，另06:15接收收盘结果；周六早晨06:15允许归档纽约周五收盘，周末不运行盘中扫描。此任务仅同步，不改变原监测任务的时段。以America/New_York及各源真实时间解释夏冬令时。内容无变化立即结束；文件不因墙上时间改变而重写。

## 发布验收
只提交us-share-workbench及本同步器、测试、注册表合同相关变更。运行数据边界测试、JS语法检查与manifest验证；变更时复用单个浏览器完成桌面/手机视觉及筛选验收。Git推送、合并、一次Cloudflare部署、缓存穿透公网全部文件SHA256回读后才称已更新。HTML仅剔除Cloudflare注入的analytics脚本再比对。保留真实源日期，不将检查时间当数据日期。
