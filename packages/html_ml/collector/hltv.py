from __future__ import annotations

from datetime import datetime, timezone

from html_ml.models.domain import LiveMatchState


class HLTVLiveCollector:
    """Skeleton collector.

    Real implementation will keep a Playwright page open, observe DOM/network
    updates, normalize them into LiveMatchState snapshots, and persist them.
    """

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
