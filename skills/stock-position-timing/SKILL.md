---
name: stock-position-timing
description: Judge stock current position and timing, including buy/sell timing, support/resistance, pullback zones, stop-loss/invalidation, and chase-risk using the user's local mda100/Futu OpenD/a-stock-data workflow. Use when the user says "择时", gives a stock code/name plus "择时", or asks about 买点, 卖点, 当前位置, K线结构, 支撑压力, 趋势阶段, 能不能追, 持有/加仓/减仓, or wants a concise trading-position diagnosis.
---

# Stock Position Timing

## Overview

Use this skill to turn one or more A-share codes into a concrete position diagnosis: current location, buy observation zone, add/reduce/hold discipline, stop-loss or invalidation line, and the algorithm votes behind the conclusion.

Default to Chinese output. Keep the answer operational and level-based: `能不能追`, `等哪里`, `破哪里失效`, `已有仓位怎么处理`.

## Required Context

Before judging positions in this workspace:

1. Read `MDA100_STATE.md` and `AGENTS.md` if the task relates to mda100, md50, holdings review, or A-share timing.
2. Use Futu OpenD for K-line, support/resistance, moving average, breakout/breakdown, and chart-shape questions.
3. Use the local `a-stock-data` skill at `/Users/lingliang/.workbuddy/skills/a-stock-data/SKILL.md` for A-share market data when available, following its source priority.
4. If Futu OpenD or local market data cannot be verified, say so explicitly and avoid pretending precise price levels are live-verified.

## Algorithm Catalog

For the user's standing algorithm list beyond `乖离率` and `ATR`, read `references/position-algorithms.md` when the task asks for methodology, model updates, or a complete vote breakdown.

The core stack is:

- S setup / S shape
- Key moving-average structure: EMA5/10/20/55/200 and reclaim/breakdown
- EMA200 stage temperature and stage-two model
- A6 strength vote: MTM, LWR, RSI, KDJ, MACD
- Dynamic RS: 120/60/20-day weighted relative strength inside the verified pool
- 20-day gain band / chase-risk backtest frame
- Ice-god volume-price layer: explosive bullish candle, low-volume pullback, N-shaped half-range buy point, volume-risk exits
- Box / cup-handle / double-bottom / central-zone breakout confirmation
- Gap pullback strategy
- Momentum heat and divergence: MACD/KDJ/RSI
- Contrarian oversold / mistaken-selloff repair
- Market-regime gate and news-risk veto

Use `乖离率` and `ATR` as risk-distance and action-zone tools, not as the only decision layer.

## Workflow

1. Normalize the input:
   - Confirm code, market, and name.
   - For A shares, use Shanghai/Shenzhen/Beijing code prefixes correctly.
   - If the user gives several names, analyze each with the same fields and rank the comfort of entry.

2. Verify data:
   - Pull at least 250 daily bars when possible.
   - Calculate latest close, percent change, volume ratio, EMA5/10/20/55/200, MA20/50/120 if already used locally, ATR14, recent high/low, and 20/60/120-day returns.
   - For intraday questions, add 30-minute or 60-minute structure only after daily trend is clear.

3. Run the screening funnel before selecting algorithms:
   - Gate 1: Data validity. If daily K-line, volume, or latest price cannot be verified, do not give precise buy/sell levels.
   - Gate 2: Trend survival. First check EMA20/55/200 and the primary support. If the stock is already broken below EMA55 and cannot reclaim, skip bullish setup hunting and classify as `破位观望/减仓`.
   - Gate 3: Position scenario. Choose only the relevant branch:
     - Trend continuation: use EMA5/10/20, A6, dynamic RS, and ATR/乖离 for holding discipline.
     - Pullback buy: use EMA20/55, ATR, volume contraction, and N-shape half-range.
     - Breakout buy: use box/cup/double-bottom/20-day-high breakout, volume confirmation, and failed-breakout risk.
     - Overheat/chase risk: use 20-day gain band, EMA deviation, ATR%, and momentum heat.
     - Panic repair: use contrarian repair only when industry thesis is intact and key average/support is reclaimed.
   - Gate 4: Veto. Apply market-regime and news-risk veto last; a veto can downgrade action but should not create a buy signal.

