---
name: stock-drawdown-alerts
description: 跨市场个股/ETF历史回撤概率、ATR、同业验证、上涨修复/斐波那契扩展与富途关键节点提醒 Skill。用户提到“回撤节点、38.2/50/61.8/78.6、主概率/次概率、ATR回测、参考同类型股票、抄底后能涨到哪里、第一收复位、ABC扩展目标、把节点写进富途备注”时应使用，尤其适用于 A股、美股、港股持仓或观察池的批量处理。A股纯历史回撤/修复研究且不涉及同业概率或提醒写回时，继续使用 a-stock-drawdown-rebound。
compatibility: 需要本机 Futu OpenD 127.0.0.1:11111、项目 .venv 与 futu-api；提醒写入必须获得用户明确授权。
---

# 跨市场历史回撤与富途提醒

## 目标

把“画一组固定斐波那契线”升级为可复核的决策流程：

1. 用目标股票自身历史波段统计回撤分布。
2. 用 ATR14、时间衰减和同业股票交叉验证。
3. 分开“有效回撤支撑”与“回到/跌破前低”的失败情景。
4. 输出主概率、次概率、并列核心区和前低失效线。
5. 区分支撑试错、修复收复和突破后ABC扩展目标。
6. 用户明确授权后，把节点和动作写入富途提醒并回读核验。

这是一套价格行为与提醒管理工具，不是自动交易系统。触及节点只表示进入观察区。

## 路由边界

- A股纯历史回撤、反弹修复、价格密集区：使用 `a-stock-drawdown-rebound`。
- A股次日买卖执行：使用 `a-stock-position-timing`。
- 美股/港股当前买卖择时：使用 `stock-position-timing`。
- 只要任务包含“同业概率、ATR归一化、主次节点、富途提醒写回”，由本 Skill 负责节点计算与提醒；需要给交易动作时再叠加对应择时 Skill。
- 提醒不是订单。不得把提醒写入当成交易授权。

## 数据红线

1. 优先使用 Futu OpenD 的已完成前复权日线；只有真实连通才写 `VERIFIED_FUTU_OPEND`。
2. 默认截止上一自然日，避免混入未收盘日K。若用户要求盘中，快照只能决定提醒方向，不能改变历史完成K线统计。
3. 每只股票尽量使用至少250根日K；不足时标记样本不足，并增加同业权重。
4. 全部节点必须保留锚点日期、低点、高点、峰值是否已确认、ATR14和样本数。
5. ZigZag端点有回看偏差，不能宣称为当时可交易信号。

## 默认统计口径

完整方法见 [references/methodology.md](references/methodology.md)。执行时遵守：

- 标准候选比例：`38.2% / 50% / 61.8% / 78.6%`。
- `100%`只作为前低复测/失效线，不参与支撑概率排名。
- `>100%`单列为跌破前低的失败情景。
- `71.8%`不是经典 Fibonacci 主比例，默认禁用。只有用户明确要求且历史回测能证明其增量价值时才能启用，并标注“实验位”。
- 同时测试 `8% / 12% / 15% / 20%` ZigZag，降低单阈值偶然性。
- 使用Wilder ATR14；ATR用于波动归一化、节点合并与风险距离，不单独创造买点。
- 默认近期半衰期为756个交易日。
- 两个候选得分差小于1个百分点时，输出“并列核心区”，不得硬分主次。

## 工作流

### 1. 准备配置

复制 [references/config.example.json](references/config.example.json)，至少填写：

- `targets`：需要计算和写提醒的股票。
- `peers`：同类型股票及权重。
- `target_weight`：目标自身历史权重，默认60%。
- `start/end`：回测区间。

同业必须解释产业关系，不能只因为走势相似就加入。

### 2. 只读分析

```bash
HOME=.runtime/futu_home .venv/bin/python \
  .agents/skills/stock-drawdown-alerts/scripts/analyze.py \
  --config <config.json> --output <analysis.json>
```

先检查：

- OpenD状态与最后完成K线日期；
- 每只目标/同业的日K数量；
- 12%主阈值的已确认周期数；
- 多阈值排名是否稳定；
- 主次得分是否实际并列；
- 当前价格是否已经超过旧峰值，导致活动峰值尚未确认。

### 3. 形成节点

