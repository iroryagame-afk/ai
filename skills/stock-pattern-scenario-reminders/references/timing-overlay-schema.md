# 技术形态与择时 Skill 的统一交接层

`timing_overlay` 解决一个常见误区：形态成立只说明结构证据较强，不等于当前可买。技术图形 Skill 先输出跨市场共通判断，再由对应择时 Skill 补齐交易机制。

## 共通字段

```json
{
  "timing_overlay": {
    "market": "US",
    "source_skill": "stock-position-timing",
    "data_status": "VERIFIED_FUTU_OPEND",
    "trend_state": "healthy",
    "heat_state": "normal",
    "market_gate": "neutral",
    "signal_state": "pending_close",
    "position_state": "flat",
    "decision": "wait_confirmation",
    "summary": "候选突破，等收盘确认",
    "confirmation": {
      "required": ["收盘站上139", "回踩136–139守住"],
      "met": []
    },
    "execution": {}
  }
}
```

枚举：

- `market`: `A_SHARE / US / HK`
- `trend_state`: `healthy / repair / overheated / broken / unknown`
- `heat_state`: `normal / warm / overheated / unknown`
- `market_gate`: `offense / neutral / defense / not_applicable / unknown`
- `signal_state`: `alert / pending_close / confirmed / failed`
- `position_state`: `flat / existing_sellable / new_today_locked / mixed / unknown`
- `decision`: `wait_confirmation / observe / candidate / execute_small / hold / reduce / avoid`

共通漏斗按这个顺序判断：

1. 数据是否已核验。
2. EMA20/55/200 与主支撑是否仍然存活。
3. ATR%、20日涨幅、EMA20/200偏离是否过热。
4. 宽基与风格/行业基准是否允许进攻。
5. 观察区是否获得完成K线、量价或回踩确认。
6. 用户是无仓、可卖昨仓、今日锁定新仓还是混合仓。
7. 最后才交给市场专属执行规则。

## A股执行字段

```json
{
  "market": "A_SHARE",
  "source_skill": "a-stock-position-timing",
  "signal_state": "confirmed",
  "decision": "candidate",
  "summary": "T日确认，列入T+1观察",
  "execution": {
    "signal_date": "2026-07-16",
    "earliest_entry_date": "2026-07-17",
    "earliest_sell_date_if_filled": "2026-07-20",
    "same_day_exit_allowed": false,
    "t1_scenarios": {
      "flat_or_small_gap": "承接成立才观察仓",
      "large_gap_up": "不追，等回踩",
      "large_gap_down": "跌破风险线取消"
    },
    "tradability_checks": ["停牌", "涨跌停", "一字板", "证券属性", "公告风险"]
  }
}
```

A股边界：

- `T日收盘确认` 只能生成 `T+1 candidate`，不能假设按 T 日收盘成交。
- 新买普通 A 股 `same_day_exit_allowed` 必须为 `false`。
- 必须写平开/小跳空、高开、低开三种执行分支。
- 涨跌停、停牌、集合竞价、跳空与可卖数量仍由 `a-stock-position-timing` 负责。

## 美股/港股执行字段

```json
{
  "market": "US",
  "source_skill": "stock-position-timing",
  "signal_state": "confirmed",
  "decision": "execute_small",
  "summary": "09:45后放量站稳，可小仓",
  "execution": {
    "session": "regular_confirmed",
    "same_day_exit_allowed": true,
    "intraday_trigger": "站上首15分钟高点并守住VWAP",
    "intraday_stop": "跌破VWAP或首15分钟低点",
    "abandon_condition": "QQQ跌破VWAP且无法收复"
  }
}
```

美股/港股边界：

- 美股盘前与开盘前15分钟只能是候选；不能写 `execute_small`。
- 美股新开仓需检查 QQQ/SPY；`market_gate=defense` 时最多 `observe`。
- VWAP、开盘区间、盘前高点和同日退出只属于盘中执行，不反向修改日线形态名称。
- 港股不能套用 QQQ/SPY；使用匹配的港股宽基/行业基准，具体规则仍由择时 Skill 判断。

## 不合并的内容

- A股交易所机制、费用、涨跌停、停牌和 T+1 回测。
- 美股盘前/盘后、VWAP、首15分钟和同日止损回测。
- 两个择时 Skill 的手机竖图模板、完整算法清单和历史绩效门槛。

这些内容更新频率和市场规则不同，复制进技术图形 Skill 会产生漂移；技术图形 Skill 只保存交接结果及来源 Skill。
