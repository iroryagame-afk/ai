# 外部工具吸收评估（2026-07-16）

只记录可复用设计，不复制第三方代码。需要重新调研时优先打开官方文档或原仓库。

| 工具 | 已核验能力 | 吸收内容 | 当前不吸收 |
|---|---|---|---|
| [Longbridge MCP](https://open.longbridge.com/docs/mcp) | 官方托管 MCP，提供行情、K线、指标、研究、账户、提醒及交易工具 | 数据源适配器思想、OAuth 最小权限、行情与提醒分层 | 不替换本地 Futu 主源；不让形态 Skill 调订单工具 |
| [TradingAgents-CN](https://github.com/hsliuping/TradingAgents-CN) | 多角色金融研究框架，覆盖技术、基本面、新闻和风控 | 把结论拆成证据、反证、风险门；保留 Bull/Bear 两面检查 | 不以多 Agent 投票数当证据；不引入其商业授权约束代码 |
| [daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis) | 多市场分析、技术指标、提醒、历史记录和事后回测 | 版本化记录、20/60 日回看、数据块缺失原因、fail-open 标记 | 不复制其大而全运行栈，不混入未经核验的行情 fallback |
| [UZI-Skill](https://github.com/wbh604/UZI-Skill) | 多维证据、深度档位、评分校准和大量回归测试 | 快/标准/深度审计思路、证据阶梯、评分组件可审计 | 不复制人物角色话术，不用“共识人数”制造精确感 |
| [TA-Lib](https://ta-lib.org/) | 200 类指标和 K 线形态识别，成熟 C 核心及 Python 封装 | RSI/MACD/量价等确定性候选；K线组合作为辅助信号 | K线函数不能替代中期图形、关键位置和完成K线确认 |
| [stock-pattern](https://github.com/BennyThadikaran/stock-pattern) | 反向头肩、双顶、三角、VCP、谐波等扫描与回测 | 扩展分类、候选扫描后必须人工/规则复核 | GPL 代码不复制进本 Skill；作者也明确其不能替代交易者判断 |
| [chart_patterns](https://github.com/zeta-zetra/chart_patterns) | 双底顶、头肩、三角、旗形和三角旗的参数化扫描 | 结构线、比率容差、同形态多候选比较 | 无发布版本且验证有限，不直接作为生产依赖 |
| [Hugging Face candlestick models](https://huggingface.co/models?other=candlesticks) | 存在 YOLO 等截图检测模型与 Spaces | 仅作为截图候选发现的可选实验层 | 未看到足够跨市场、复权、周期和样本外验证，不进入主判或提醒写入 |

## 当前采用的架构

1. 数据层：Futu OpenD 主源；其他 MCP 只作带来源标记的交叉检查。
2. 候选层：规则/指标/视觉模型可以提出多个候选。
3. 审计层：用几何、触点、量价、突破、回踩、动量、市场七项评分，并写次选和反证。
4. 决策层：A/B/C 只写条件路径，不给主观概率。
5. 执行层：提醒与订单严格分开；提醒写入仍需明确授权和回读。
6. 校准层：保存当时计划，在 20/60 日后做事后验证，避免只记住成功图形。
