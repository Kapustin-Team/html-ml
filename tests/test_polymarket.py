from html_ml.collector.polymarket import PolymarketCollector
from html_ml.models.domain import MarketType


def test_classify_match_winner_market() -> None:
    collector = PolymarketCollector()
    assert collector.classify_market_type('Will Team Spirit beat NAVI?') == MarketType.MATCH_WINNER


def test_classify_map_winner_market() -> None:
    collector = PolymarketCollector()
    assert collector.classify_market_type('Counter-Strike: Team A vs Team B - Map 1 Winner') == MarketType.MAP_WINNER


def test_classify_map_handicap_market() -> None:
    collector = PolymarketCollector()
    assert collector.classify_market_type('Counter-Strike: Team A vs Team B - Map Handicap') == MarketType.MAP_HANDICAP


def test_parse_jsonish_list() -> None:
    collector = PolymarketCollector()
    assert collector._parse_jsonish_list('["Yes", "No"]') == ['Yes', 'No']


def test_normalize_binary_market() -> None:
    collector = PolymarketCollector()
    market = {
        'id': '123',
        'question': 'Will Team Spirit beat NAVI?',
        'outcomes': '["Yes", "No"]',
        'outcomePrices': '["0.42", "0.58"]',
    }
    snapshots = collector.normalize_market(market)
    assert len(snapshots) == 2
    assert snapshots[0].market_id == '123'
    assert snapshots[0].market_type == MarketType.MATCH_WINNER
    assert snapshots[0].selection == 'Yes'
    assert snapshots[0].price == 0.42
