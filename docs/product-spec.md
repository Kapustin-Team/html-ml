# Product spec — html-ml v1

## Goal
Build a CS2 betting research environment where multiple agent/policy types can be benchmarked on real live data in paper mode.

## Data sources
- **Live match state:** HLTV live pages via browser automation with an always-open tab.
- **Odds source:** Polymarket.

## v1 market scope
- Match winner
- Total maps
- Map handicap
- Winner on a specific map

## Decision flexibility
The agent may later support:
- initial entry,
- averaging in (ladder / scale-in),
- selling / reducing exposure,
- chase / recovery logic,
- hold / no-bet.

## v1 execution mode
- Paper betting only.
- Real-world live data, no real money execution.

## Policy families to benchmark
1. LLM policies through OpenRouter
2. Classical ML policies
3. Hybrid policies later

## Risk baseline for first experiments
- Starting bankroll: **$3000**
- Flat stake: **$100**
- Alternative stop-loss and bankroll strategies will be benchmarked later.

## Storage
- Start local: SQLite or PostgreSQL
- Prefer a DB layer that can switch to PostgreSQL without major refactor.

## UI
- Initial interface can be CLI-first.
- Web UI is optional after the ingestion/simulation loop works.

## v1 success criteria
1. Collector can continuously capture live CS2 match state from HLTV.
2. Odds snapshots from Polymarket are stored over time.
3. A normalized DB state exists for replay/backtesting.
4. At least one baseline policy and one LLM policy can emit paper decisions.
5. PnL and basic risk metrics can be computed from stored runs.
