from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from html_ml.models.domain import LiveMatchState


class HLTVLiveCollector:
    """HLTV collector helpers.

    Current stage:
    - stub live snapshots remain for baseline agent/dev flow
    - real headed-browser probing/parsing can normalize match list entries

    Next stage:
    - persistent browser page
    - per-match live state parsing
    - DOM/network-driven updates
    """

    @staticmethod
    def normalize_format(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        lowered = value.strip().lower()
        if lowered in {'bo1', 'bo3', 'bo5'}:
            return lowered
        return lowered or None

    def match_entry_to_state(self, entry: dict, observed_at: Optional[datetime] = None) -> LiveMatchState:
        observed = observed_at or datetime.now(timezone.utc)
        team_a = str(entry.get('team1') or 'TBD')
        team_b = str(entry.get('team2') or 'TBD')
        title = f'{team_a} vs {team_b}'
        live_detail = entry.get('live_detail') or {}
        return LiveMatchState(
            source='hltv',
            external_match_id=str(entry.get('match_id') or entry.get('href') or title),
            match_title=title,
            team_a=team_a,
            team_b=team_b,
            event_name=entry.get('event_name'),
            format=self.normalize_format(entry.get('format')),
            current_map_name=live_detail.get('current_map_name'),
            map_index=live_detail.get('map_index'),
            score_team_a=live_detail.get('score_team_a') or 0,
            score_team_b=live_detail.get('score_team_b') or 0,
            maps_team_a=live_detail.get('maps_team_a') or 0,
            maps_team_b=live_detail.get('maps_team_b') or 0,
            team_a_side=live_detail.get('team_a_side'),
            team_b_side=live_detail.get('team_b_side'),
            raw_payload=entry,
            observed_at=observed,
        )

    def collect_once_stub(self) -> list[LiveMatchState]:
        now = datetime.now(timezone.utc)
        return [
            LiveMatchState(
                external_match_id='stub-match-1',
                match_title='Team Spirit vs NAVI',
                team_a='Team Spirit',
                team_b='NAVI',
                event_name='Stub Event',
                format='bo3',
                current_map_name='Mirage',
                map_index=1,
                score_team_a=8,
                score_team_b=6,
                maps_team_a=0,
                maps_team_b=0,
                team_a_side='CT',
                team_b_side='T',
                raw_payload={'stub': True},
                observed_at=now,
            )
        ]
