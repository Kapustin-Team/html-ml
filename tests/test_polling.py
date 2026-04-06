from html_ml.collector.polymarket import PolymarketCollector
from html_ml.models.domain import MarketType


def test_collect_watchlist_snapshots_builds_supported_market_types() -> None:
    collector = PolymarketCollector()

    class StubCollector(PolymarketCollector):
        def top_watch_matches(self, limit: int = 10, max_pages: int = 5, only_future: bool = True):  # type: ignore[override]
            return [
                collector.build_watch_match(
                    {
                        'id': 'evt-1',
                        'slug': 'evt-1',
                        'title': 'Counter-Strike: Team A vs Team B (BO3) - Test',
                        'startDate': '2026-04-06T10:00:00Z',
                        'endDate': '2026-04-06T14:00:00Z',
                        'markets': [
                            {
                                'question': 'Counter-Strike: Team A vs Team B (BO3) - Test',
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
                )
            ]

    stub = StubCollector()
    snapshots = stub.collect_watchlist_snapshots(limit=1, max_pages=1)

    assert len(snapshots) == 6
    assert {snapshot.market_type for snapshot in snapshots} == {
        MarketType.MATCH_WINNER,
        MarketType.MAP_TOTALS,
        MarketType.MAP_HANDICAP,
    }
    assert snapshots[0].raw_payload['event_id'] == 'evt-1'
