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

## Current status

Initial Python skeleton is in place for:
- config + environment management
- SQLAlchemy DB schema
- HLTV collector stub
- Polymarket collector stub
- baseline flat-bet agent stub
- CLI commands for init / collect / run

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
html-ml initdb
html-ml research-polymarket --limit-pages 2
html-ml collect-polymarket --max-pages 2
html-ml collect-stub
html-ml run-baseline --aggression aggressive
```

## Next implementation steps

1. Real Playwright-based HLTV live collector
2. Matching HLTV live games to Polymarket markets
3. Paper position engine with buy / scale-in / reduce / close
4. OpenRouter policy adapter + ML baselines
5. Replay/backtest runner over stored snapshots
