---
name: stock-pattern-scenario-reminders
description: 跨市场股票技术形态识别、结构质量审计、关键决策区/趋势线标注、三情景路径图、高清 PNG 和富途操作提醒 Skill。用户问头肩底/顶、双底/顶、三重底/顶、复合/圆弧/V形底顶、杯柄、箱体、三角形、旗形/三角旗、楔形、通道、VCP、缺口、K线组合、指标背离、是否突破或跌破、后续走势画图、截图识别、富途关键位提醒时应使用；即使只发代码说“也做一个”也沿用本流程。适用于 A股、港股和美股。不得把候选识别当成确定预测；提醒写入必须获得明确授权，写后必须回读。
compatibility: 需要项目 `.venv`、本机 Futu OpenD `127.0.0.1:11111`；PNG 默认使用本机 Chrome 无界面渲染，可能需要主机权限批准。
---

# 股票形态情景图与富途提醒

## 目标

把“看起来像某个形态”变成可复核的完整交付：

1. 用 Futu OpenD 核验最新快照和至少 250 根已完成日线。
2. 比较主判与至少一个合理次选，允许结论是“混合、近似、尚未形成”，不要硬套形态。
3. 给出决策区、结构线、确认位、第一风险位和形态失效位。
4. 画三条条件路径：有效突破、区间/假突破、跌破失效。
5. 用户要图片时输出裁切后的高清 PNG，方便直接复制粘贴。
6. 用户明确授权后，把关键价位与具体操作写入富途提醒并回读核验。

提醒只是观察工具，不是订单；本 Skill 不下单、不撤单、不改单。

## 路由

- A股具体买卖执行语义叠加 `../a-stock-position-timing/SKILL.md`。只接收它的 T+1 执行结果，不复制涨跌停、停牌、集合竞价和回测规则。
- 美股/港股具体买卖执行语义叠加 `../stock-position-timing/SKILL.md`。只接收它的盘中/波段执行结果，不复制 VWAP、首15分钟和同日止损规则。
- 历史回撤概率、斐波那契主次节点和 ABC 扩展继续使用 `../stock-drawdown-alerts/SKILL.md`。
- 订单操作只能使用 `../futuapi-confirmed-trade/SKILL.md`，到价提醒不得升级为订单授权。

形态问题只回答“结构是什么、是否确认、哪里失效”时，不必运行完整择时 Skill。用户进一步问“能不能买、怎么操作、已有仓位怎么办、明天/盘中怎么做”时，必须生成 `timing_overlay` 并调用对应市场的择时 Skill。结构质量高不自动等于可买。

## 工作流

### 1. 拉取并核验数据

使用项目虚拟环境，避免系统 Python 缺少 `futu-api`：

```bash
HOME=.runtime/futu_home .venv/bin/python \
  .agents/skills/stock-pattern-scenario-reminders/scripts/fetch_pattern_data.py \
  --code US.PLTR \
  --output outputs/stock-pattern-analysis/pltr-data.json
```

脚本输出：

- 快照及更新时间，区分正常时段、盘后和隔夜；
- 前复权日线、EMA20/55/200、ATR14、RSI14、MACD；
- 20 日量比、布林带宽、20/60 日收益和 55 日高低点；
- 局部高低点；
- 美股附带 QQQ/SPY 的 EMA20/55 市场闸门。

OpenD 未连接时停止精确点位结论，明确写 `未完成实时核验`。

Futu OpenD 是本项目默认权威行情源。Longbridge MCP、截图识别或其他数据源可以作为独立交叉检查，但必须记录来源和时间，不得静默混用复权口径。Longbridge 也包含交易工具；本 Skill 只允许使用其行情/研究/提醒能力，订单仍路由到确认交易 Skill。

用户只给截图时，先用视觉信息定位“候选形态和大概区间”，再回到 OpenD OHLCV 重算日期、价格、结构线和突破状态。截图像素不是精确提醒价格的证据。

