# US Watchlist Timing

Futu OpenD based US watchlist timing scan.

- Data source: Futu OpenD `request_history_kline`, US regular-session daily bars.
- Benchmark gate: QQQ and SPY.
- Output files:
  - `latest_us_watchlist_timing.json`
  - `latest_us_watchlist_timing.csv`

Run from the stock-analysis workspace:

```bash
./.venv/bin/python scripts/scan_futu_us_watchlist_timing.py --group Favorites --sleep 0.6
./.venv/bin/python scripts/scan_futu_us_watchlist_timing.py --group US --sleep 0.6
```

This is a research/timing screen, not investment advice.
