from datetime import datetime, timezone

from html_ml.linker import HltvMatchRow, PolymarketRow, link_hltv_to_polymarket


NOW = datetime.now(timezone.utc)


def test_linker_matches_question_with_same_team_order() -> None:
    links = link_hltv_to_polymarket(
        [
            HltvMatchRow(
                match_id='2393023',
                match_title='Astralis vs The MongolZ',
                team_a='Astralis',
                team_b='The MongolZ',
                event_name='PGL Bucharest 2026',
                observed_at=NOW,
            )
        ],
        [
            PolymarketRow(
                market_id='pm-1',
                question='Astralis vs The MongolZ - who wins?',
                market_type='match_winner',
                observed_at=NOW,
            )
        ],
    )

    assert len(links) == 1
    assert links[0].polymarket_market_id == 'pm-1'
    assert links[0].score >= 0.9


def test_linker_matches_when_team_order_is_swapped() -> None:
    links = link_hltv_to_polymarket(
        [
            HltvMatchRow(
                match_id='2393022',
                match_title='NRG vs EYEBALLERS',
                team_a='NRG',
                team_b='EYEBALLERS',
                event_name='PGL Bucharest 2026',
                observed_at=NOW,
            )
        ],
        [
            PolymarketRow(
                market_id='pm-2',
                question='Will EYEBALLERS beat NRG?',
                market_type='match_winner',
                observed_at=NOW,
            )
        ],
        min_score=0.5,
    )

    assert len(links) == 1
    assert links[0].polymarket_market_id == 'pm-2'


def test_linker_ignores_non_match_winner_markets() -> None:
    links = link_hltv_to_polymarket(
        [
            HltvMatchRow(
                match_id='2393025',
                match_title='PARIVISION vs FUT',
                team_a='PARIVISION',
                team_b='FUT',
                event_name='PGL Bucharest 2026',
                observed_at=NOW,
            )
        ],
        [
            PolymarketRow(
                market_id='pm-3',
                question='PARIVISION vs FUT total maps over 2.5?',
                market_type='map_totals',
                observed_at=NOW,
            )
        ],
    )

    assert links == []
