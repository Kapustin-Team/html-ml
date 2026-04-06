from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class MarketType(str, Enum):
    MATCH_WINNER = 'match_winner'
    MAP_TOTALS = 'map_totals'
    MAP_HANDICAP = 'map_handicap'
    MAP_WINNER = 'map_winner'


class Side(str, Enum):
    TEAM_A = 'team_a'
    TEAM_B = 'team_b'
    OVER = 'over'
    UNDER = 'under'


class AggressionProfile(str, Enum):
    CONSERVATIVE = 'conservative'
    BALANCED = 'balanced'
    AGGRESSIVE = 'aggressive'


class LiveMatchState(BaseModel):
    source: str = 'hltv'
    external_match_id: str
    match_title: str
    team_a: str
    team_b: str
    event_name: Optional[str] = None
    format: Optional[str] = None
    current_map_name: Optional[str] = None
    map_index: Optional[int] = None
    score_team_a: int = 0
    score_team_b: int = 0
    maps_team_a: int = 0
    maps_team_b: int = 0
    team_a_side: Optional[str] = None
    team_b_side: Optional[str] = None
    raw_payload: dict = Field(default_factory=dict)
    observed_at: datetime


class OddsSnapshot(BaseModel):
    source: str = 'polymarket'
    market_id: str
    question: str
    market_type: MarketType
    selection: str
    price: float
    implied_probability: float
    observed_at: datetime
    raw_payload: dict = Field(default_factory=dict)


class AgentDecision(BaseModel):
    agent_name: str
    model_name: str
    aggression: AggressionProfile
    market_type: MarketType
    selection: str
    action: str
    stake_usd: float = 0.0
    confidence: float = 0.0
    rationale: Optional[str] = None
    observed_at: datetime
