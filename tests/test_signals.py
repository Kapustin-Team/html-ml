from datetime import datetime, timezone

from html_ml.signals import LinkedMarketView, build_candidate_bets


NOW = datetime.now(timezone.utc)


def test_build_candidate_bets_prefers_shortening_side_in_tight_market() -> None:
    rows = [
        LinkedMarketView(
            hltv_match_id='2393022',
            match_title='NRG vs EYEBALLERS',
            event_name='PGL Bucharest 2026',
            format='bo3',
            live=True,
            time_text='LIVE',
            polymarket_market_id='pm-1',
            polymarket_question='Counter-Strike: NRG vs EYEBALLERS (BO3) - PGL Bucharest Group Stage',
            link_score=0.8,
            matched_by='team-order-fuzzy',
            team_a='NRG',
            team_b='EYEBALLERS',
            team_a_price=0.48,
            team_b_price=0.52,
            team_a_prev_price=0.51,
            team_b_prev_price=0.49,
            observed_at=NOW,
        )
    ]

    bets = build_candidate_bets(rows)
    assert len(bets) == 1
    assert bets[0].selection == 'NRG'
    assert bets[0].edge_score > 0.6


def test_build_candidate_bets_skips_wide_market() -> None:
    rows = [
        LinkedMarketView(
            hltv_match_id='2393025',
            match_title='PARIVISION vs FUT',
            event_name='PGL Bucharest 2026',
            format='bo3',
            live=False,
            time_text='21:30',
            polymarket_market_id='pm-2',
            polymarket_question='Counter-Strike: PARIVISION vs FUT Esports (BO3) - PGL Bucharest Group Stage',
            link_score=0.8,
            matched_by='team-order-fuzzy',
            team_a='PARIVISION',
            team_b='FUT',
            team_a_price=0.30,
            team_b_price=0.70,
            team_a_prev_price=0.31,
            team_b_prev_price=0.69,
            observed_at=NOW,
        )
    ]

    bets = build_candidate_bets(rows)
    assert bets == []
