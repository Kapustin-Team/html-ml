from __future__ import annotations

from datetime import datetime, timezone

from html_ml.config import settings
from html_ml.models.domain import AgentDecision, AggressionProfile, LiveMatchState, MarketType, OddsSnapshot


class BaselineFlatBetAgent:
    def __init__(self, agent_name: str = 'baseline-flat', model_name: str = 'rules-v1') -> None:
        self.agent_name = agent_name
        self.model_name = model_name

    def decide(
        self,
        match_state: LiveMatchState,
        odds: OddsSnapshot,
        aggression: AggressionProfile = AggressionProfile.BALANCED,
    ) -> AgentDecision:
        action = 'hold'
        stake = 0.0
        confidence = 0.5
        rationale = 'No edge model yet; baseline skeleton keeps hold by default.'

        if odds.implied_probability < 0.5 and aggression == AggressionProfile.AGGRESSIVE:
            action = 'bet'
            stake = settings.flat_bet_usd
            confidence = 0.55
            rationale = 'Stub aggressive rule: take slight underdog at flat stake.'

        return AgentDecision(
            agent_name=self.agent_name,
            model_name=self.model_name,
            aggression=aggression,
            market_type=MarketType.MATCH_WINNER,
            selection=odds.selection,
            action=action,
            stake_usd=stake,
            confidence=confidence,
            rationale=rationale,
            observed_at=datetime.now(timezone.utc),
        )
