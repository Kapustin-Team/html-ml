# Architecture draft

## Streams
1. Live collector opens HLTV/live pages and continuously extracts updates.
2. Collector writes normalized events/snapshots into DB.
3. Feature builder converts raw events into betting state.
4. Agent runner queries current state and asks models for an action.
5. Simulator / evaluator scores the action based on reward rules.

## Initial bounded scope
- Start with CS2 only.
- Start with one data source (HLTV) plus optional bookmaker feed later.
- Start with paper betting first, not real money execution.

## Initial action space
- no_bet
- bet_team_a
- bet_team_b
- optional: bet_over / bet_under / map winner later

## Initial aggression profiles
- conservative
- balanced
- aggressive
- all-in-research (sandbox only)

## Primary metrics
- ROI
- drawdown
- win rate
- calibration
- expected value estimate quality
- Sharpe-like risk-adjusted metric
