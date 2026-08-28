# CSNPK 全站刷新运行手册

状态：现行
生效日期：2026-08-23
机器合同：docs/csnpk-refresh-manifest.json
页面权威：docs/csnpk-page-registry.md

## 1. “全部刷新”的准确含义

“全部刷新”不是把仓库内每个 HTML 重新生成一遍，而是按页面刷新类型独立处理：

1. 收盘型页面：只有对应市场出现新的完整交易日才生成。
2. 事件型页面：按事件扫描自己的时间窗更新，不受 CN/US 收盘门禁阻塞。
3. 静态研究页：只有研究内容、来源或页面结构改变时更新。
4. 派生门户：只在其上游页面真实变化后重算。
5. 兼容页：仍公开且仍有动态数据的继续随市场刷新；纯重定向页只核验跳转。
6. 退役路由：必须保持不存在并在公网返回 404，禁止从旧树、缓存或生成器恢复。

任何页面组失败都只阻断该页面组及其下游，不覆盖其他已通过页面。报告必须逐组写明 changed、no_new_market_date、source_gate_failed、generator_failed、published_verified 或 retired_404_verified。

## 2. 工作树硬门

1. 先 git fetch origin --prune。
2. 发布只能从最新 origin/main 创建干净隔离 worktree。
3. 固定发布目录若落后远端、含未提交文件或含退役页面，一律视为不可信输入；不得在原地挑文件发布。
4. 生成器写入临时输出目录，校验通过后才同步到隔离 worktree。
5. 只暂存本轮清单允许的文件。不得使用 git add -A。
6. 旧 worktree 删除前必须确认：
   - HEAD 已被 origin/main 包含，或唯一提交已明确放弃；
   - worktree 无未提交成果，或未提交成果已明确放弃；
   - 当前定时任务和浏览器会话未占用该目录。

## 3. 刷新分组与顺序

### 3.1 CN 完整收盘组

门禁：OpenD 已连接；最新 CN 完整交易日大于对应公网页日期；覆盖率、财报日历和 T+1 边界通过。

顺序：

1. scripts/scan_a_long_reversal_candidates.py
2. scripts/generate_a_trend_candidates_page.py
3. scripts/build_futu_a_share_software_hardware_pages.py
4. scripts/build_futu_a_share_biotech_defensive_pages.py
5. scripts/add_deleveraging_index_charts.py
6. 校验并同步：
   - /a-share-trend-candidates/
   - /a-share-software-deleveraging/
   - /a-share-hardware-deleveraging/
   - /a-share-biotech-trend/
   - /a-share-dividend-defense/

7. `scripts/generate_bingshen_market_radar.py`：使用 Futu OpenD 全市场只读快照与腾讯指数日期交叉核验，生成 `/bingshen/data.json`；有效覆盖低于 5000 只、日期不一致或 15:00 完整收盘未就绪时保留公网上一版。再通过腾讯自选股只读接口生成同交易日 `/bingshen/tencent-snapshot.json`，覆盖冰神 17 只观察池的筹码、十大流通股东机构席位和北向季度持仓；生成 `/bingshen/fund-flow-snapshot.json`，覆盖全市场个股与申万行业单日主力净流入，三份文件交易日必须一致。封单额、开板次数等未接入字段必须明确留空，不用演示数据补位。

六页必须分别读取自己的 data.json 日期，不能互相代替。产业图谱 /a-share-domestic-compute/、/a-share-supply-tightness/、/a-share-next-generation/ 和兼容总表 /a-share-t1-focus/ 属于研究更新，不随每日收盘强制重写。

### 3.2 US 完整收盘组

门禁：OpenD 已连接；最新 US 完整交易日大于对应公网页日期；行情、期权、财报日历和覆盖率硬门通过。

推荐顺序：