4. Classify the position:
   - `右侧强趋势可持有`: price holds EMA5/10 or shallow EMA10 pullback.
   - `常规回踩观察`: trend intact, near EMA20 or primary support, volume not expanding downward.
   - `中期二买观察`: near EMA55, higher opportunity but must hold EMA55.
   - `突破观察`: near 20-day high, box/cup/neckline breakout with volume confirmation.
   - `过热不追`: too far above key averages or 20-day gain band is high; wait for pullback.
   - `破位观望/减仓`: loses EMA55 or primary support and cannot reclaim.
   - `错杀修复观察`: extreme selloff, thesis intact, key average reclaimed with volume confirmation.

5. Build action levels:
   - Buy observation zone: nearest validated support, EMA10/20/55 zone, N-shape half-range zone, box breakout retest zone, or ATR pullback zone.
   - Add zone: only after support holds or breakout retest succeeds.
   - Reduce zone: overheat, failed breakout, high-volume bearish candle, or loss of short trend.
   - Stop/invalidation: key support, explosive bullish candle bottom, box upper edge after failed breakout, EMA55, or ATR risk line.

6. Apply vetoes:
   - Do not mark S without the specified setup source:
     `/Users/lingliang/Movies/codexob/codex/01RAW/Clippings/10192025真正的干货：实战中我最喜欢的setup 1.md`
   - Do not turn news alone into a buy recommendation.
   - News risk, earnings miss, regulatory inquiry, reduction/unlock, failed clarification, or broad-market defense mode can downgrade action even when the chart looks acceptable.
   - If data is not live-verified, label the result `未完成实时核验`.

## Algorithm Selection Rule

Do not run every algorithm on every stock. For a single-stock quick answer, normally use 3-5 active checks:

- Always use: data validity, EMA trend survival, support/resistance, and one action-zone tool such as ATR or 乖离率.
- Add only when relevant: S setup, N-shape volume-price, box/cup/double-bottom breakout, gap pullback, contrarian repair, or news veto.
- Keep unused algorithms out of the table unless the user asks for a full diagnostic.
- If algorithms conflict, prioritize the screening funnel over vote-counting. A broken trend is not rescued by a minor momentum vote; a strong theme is still `暂不追` when the entry is overheated.

## Output Format

For a quick single-code question, answer in this compact structure:

```markdown
结论：观察/可小仓/持有/减仓/暂不追。

当前位置：
- 趋势阶段：
- 买入观察区：
- 持仓纪律：
- 失效/止损：
- 上方压力：

算法投票：
| 算法 | 结论 | 含义 |
|---|---|---|

一句话：...
```

For a full stock consultation, append the user's house format:

- 200字左右总结
- 产业/主题定位
- 核心产品阶段
- 纯度、弹性、确定性、风险评级
- 龙一/龙二或相对排序
- 最终评级
- 6-12个月研究型目标价：保守/基准/乐观
- 明确写明：不构成投资建议

## Mobile Vertical Timing Card

When the user asks to turn a timing answer into a `手机竖图`, `竖图`, `长图`, `方便手机看`, or says a generated timing card is good and should be reused, create a mobile-first vertical PNG in addition to the text answer.

Use the reusable template:

`templates/mobile-timing-card.html`

Default card rules:

- Size: `1080 x 2600` PNG, portrait, readable on mobile.
- Output directory: `outputs/<ticker-lower>-timing-card/`.
- Required files: `index.html` and `<ticker-lower>-timing-card.png`.
- Visual style: dense technical modules, light grid background, black linework, teal data blocks, yellow highlights for key price zones, pink only for warnings/overheat/risk.
- Required modules: title/price, conclusion, current position, buy observation zones, risk/invalidation, resistance/upside, algorithm votes, action path, 6-12 month research target range, data-source disclaimer.
- Keep the operational levels prominent: `等哪里`, `破哪里失效`, `已有仓位怎么处理`, `目标价三档`.
- Do not let footer/disclaimer overlap target-price modules. Verify the PNG visually after rendering.
- Prefer rendering HTML to PNG with local Chrome/Playwright so Chinese text stays crisp. If browser rendering is unavailable, keep the HTML file and clearly say PNG was not produced.
- If the market data is not live-verified, print that status both in the card footer and the final response.

For the module content, preserve the timing diagnosis exactly. Do not invent new price levels just to fill the card.

## Style

Prefer concise operational language over textbook explanations. When the answer involves current price levels, include the date/time or data source status. When several algorithms disagree, state which layer has priority: S setup and key chart structure first, then contrarian repair, stage health, RS, technical score, chase risk, and news veto.
