# Workbench observation feeds

Public route: `/a-share-workbench/` (unlisted, no login). Views: `#observe`, `#mobserve`, `#cl20`.

Run in a clean publication worktree based on `origin/main`:

```
python3 scripts/build_workbench_observation_feeds.py --source-root /Users/lingliang/Documents/Codex/股票分析
python3 -m unittest discover -s tests -p test_workbench_observation_feeds.py
```

A uses the validated latest run's ranked candidates; M uses identity-verified candidates, excluding unknown evidence and C-only distant entries. `in_futu` marks the final selected names; this exporter never changes broker groups. A pointer, target and independent readback must agree; M must report OpenD connected and successful final readback.

CL20 reads the official local service under `~/Library/Application Support/CodexCL20/outputs/cl20_watchlist_trial/`. Export only allowlisted research fields from actual outbox events. Preserve tentative labels, cancellation/revision, and acceptance status. Detection time is displayed in Beijing; pivot time remains exchange-local. Keep the most recent 300 records. Never export raw bodies, recipient IDs, account data or credentials. Never call scans or notification senders.

Every 15 minutes, compare to the published JSON. A scan timestamp alone is not a publication change. If unchanged, stop before browser/deploy. On a change, run the tests and normal CSNPK clean-worktree, single-browser visual QA, Git push/merge, one Cloudflare deployment and cache-busting public hash readback. Only observation-feeds.json changes during routine refreshes. Keep last verified published data on source failure; report the failure without replacing it with empty data. Existing A/M/CL20 source schedules remain untouched.

The page fetches the published snapshot every 60 seconds while visible. This does not initiate market scans. Site-wide trade-day-only refresh short-circuit is not used for this event-driven consumer.

QA: desktop and 390px mobile, search, all three views, privacy allowlist and lifecycle preservation. Existing cream palette is intentional; hidden local holding image has no src until user supplies one; table cells provide spacing inside table wrappers.