按任务选择审计深度，避免每次都堆满指标：

- `quick`：回答“像不像/到没到关键位”，日线主结构 + ATR/量价，明确未完成项；不写提醒。
- `standard`（默认）：至少 250 根日线、七项结构评分、A/B/C、基准相对强弱和提醒计划。
- `deep`：加入周线背景、同业/基准比较、历史同类形态与 20/60 日事后记录；适合建仓前或复盘，不因更多分析自动提高评级。

### 2. 判断形态，不强行命名

完整分类、最低结构要求与反证见 [references/pattern-taxonomy.md](references/pattern-taxonomy.md)。优先分层检查：

外部工具的已核验能力、许可证/可靠性边界与吸收决定见 [references/external-tool-review.md](references/external-tool-review.md)。仅在用户要求比较或安装外部工具时读取该文件。

- 反向头肩底：左肩低点、较低头部、右肩较高低点，两个反弹高点形成颈线。
- 头肩顶：左肩高点、较高头部、右肩较低高点，两个回落低点形成颈线。
- 双底/三重底：低点接近，头部不明显时不要冒充头肩底。
- 复合底/圆弧底：底部持续时间长、低点数量多、颈线区较宽。
- 箱体/平台：高低边界重复测试，没有清晰肩头关系。
- 三角形、旗形/三角旗、楔形、通道：用至少两条可复核结构线描述，不用水平颈线替代斜线。
- VCP：检查多轮波动和成交量是否同步收缩，再看枢轴突破。
- 杯柄、V 形和岛形反转：确认其专属条件；若回踩不可执行，结论必须降级。
- K 线组合、缺口、RSI/MACD 背离：只作关键位附近的辅助证据，不独立替代主结构。

高级谐波形态只有各腿比例落入预先声明的容差才标注。艾略特波浪默认不进入提醒主线。

形态至少分三档表述：

- `成立并已确认突破`
- `候选结构，正在测试颈线`
- `不成立，更接近其他结构`

影线刺穿不等于有效突破。默认把确认分开：

- 激进：完成日 K 收在颈线之上。
- 稳健：收盘带 1% 左右缓冲，或连续两日站稳，并回踩颈线不破。
- 失败：重新收回颈线下方；跌破右肩/头部则形态降级或失效。

### 3. 评分证据，不把分数写成胜率

在计划 JSON 中填写 `assessment.components`，再运行：

```bash
.venv/bin/python \
  .agents/skills/stock-pattern-scenario-reminders/scripts/score_pattern_evidence.py \
  --plan outputs/stock-pattern-analysis/pltr-plan.json --write-back
```

评分分解为几何、触点/持续时间、量价、突破、回踩、动量、市场/相对强弱，总分只代表“形态命名质量”。低于 `high` 时至少保留一个 `alternatives`，并列出 `contradictions` 与 `missing_evidence`。这样吸收多视角审计的优点，同时避免用多 Agent 投票制造虚假确定性。

### 4. 形成情景计划

按 [references/pattern-plan-schema.md](references/pattern-plan-schema.md) 创建一个计划 JSON。每只股票独立一个文件，避免多票图挤在一起。

三条路径必须是条件情景，不写主观概率：

- A：主形态确认。底部/多头延续可以向上，顶部/空头延续可以向下。
- B：颈线震荡/假突破。写区间上下沿和等待条件。
- C：A 的反向失效路径。方向必须与 A 相反。

目标位可来自前高、缺口、平台高度或形态量度，但要标成研究目标，不得伪装成确定预测。

### 5. 需要操作建议时叠加择时覆盖层

读取 [references/timing-overlay-schema.md](references/timing-overlay-schema.md)，把两个择时 Skill 中可以共用的判断写入 `timing_overlay`：

1. 数据有效性；
2. EMA20/55/200 与主支撑的趋势生存；
3. ATR%、20日涨幅、EMA偏离的过热状态；
4. 宽基 + 风格/行业基准闸门；
5. 观察区、完成K线和回踩的确认状态；
6. 无仓、可卖昨仓、今日锁定新仓或混合仓状态；
7. 最终动作：等待、观察、候选、小仓执行、持有、减仓或回避。

