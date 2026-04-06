from datetime import datetime, timezone

from html_ml.db.repository import save_odds_snapshot
from html_ml.db.schema import OddsSnapshotORM, SessionLocal, init_db
from html_ml.models.domain import MarketType, OddsSnapshot


def test_previous_price_pairs_can_be_read_from_db() -> None:
    init_db()

    with SessionLocal() as db:
        db.query(OddsSnapshotORM).delete()
        db.commit()

        save_odds_snapshot(
            db,
            OddsSnapshot(
                market_id='m1',
                question='Counter-Strike: Team A vs Team B',
                market_type=MarketType.MATCH_WINNER,
                selection='Team A',
                price=0.40,
                implied_probability=0.40,
                observed_at=datetime(2026, 4, 6, 10, 0, tzinfo=timezone.utc),
                raw_payload={},
            ),
        )
        save_odds_snapshot(
            db,
            OddsSnapshot(
                market_id='m1',
                question='Counter-Strike: Team A vs Team B',
                market_type=MarketType.MATCH_WINNER,
                selection='Team A',
                price=0.55,
                implied_probability=0.55,
                observed_at=datetime(2026, 4, 6, 10, 5, tzinfo=timezone.utc),
                raw_payload={},
            ),
        )

    from html_ml.cli import _latest_previous_prices

    previous = _latest_previous_prices()

    assert ('m1', 'Team A') in previous
    assert previous[('m1', 'Team A')][0] == 0.40
