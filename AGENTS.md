# csnpk 发布仓库规则

## 分析报告导航

- 向 `csnpk.com` 新增或首次公开发布专题策略、行业研究或公司深度分析报告时，必须在同一轮修改中更新 `nav/reports.json`。
- `nav/reports.json` 只收录已公开、可长期阅读的分析报告。`CSN`、`csn2`、A 股资金流、美股板块资金流等每日或动态更新页，以及工具包和非投研内容不得收录。
- 修改后必须运行 `python3 scripts/validate_report_nav.py`，不得绕过清单字段、重复项、排除项和本地链接检查。
- 发布验收必须同时覆盖报告公开 URL、`/nav/` 和 `/nav/reports.json`；导航页必须能搜索到新报告。
- Cloudflare 线上验收使用带时间戳参数的 cache-busting URL。未完成公开回读时，不得声称报告或导航已经上线。
- 报告被删除、改名或更换公开路径时，必须同步更新清单，避免死链。

详细规则见 `docs/report-nav-policy.md`。
