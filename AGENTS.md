# csnpk 发布仓库规则

## 分析报告导航

- 向 `csnpk.com` 新增或首次公开发布专题策略、行业研究或公司深度分析报告时，必须在同一轮修改中更新 `nav/reports.json`。
- `nav/reports.json` 只收录已公开、可长期阅读的分析报告。`CSN`、A 股严选、轮动雷达等每日或动态更新页，以及工具包和非投研内容不得收录。
- 修改后必须运行 `python3 scripts/validate_report_nav.py`，不得绕过清单字段、重复项、排除项和本地链接检查。
- 发布验收必须同时覆盖报告公开 URL、`/nav/` 和 `/nav/reports.json`；导航页必须能搜索到新报告。
- Cloudflare 线上验收使用带时间戳参数的 cache-busting URL。未完成公开回读时，不得声称报告或导航已经上线。
- 报告被删除、改名或更换公开路径时，必须同步更新清单，避免死链。

详细规则见 `docs/report-nav-policy.md`。

## 页面体系

- 当前正式页面、导航分组、退役入口和验收边界以 `docs/csnpk-page-registry.md` 为唯一清单。
- 修改核心导航时，必须同步修改对应生成器与已发布静态页；不得只修线上副本，导致下次生成回退。
- `/mda100/`、`/a-share-market/`（含 `/etf/`）、`/a-share-thrust/`、`/a-share-rotation/`、`/a-share-ai-software/`、`/a-share-ai-hardware/` 与 `/a-share-flow/` 均已退役并保持 404；`/csn2/` 与 `/earnings/` 也保持下线。
- 公网页面成功返回不等于数据已刷新；数据日期、生成时间和核验状态必须按各页面自身标记判断。

## GitHub 共享工作台

- GitHub Issue 是具体任务的任务合同；仓库文档保存长期规则；PR/Commit 保存代码证据；`tasks/current/issue-<编号>.md` 保存逐任务交接。聊天不得成为重要条件的唯一载体。
- 接手任务时按 `Issue → tasks/current/issue-<编号>.md → PR/Commit → 当前数据重新核验` 的顺序恢复上下文。Issue 与仓库规则冲突时，先暂停并向用户指出冲突。
- `docs/HANDOFF.md` 只作索引，不保存所有任务过程；并行任务不得共同覆写一个总交接正文。
- Issue 必须写明外部写入授权。读取、修改本地文件、推送分支、创建 PR、更新 Issue、部署线上、修改 Secrets 分别授权；未勾选的动作不得自行扩大。
- 每个任务使用独立分支，默认命名为 `codex/issue-<编号>-<slug>`。只暂存本任务文件，不混入其他工作树改动。
- 任务结束前更新对应交接文件。若 Issue 已授权更新，则同步留言；若未授权或工具不可用，提供可复制的留言并明确“GitHub Issue 未更新”。
- 任务状态只使用：`planned`、`in_progress`、`blocked`、`ready_for_review`、`merged`、`deployed_unverified`、`published_verified`。
- 只有已推送快照完成部署、cache-busting 公网回读和必要的视觉核验后，才允许标记 `published_verified`。任何硬门失败时保留线上旧版并如实记录。
- 详细流程、数据规则和验收要求见 `docs/WORKFLOW.md`、`docs/DATA_SOURCE_RULES.md` 与 `docs/RELEASE_CHECKLIST.md`。