对每只目标输出：

- 当前锚点：低点日期/价格 → 峰值日期/价格；
- ATR14与ATR%；
- 自身统计、同业统计和合成统计；
- 主概率节点、次概率节点，或并列核心区；
- 前低失效线；
- 当前价格在节点上方还是下方。

触及节点的默认动作语义：

- 价格在节点上方：`到达观察`，等待止跌/收复确认。
- 价格在节点下方：`收复观察`，重新站回才算修复。
- 跌破前低：`跌破风控`。

### 4. 计算上涨修复与扩展

用户问“抄底后能涨到哪里”时，先把锚点写成 `A起涨低点 → B波段高点 → C候选/确认回调低点`：

```bash
HOME=.runtime/futu_home .venv/bin/python \
  .agents/skills/stock-drawdown-alerts/scripts/project_rebound.py \
  --low <A> --peak <B> --rebound-low <C>
```

输出分两层：

- 修复阶梯：只取C上方更浅一档的回撤位，再到23.6%和前高B。第一档是“第一结构收复位”，不是底部确认。
- 扩展阶梯：只有C被完成K线/回踩确认且B被收复后，才使用 `C + (B-A) × 0.618/1.0/1.272/1.618`。

如果C还在下移，只报修复位，扩展位标为“待C确认后重算”。不得把盘中瞬时低点写成已确认目标。

### 5. 写入富途

先展示将写入的价格与备注。只有用户明确说“写入/添加/更新富途提醒”后运行：

```bash
HOME=.runtime/futu_home .venv/bin/python \
  .agents/skills/stock-drawdown-alerts/scripts/sync_reminders.py \
  --analysis <analysis.json> --apply --confirm WRITE_FUTU_REMINDERS
```

写入规则：

- 每只股票默认只写两个统计节点和一个前低失效线。
- 两个统计节点的备注必须同时包含概率排序和得分，例如 `P1·38.2/44%`、`P2·78.6/29%`；得分差小于1个百分点时两档都写 `并1`。
- 同价提醒使用 MODIFY，避免重复。
- 不删除用户其他提醒。
- 富途备注控制在20个字符内。
- 默认使用 `ALWAYS` 重复提醒，每次再次满足条件时继续提醒，直到用户手动关闭；不得修改为自动下单。
- 修改已存在的节点后必须再执行 `ENABLE`，避免已触发过的节点仍处于停用状态、主图水平提醒线消失。
- A股备注的操作必须写“次日观察/次日风控”；美股/港股只写观察或风控，不承诺买入。

删除提醒属于独立破坏性动作。必须让用户指出股票和价格，再精确删除并回读，不得批量清空。

### 6. 回读验收

```bash
HOME=.runtime/futu_home .venv/bin/python \
  .agents/skills/stock-drawdown-alerts/scripts/verify_reminders.py \
  --applied <applied.json> --output <readback.json>
```

只有目标数量、价格、备注全部回读一致，才能写“已完成富途核验”。

## 输出格式

结论先行，保持紧凑：

```markdown
结论：主概率X%，次概率Y%；若得分接近则写“X%—Y%并列核心区”。

数据状态：OpenD、最后完成K线、样本数、ATR14/ATR%。

| 股票 | 当前锚点 | 主/并列节点 | 次节点 | 前低失效 |
|---|---|---:|---:|---:|

动作说明：到达只观察；收盘/盘中确认规则；失效后的风控。
上涨目标：C上方的修复阶梯；C已确认且突破B时，再列ABC扩展。
边界：ZigZag回看偏差、样本不足、同业映射和复权口径。
```

若已写富途，追加：写入数量、回读数量、提醒频率以及应用/回读文件路径。

## 验收

修改计算逻辑后运行：

```bash
HOME=.runtime/futu_home .venv/bin/python \
  .agents/skills/stock-drawdown-alerts/tests/test_model.py

HOME=.runtime/futu_home .venv/bin/python \
  /Users/lingliang/.codex/anthropic-skills/skills/skill-creator/scripts/quick_validate.py \
  .agents/skills/stock-drawdown-alerts
```

必须验证：标准比例不含71.8%、100%不参与支撑排名、并列阈值、节点公式、活动新高标记、概率排序备注和提醒备注长度。
