from html_ml.collector.polymarket import PolymarketCollector
from html_ml.models.domain import MarketType


def test_build_watch_match_accepts_real_match_question_without_counter_strike_prefix() -> None:
    collector = PolymarketCollector()
    event = {
        'id': '1',
        'title': '',
        'slug': 'astralis-vs-the-mongolz',
        'markets': [
            {
                'question': 'Astralis vs The MongolZ - who wins?',
                'outcomes': '["Astralis", "The MongolZ"]',
                'outcomePrices': '["0.48", "0.52"]',
            }
        ],
    }

    match = collector.build_watch_match(event)
    assert match is not None
    assert match.title == 'Astralis vs The MongolZ - who wins?'
    assert match.match_market is not None
    assert match.match_market.question == 'Astralis vs The MongolZ - who wins?'


def test_collect_cs2_market_snapshots_uses_watch_matches_with_real_questions() -> None:
    collector = PolymarketCollector()

    collector.list_watch_matches = lambda max_pages=5, only_future=False: [  # type: ignore[assignment]
        collector.build_watch_match(
            {
                'id': '2',
                'title': 'Astralis vs The MongolZ',
                'slug': 'astralis-vs-the-mongolz',
                'markets': [
                    {
                        'question': 'Astralis vs The MongolZ - who wins?',
                        'outcomes': '["Astralis", "The MongolZ"]',
                        'outcomePrices': '["0.48", "0.52"]',
                    }
                ],
            }
        )
    ]

    snapshots = collector.collect_cs2_market_snapshots(max_pages=1)
    assert len(snapshots) == 2
    assert all(snapshot.market_type == MarketType.MATCH_WINNER for snapshot in snapshots)
    assert snapshots[0].question == 'Astralis vs The MongolZ - who wins?'
