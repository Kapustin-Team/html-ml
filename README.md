# html-ml

Research environment for CS2 betting agents:
- live HLTV ingestion
- historical/live state storage
- simulation environment for betting policies
- experiments with different risk/aggression profiles
- dashboards and evaluation

## Planned modules

### apps
- `apps/api` — API for features, odds snapshots, match state, agent decisions
- `apps/worker` — background jobs: collectors, parsers, feature builders
- `apps/dashboard` — UI for live stats, experiments, and backtests

### packages
- `packages/collector` — HLTV/live page collectors
- `packages/db` — DB schema + access layer
- `packages/core` — shared domain models
- `packages/simulator` — betting environment and reward functions
- `packages/agents` — policy wrappers for different models and aggression profiles

### docs
- architecture, data contracts, reward design, roadmap

## Core idea

The system should allow us to:
1. ingest live and historical CS2 match signals,
2. build a market/game state representation,
3. ask different models to place bets with configurable aggression,
4. evaluate profit/risk over time,
5. iterate towards better betting policies.