然后按市场补充执行字段：

- A股：`T日信号 → T+1执行 → 新买最早可卖日`，以及平开/高开/低开三分支和可交易性检查。
- 美股：盘前/开盘观察/09:45后确认、VWAP/首15分钟触发、同日止损和 QQQ/SPY 放弃条件。
- 港股：保留同日交易语义，但使用港股匹配基准，不套 QQQ/SPY。

验证覆盖层：

```bash
.venv/bin/python \
  .agents/skills/stock-pattern-scenario-reminders/scripts/validate_timing_overlay.py \
  --plan outputs/stock-pattern-analysis/pltr-plan.json
```

验证器会阻止：未确认信号直接买、破位/过热/防守市场直接新开仓、A股当日卖出新仓、T日信号假设T日成交、美股盘前或首15分钟直接执行。

### 6. 生成图和 PNG

```bash
HOME=.runtime/futu_home .venv/bin/python \
  .agents/skills/stock-pattern-scenario-reminders/scripts/render_pattern_chart.py \
  --plan outputs/stock-pattern-analysis/pltr-plan.json \
  --output-dir outputs/stock-pattern-images \
  --png
```

默认输出：

- `<ticker>-scenarios.html`：可继续编辑的源图。
- `<ticker>-scenarios.png`：2800×1100 左右的横版高清图。

图中必须直接标注：形态点、决策区/结构线、结构质量（注明非胜率）、当前价/数据时间、A/B/C 路径、确认与失效条件。PNG 生成后要目视检查文字截断、重叠和大面积空白。

图面主标题必须同时包含股票名称和市场代码，统一为“股票名称（市场代码） · 日期 · 价格”；不再只显示代码。

未来路径区必须把“价格曲线”与“情景说明轨道”分开：A/B/C 说明块按各自曲线终点的价格高度动态排序，进行碰撞避让，再用同色引导线连接。说明标题、触发条件和目标位使用与曲线同色系的深色文字，不得再按 A/B/C 字母固定高度。

上述规则的目的是让读者在不查图例的情况下，也能立即看出每段说明属于哪条价格路径。PNG 交付前按以下清单验收：

- 说明块的垂直顺序与曲线终点的价格高低一致，而不是字母顺序。
- 每条路径同时使用曲线、终点圆点、引导线、A/B/C 文字和同色系完整边框，不只依赖颜色。
- 说明块不与其他说明块、价格曲线或决策区文字重叠；过长条件在块内换行或省略。
- 决策区标签放在历史侧或独立价格标签位，不侵入情景说明轨道。
- 渲染器变更后至少用“A 向上”、“A 向下”和“三个终点接近”三类计划回归，再目视检查实际 PNG。

图面形态标题只写最终识别到的正向分类，例如“高位复合顶部破位”或“复合双底候选”。不在图面写“非头肩底”、“不是双底”等排除性判断；被否定的形态只保留在 `assessment.contradictions` 或文字审计中。

### 7. 富途提醒：默认预览；同轮授权后随图自动写入

计划 JSON 的 `reminders` 默认只放三条，价格字段统一写 `price`；读取旧计划时兼容 `value`：

1. 向上确认位；
2. 第一风险位；
3. 形态彻底失效位。

备注不超过 20 个字符，优先写“触发 + 动作”，例如：

- `突破139｜不追·回踩136观察仓`
- `跌破123｜减仓·收复再看`
- `跌破106｜头部失效·止损`

先做只读预览：

```bash
HOME=.runtime/futu_home .venv/bin/python \
  .agents/skills/stock-pattern-scenario-reminders/scripts/sync_pattern_reminders.py \
  --plan outputs/stock-pattern-analysis/pltr-plan.json
```

