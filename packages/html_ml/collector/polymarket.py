from __future__ import annotations

from datetime import datetime, timezone

from html_ml.models.domain import MarketType, OddsSnapshot


class PolymarketCollector:
    """Skeleton collector for odds snapshots.

    Real implementation will fetch/filter relevant CS2 markets and persist
    normalized odds snapshots.
    """

    def collect_once_stub(self) -> list[OddsSnapshot]:
        now = datetime.now(timezone.utc)
        return [
            OddsSnapshot(
                market_id='stub-market-1',
                question='Will Team Spirit beat NAVI?',
                market_type=MarketType.MATCH_WINNER,
                selection='Team Spirit',
                price=0.57,
                implied_probability=0.57,
                observed_at=now,
                raw_payload={'stub': True},
            )
        ]
