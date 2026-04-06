# Data model draft

## Core entities

### live_match_snapshots
Time-series snapshots of the current observed HLTV match state.

Fields:
- source
- external_match_id
- match_title
- team_a / team_b
- event_name
- format
- current_map_name
- map_index
- score_team_a / score_team_b
- maps_team_a / maps_team_b
- team_a_side / team_b_side
- raw_payload
- observed_at

### odds_snapshots
Time-series Polymarket snapshots.

Fields:
- source
- market_id
- question
- market_type
- selection
- price
- implied_probability
- raw_payload
- observed_at

### agent_decisions
Paper decisions emitted by a policy.

Fields:
- agent_name
- model_name
- aggression
- market_type
- selection
- action
- stake_usd
- confidence
- rationale
- observed_at

## Next likely entities
- matches
- maps
- rounds
- player_snapshots
- bankroll_runs
- positions
- fills
- experiment_runs
- backtest_results