只有用户明确说“写入、添加、更新、自动加富途提醒”后才执行。该指令只授权本轮明确点名的股票；不得跨股票、跨后续轮次沿用。

若本轮同时要求“做图 + 加提醒”，优先使用一条命令：PNG 成功生成后自动写入，随后立即回读。用户已经明确授权时不要重复追问：

```bash
HOME=.runtime/futu_home .venv/bin/python \
  .agents/skills/stock-pattern-scenario-reminders/scripts/render_pattern_chart.py \
  --plan outputs/stock-pattern-analysis/pltr-plan.json \
  --output-dir outputs/stock-pattern-images \
  --png \
  --apply-reminders --confirm WRITE_FUTU_PATTERN_REMINDERS \
  --reminder-output-dir outputs/futu-reminders
```

若图已生成，仅补写提醒，执行：

```bash
HOME=.runtime/futu_home .venv/bin/python \
  .agents/skills/stock-pattern-scenario-reminders/scripts/sync_pattern_reminders.py \
  --plan outputs/stock-pattern-analysis/pltr-plan.json \
  --output-dir outputs/futu-reminders \
  --apply --confirm WRITE_FUTU_PATTERN_REMINDERS
```

写入规则：

- 同股票同价使用 `MODIFY`，避免重复；否则 `ADD`。
- 修改后执行 `ENABLE`，避免已触发提醒继续停用。
- 频率固定为 `ALWAYS`。
- 不删除用户其他提醒。
- 写入后在同一次运行中回读价格和备注；只有全部一致才报告完成。
- 只写提醒，不下单、不改单、不启用任何自动交易。
- 触价只代表进入观察区。备注写“观察仓”时，仍需完成 K 线或回踩确认。

## 输出格式

```markdown
结论：标准形态 / 候选结构 / 不是该形态；是否已确认突破。

数据状态：
- Futu OpenD：
- 最新完成K线：
- 盘中/盘后/隔夜：

关键位：
- 决策区/结构线：
- 颈线/确认（如适用）：
- 回踩观察：
- 第一风险：
- 形态失效：

后续路径：
- A 主形态确认：
- B 区间/假突破：
- C 跌破失效：

择时覆盖（用户询问操作时）：
- 趋势/过热：
- 市场闸门：
- 信号状态：
- 仓位状态：
- 当前动作：
- A股T+1执行 / 美股盘中触发：

图片：HTML + PNG
富途提醒：未授权 / 已写入并回读 N/N
```

多只股票时先给一句相对结论，例如“PLTR 更像头肩底候选，TEM 更像复合三重底回踩”，再分别展示图片。

## 边界

- 局部极值和 ZigZag 有回看偏差，只用于结构标注，不宣称是当时可交易信号。
- 盘中快照可以判断是否正在触线，不能替代完成日 K 的突破确认。
- 美股新开仓措辞必须查看 QQQ/SPY；市场闸门防守时最多写“观察仓”。
- ATR% 超过 6% 或 20 日涨幅超过 25% 时，不写“追”，只写回踩或二次确认。
- 自动扫描、TA-Lib K 线函数、GitHub/Hugging Face 视觉模型只能生成候选；准确价格、复权、完成 K 线和失效条件必须由结构化行情复核。
- 不把“多个模型/多个角色意见一致”当成独立证据。只有来源、日期、价格、成交量和可复算规则才计分。
- 不复制两个择时 Skill 的市场专属规则。技术图形 Skill 保存统一信号层和交接结果；交易机制、手机卡模板和回测门槛仍以来源择时 Skill 为准。
- `assessment.score` 衡量形态命名质量；`timing_overlay.decision` 衡量当前可执行性。两者必须分开，不能用高形态分覆盖市场防守、过热、未确认或 T+1 风险。
- 形态提醒需要保留版本和事后验证记录；至少在 20/60 个交易日后回看突破、止损和目标命中，避免只展示成功案例。
- 未经明确授权不得写提醒；提醒授权也不等于交易授权。
