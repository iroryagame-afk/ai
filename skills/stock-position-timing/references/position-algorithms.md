# Position Algorithms

This reference lists the user's recurring stock-position algorithms beyond `乖离率` and `ATR`.

## Priority Order

1. Final score and S setup
2. S setup validity
3. Contrarian / mistaken-selloff repair
4. Stage-two health
5. Dynamic RS
6. Technical structure score
7. Chase-risk / overheat
8. News-risk veto

## Algorithms

| Algorithm | What It Judges | Buy/Watch Signal | Reduce/Avoid Signal |
|---|---|---|---|
| S setup / S shape | Whether the stock matches the user's high-priority setup document | Only mark S when the specified setup conditions are met | Do not mark ordinary strength, rebound, or news-driven move as S |
| EMA5/10/20/55/200 structure | Current trend, support, and invalidation | EMA10 shallow pullback, EMA20 normal pullback, EMA55 second-entry support | Breaks EMA55 and cannot reclaim; loses main support |
| EMA200 stage temperature | Trend stage and overheating | 0-10% start; 10-30% advancing; pullbacks can be considered | 30-50% hot, 50-70% late, 70-100% severe deviation, above 100% no chase |
| Stage-two model | Whether the stock is in a healthy advancing stage | EMA200 slope positive, EMA20 above EMA55, price not excessively extended | EMA55 breakdown, severe EMA200 distance, stage-end warning |
| A6 strength vote | Short/mid-term momentum confirmation | MTM, LWR, RSI, KDJ, MACD votes mostly positive | A6 weak: do not chase; momentum turns down |
| Dynamic RS | Relative strength inside the verified pool | 120/60/20-day returns weighted 50%/30%/20% and ranked high | RS falls behind peers; use only for same-score ordering |
| 20-day gain band | Whether the move is chaseable | Under 10% is more buyable; 10-15% needs caution and pullback | 15-25% high zone; above 25% overheating in strict equipment-style framing |
| Volume-price N shape | Ice-god low-risk continuation setup | Explosive bullish candle -> low-volume pullback -> second volume confirmation; buy near lower half of first candle range | Breaks the explosive bullish candle bottom; high-volume bearish candle; continuous volume-down decline |
| Box / cup-handle / double-bottom / central-zone breakout | Whether a pattern has confirmed | Breakout above neckline/box high with volume, or successful retest | Falls back below neckline/box high; failed breakout |
| Gap pullback | Whether event gap has support | Gap with volume, then pullback to gap zone without filling/breaking it | Breaks below gap lower edge with volume |
| Momentum heat / divergence | Whether indicators support or warn | MACD/KDJ/RSI improve after support hold or breakout | High-position divergence, KDJ overheated, MACD weakens after failed high |
| Contrarian / mistaken-selloff repair | Whether panic selling created a recoverable point | Extreme fall, cold sentiment, key average reclaimed, volume confirms, thesis intact | Industrial thesis broken or rebound lacks volume and cannot reclaim support |
| Market-regime gate | Whether index environment allows offense | Broad market holds support or is neutral/strong; position can be normal | Defensive market: reduce size, avoid non-key support buys and high chase |
| News-risk veto | Whether information flow invalidates the technical setup | News is only confirmation; favorable news cannot replace chart | Regulatory inquiry, reduction/unlock, bad guidance, earnings miss, clarification failure |

## Interpretation Rules

- For new buys, require at least one of: support pullback confirmation, N-shape half-range support, breakout retest success, or S setup validity.
- For existing positions, do not sell strong-trend core names mechanically because 20EMA deviation is high; first check EMA5/10 discipline and volume.
- For high-beta themes, position size must shrink as ATR%, 20-day gain, and market defense pressure rise.
- For A-share page or mda100 tasks, keep the model within A shares and do not mix in US/HK names except as temporary external clues.
- Always separate chart timing from industry thesis. A strong theme can still be `暂不追`; a weak theme should not become `买入` just because the chart bounces.

## Screening Instead Of Full Checklist

Use the algorithm list as a menu, not a mandatory checklist.

| Scenario | Use These | Usually Skip |
|---|---|---|
| Quick buy/sell position | EMA structure, support/resistance, ATR or deviation, volume | Full S validation, long RS ranking, deep news unless asked |
| Strong trend holding | EMA5/10 discipline, 5EMA/20EMA deviation, A6, volume | N-shape bottom hunt, contrarian repair |
| Pullback entry | EMA20/55, ATR pullback, volume contraction, N-shape half-range | Breakout-only rules unless price is near breakout retest |
| Breakout entry | Box/cup/double-bottom neckline, volume ratio, failed-breakout line | Contrarian repair, EMA55 second-entry unless breakout fails |
| High chase risk | 20-day gain band, EMA200 stage temperature, ATR%, momentum heat | Low-absorption buy logic |
| Broken trend | EMA55/primary support loss, reclaim test, news veto | S setup hunting and bullish target extrapolation |
| Panic repair | Extreme fall, thesis intact, support reclaim, volume confirmation | Ordinary trend-following add rules until repair confirms |

For final output, show only the active checks. Mention skipped checks only when skipping changes the conclusion.
