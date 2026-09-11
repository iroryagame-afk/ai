# 每日选股名单同步

独立栏目 /a-share-workbench/#daily-selection，只消费任务《整合逻辑推送每日A股选股》local/01a08a14-1c46-7be1-8696-80258b3ef05d 最新明确交付结果，不自行扫描或推送。当前交付为日线主升延续C类，不恢复早期讨论的A/B类。

先read_thread核对最新交付路径，当前股票工作区outputs/daily_trend_watchlist/20260910/result.json及report.md。使用scripts/build_daily_selection_data.py --source <result.json> --out <临时JSON>；版本或结构改变时审查适配，不混入全自选、账户或旧结果。

与origin/main:a-share-workbench/daily-selection.json比较，无变化不发布。保留源日期、观察/偏远状态和核验范围；页面展示不等于消息已送达。合并到已有工作台17:40同步，两个来源分别导出，一次校验和发布；不改变原扫描或提醒任务。

发布遵守docs/csnpk_refresh_runbook.md，干净最新origin/main工作树、视觉检查、PR、单次部署、公网JSON哈希和业务HTML回读。不加入全站导航。