1. rs-thrust-web/scripts/refresh_rs_thrust.py，生成 /rs-thrust/ 与 /rotation/。
2. scripts/generate_csn_hotlist_html.py，生成 /csn/hot/。
3. scripts/build_ai_software_monitor.py 分别运行 software 与 hardware，生成两个铲子监控台。
4. scripts/scan_us_long_reversal_candidates.py 与 scripts/generate_us_trend_candidates_page.py。
5. scripts/build_us_watchlist_skew_snapshot.py，生成 /us-skew/。
6. scripts/build_futu_software_deleveraging_page.py，生成 /us-software-deleveraging/。
7. scripts/add_deleveraging_index_charts.py，更新去杠杆页面指数图；/ai-infrastructure-deleveraging/ 的日期以 index-chart.json 为准。
8. scripts/build_csn_integrated_recommendations.py，重算 /csn/。
9. scripts/build_macro_fiscal_risk_monitor.py，更新 /macro-fiscal-risk/；不同频率来源保留各自日期。
10. scripts/build_us_market_observation.py，最后聚合 /us-market/。
11. 首页只在其依赖页面真实变化后重算。
12. 所有生成页面同步到隔离 worktree 后，统一运行 scripts/restructure_site_nav.py；单页生成器内的旧导航只视为临时壳，不得直接发布。

/us-market/ 不得再读取已退役 /ai-decision/。X/Reddit 注意力扫描是独立上游；没有新内容、扫描受限或证据不足时保留上次已核验摘要，不得阻塞美股行情聚合。

### 3.3 独立事件组

- /macro-event-radar/：候选采集和人工/规则核验分层；partial 不能伪装 complete。
- /us-market/x-consensus/：社交线索、作者图表与 OpenD 行情分层；扫描时间、帖子时间和行情日期分别保留。
- weekly-event-transmission-YYYYwWW：每周创建新目录；旧周保持快照，不在原目录冒充新周。只有 US 与 A 股子页都通过后才更新共享导航。

独立事件组失败不阻塞 CN/US 收盘组。

### 3.4 内容变更组

- /nav/：只有长期报告新增、删除、改名或路径变化时更新，并运行 scripts/validate_report_nav.py。
- /code/：只在代码包或说明改变时更新；/bingshen/ 已转为 A 股每日收盘型页面，按 3.1 的独立数据门禁刷新。
- 长期行业、专题和公司报告：不参与每日全站刷新；更新时按 docs/report-nav-policy.md 发布。
- /futu-indicators/：只核验跳转到 /code/，不得恢复为独立工具页。

## 4. 本地校验

每轮至少执行：

1. python3 scripts/validate_csnpk_refresh_manifest.py
2. python3 scripts/validate_report_nav.py
3. 页面内部链接、重复 ID、title、lang、viewport、外链 rel、脚本语法检查。
4. 所有本轮收盘型页面的 freshness 字段等于目标完整交易日；慢频来源只要求保留真实来源日期。
5. 15 个退役路由在隔离 worktree 中不存在。
6. 生成器和发布静态页同轮更新，避免下次生成回退。
7. 运行共享导航生成器和 tests/test_site_navigation.py，禁止单页生成器把旧导航重新带回线上。

## 5. 发布与公网验收

1. 提交隔离 worktree 的允许变更。
2. 推送前重新确认分支基于最新 origin/main；发生远端推进时先 rebase 并重跑校验。
3. 一个提交快照只执行一次 Cloudflare 部署。
4. 用缓存穿透 URL 回读本轮页面、JSON、Markdown、图片和重定向。
5. 公网文件 SHA-256 必须与推送提交一致。
6. 退役路由逐一确认 404；/futu-indicators/ 单独确认跳转。
7. 只有本轮真实改页才进行视觉 QA；复用一个已授权浏览器会话、一个测试标签页，检查桌面端、390px 移动端、破图、错误文本、横向溢出和主要交互。

只有 Git 推送、单次部署、缓存穿透日期回读、SHA-256 和必要视觉 QA 全部通过，才能称 published_verified 或“已刷新”。

## 6. 失败时的保留策略

- no_new_market_date：不运行该市场生成器，不部署，不做视觉 QA。
- OpenD、覆盖率、财报日历或日期不一致：保留线上上一版。
- 独立慢频数据未更新：保留旧值并显示旧日期，不用空值或猜测覆盖。
- 浏览器不可用：标记 visual_qa_unavailable，不冒充视觉通过。
- 推送、部署或公网哈希失败：状态最多为 deployed_unverified，不称已刷新。
- 任一生成器重新产生退役路由：整轮失败，删除生成产物并修生成器后重跑。
