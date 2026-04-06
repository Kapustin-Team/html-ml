from html_ml.agents.baseline import BaselineFlatBetAgent
from html_ml.collector.hltv import HLTVLiveCollector
from html_ml.collector.polymarket import PolymarketCollector
from html_ml.models.domain import AggressionProfile


def test_baseline_returns_hold_or_bet() -> None:
    agent = BaselineFlatBetAgent()
    match_state = HLTVLiveCollector().collect_once_stub()[0]
    odds = PolymarketCollector().collect_once_stub()[0]
    decision = agent.decide(match_state, odds, AggressionProfile.AGGRESSIVE)
    assert decision.action in {'hold', 'bet'}
    assert decision.stake_usd >= 0
    assert 0 <= decision.confidence <= 1


def test_baseline_balanced_default_holds_for_stub() -> None:
    agent = BaselineFlatBetAgent()
    match_state = HLTVLiveCollector().collect_once_stub()[0]
    odds = PolymarketCollector().collect_once_stub()[0]
    decision = agent.decide(match_state, odds, AggressionProfile.BALANCED)
    assert decision.action == 'hold'
    assert decision.stake_usd == 0
