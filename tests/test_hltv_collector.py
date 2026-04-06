from html_ml.collector.hltv import HLTVLiveCollector


def test_match_entry_to_state_normalizes_basic_fields() -> None:
    collector = HLTVLiveCollector()
    state = collector.match_entry_to_state(
        {
            'match_id': '12345',
            'team1': 'Astralis',
            'team2': 'TheMongolz',
            'event_name': 'PGL Bucharest 2026',
            'format': 'BO3',
            'time_text': '21:30',
        }
    )

    assert state.external_match_id == '12345'
    assert state.match_title == 'Astralis vs TheMongolz'
    assert state.team_a == 'Astralis'
    assert state.team_b == 'TheMongolz'
    assert state.event_name == 'PGL Bucharest 2026'
    assert state.format == 'bo3'
    assert state.raw_payload['time_text'] == '21:30'
