from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

import httpx

from html_ml.config import settings
from html_ml.models.domain import MarketType, OddsSnapshot

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'Accept': 'application/json,text/plain,*/*',
    'Origin': 'https://polymarket.com',
    'Referer': 'https://polymarket.com/',
}

CS2_TAG_ID = 100780


class PolymarketCollector:
    """Public Gamma API collector.

    v1 goals:
    - discover active CS2-tagged events/markets
    - normalize binary markets into OddsSnapshot rows
    - support quick research on whether Polymarket actually exposes
      the desired CS2 live betting markets
    """

    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0) -> None:
        self.base_url = (base_url or settings.polymarket_base_url).rstrip('/')
        self.client = httpx.Client(headers=DEFAULT_HEADERS, timeout=timeout, follow_redirects=True)

    def _get_json(self, path: str, params: Optional[dict[str, Any]] = None) -> Any:
        response = self.client.get(f'{self.base_url}{path}', params=params)
        response.raise_for_status()
        return response.json()

    def list_sports(self) -> list[dict[str, Any]]:
        data = self._get_json('/sports')
        return data if isinstance(data, list) else []

    def list_events(
        self,
        *,
        tag_id: Optional[int] = None,
        active: bool = True,
        closed: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            'active': str(active).lower(),
            'closed': str(closed).lower(),
            'limit': limit,
            'offset': offset,
        }
        if tag_id is not None:
            params['tag_id'] = tag_id
        data = self._get_json('/events', params=params)
        return data if isinstance(data, list) else []

    def iter_cs2_events(self, page_size: int = 100, max_pages: int = 5) -> Iterable[dict[str, Any]]:
        for page in range(max_pages):
            offset = page * page_size
            events = self.list_events(tag_id=CS2_TAG_ID, limit=page_size, offset=offset)
            if not events:
                break
            for event in events:
                yield event
            if len(events) < page_size:
                break

    @staticmethod
    def classify_market_type(question: str) -> Optional[MarketType]:
        q = (question or '').lower()
        if 'total maps' in q or 'maps total' in q or 'over' in q and 'maps' in q:
            return MarketType.MAP_TOTALS
        if 'map handicap' in q or 'handicap' in q and 'map' in q:
            return MarketType.MAP_HANDICAP
        if 'map 1' in q or 'map 2' in q or 'map 3' in q or 'on map' in q:
            return MarketType.MAP_WINNER
        if 'will ' in q and (' beat ' in q or ' defeat ' in q or ' win ' in q):
            return MarketType.MATCH_WINNER
        return None

    @staticmethod
    def _parse_jsonish_list(value: Any) -> list[Any]:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, list) else []
            except json.JSONDecodeError:
                return []
        return []

    def normalize_market(self, market: dict[str, Any]) -> list[OddsSnapshot]:
        question = market.get('question') or ''
        market_type = self.classify_market_type(question)
        if market_type is None:
            return []

        outcomes = self._parse_jsonish_list(market.get('outcomes'))
        prices = self._parse_jsonish_list(market.get('outcomePrices'))
        observed_at = datetime.now(timezone.utc)
        snapshots: list[OddsSnapshot] = []

        for outcome, price in zip(outcomes, prices):
            try:
                price_f = float(price)
            except (TypeError, ValueError):
                continue
            snapshots.append(
                OddsSnapshot(
                    source='polymarket',
                    market_id=str(market.get('id')),
                    question=question,
                    market_type=market_type,
                    selection=str(outcome),
                    price=price_f,
                    implied_probability=price_f,
                    observed_at=observed_at,
                    raw_payload=market,
                )
            )
        return snapshots

    def collect_cs2_market_snapshots(self, max_pages: int = 5) -> list[OddsSnapshot]:
        snapshots: list[OddsSnapshot] = []
        for event in self.iter_cs2_events(max_pages=max_pages):
            for market in event.get('markets') or []:
                snapshots.extend(self.normalize_market(market))
        return snapshots

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
