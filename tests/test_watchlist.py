from datetime import datetime, timezone

from html_ml.collector.polymarket import PolymarketCollector


def test_build_watch_match_extracts_key_markets() -> None:
    collector = PolymarketCollector()
    event = {
        'id': 'evt-1',
        'slug': 'test-match',
        'title': 'Counter-Strike: Team A vs Team B (BO3) - Test Event',
        'startDate': '2026-04-06T10:00:00Z',
        'endDate': '2026-04-06T14:00:00Z',
        'markets': [
            {
                'question': 'Counter-Strike: Team A vs Team B (BO3) - Test Event',
                'outcomes': '["Team A", "Team B"]',
                'outcomePrices': '["0.55", "0.45"]',
            },
            {
                'question': 'Games Total: O/U 2.5',
                'outcomes': '["Over", "Under"]',
                'outcomePrices': '["0.52", "0.48"]',
            },
            {
                'question': 'Map Handicap: Team A (-1.5) vs Team B (+1.5)',
                'outcomes': '["Team A", "Team B"]',
                'outcomePrices': '["0.4", "0.6"]',
            },
        ],
    }

    watch_match = collector.build_watch_match(event)

    assert watch_match is not None
    assert watch_match.event_id == 'evt-1'
    assert watch_match.match_market is not None
    assert watch_match.total_market is not None
    assert watch_match.handicap_market is not None
    assert watch_match.match_market.prices == [0.55, 0.45]
    assert watch_match.total_market.outcomes == ['Over', 'Under']
    assert watch_match.end_at == datetime(2026, 4, 6, 14, 0, tzinfo=timezone.utc)


def test_watch_match_score_rewards_balanced_markets() -> None:
    collector = PolymarketCollector()
    balanced_event = {
        'id': 'evt-balanced',
        'title': 'Counter-Strike: Team A vs Team B (BO3) - Balanced',
        'markets': [
            {
                'question': 'Counter-Strike: Team A vs Team B (BO3) - Balanced',
                'outcomes': '["Team A", "Team B"]',
                'outcomePrices': '["0.51", "0.49"]',
            },
            {
                'question': 'Games Total: O/U 2.5',
                'outcomes': '["Over", "Under"]',
                'outcomePrices': '["0.5", "0.5"]',
            },
        ],
    }
    lopsided_event = {
        'id': 'evt-lopsided',
        'title': 'Counter-Strike: Team C vs Team D (BO3) - Lopsided',
        'markets': [
            {
                'question': 'Counter-Strike: Team C vs Team D (BO3) - Lopsided',
                'outcomes': '["Team C", "Team D"]',
                'outcomePrices': '["0.95", "0.05"]',
            },
            {
                'question': 'Games Total: O/U 2.5',
                'outcomes': '["Over", "Under"]',
                'outcomePrices': '["0.9", "0.1"]',
            },
        ],
    }

    balanced = collector.build_watch_match(balanced_event)
    lopsided = collector.build_watch_match(lopsided_event)

    assert balanced is not None
    assert lopsided is not None
    assert balanced.score > lopsided.score
