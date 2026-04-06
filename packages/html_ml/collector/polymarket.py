from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from pydantic import BaseModel

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


class WatchMarket(BaseModel):
    question: str
    outcomes: list[str]
    prices: list[float]


class WatchMatch(BaseModel):
    event_id: str
    slug: Optional[str] = None
    title: str
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    match_market: Optional[WatchMarket] = None
    total_market: Optional[WatchMarket] = None
    handicap_market: Optional[WatchMarket] = None

    @property
    def score(self) -> float:
        score = 0.0
        if self.match_market and len(self.match_market.prices) >= 2:
            spread = abs(self.match_market.prices[0] - self.match_market.prices[1])
            score += 1.0 - min(spread, 1.0)
        if self.total_market and len(self.total_market.prices) >= 2:
            total_spread = abs(self.total_market.prices[0] - self.total_market.prices[1])
            score += 1.0 - min(total_spread, 1.0)
        if self.handicap_market and len(self.handicap_market.prices) >= 2:
            handicap_spread = abs(self.handicap_market.prices[0] - self.handicap_market.prices[1])
            score += 1.0 - min(handicap_spread, 1.0)
        return score


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

    @staticmethod
    def _parse_dt(value: Any) -> Optional[datetime]:
        if not value or not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None

    def _to_watch_market(self, market: dict[str, Any]) -> Optional[WatchMarket]:
        outcomes_raw = self._parse_jsonish_list(market.get('outcomes'))
        prices_raw = self._parse_jsonish_list(market.get('outcomePrices'))
        if not outcomes_raw or not prices_raw:
            return None

        prices: list[float] = []
        for price in prices_raw:
            try:
                prices.append(float(price))
            except (TypeError, ValueError):
                return None

        return WatchMarket(
            question=str(market.get('question') or ''),
            outcomes=[str(x) for x in outcomes_raw],
            prices=prices,
        )

    def build_watch_match(self, event: dict[str, Any]) -> Optional[WatchMatch]:
        title = str(event.get('title') or '').strip()

        match_market: Optional[WatchMarket] = None
        total_market: Optional[WatchMarket] = None
        handicap_market: Optional[WatchMarket] = None

        for market in event.get('markets') or []:
            question = str(market.get('question') or '')
            normalized = self._to_watch_market(market)
            if normalized is None:
                continue
            lowered = question.lower()
            if (' vs ' in lowered or ' versus ' in lowered or ' beat ' in lowered) and 'map ' not in lowered and 'total' not in lowered and 'handicap' not in lowered:
                match_market = normalized
                if not title:
                    title = question
            elif question.startswith('Games Total:') or 'total maps' in lowered or 'games total' in lowered:
                total_market = normalized
            elif question.startswith('Map Handicap:') or 'handicap' in lowered:
                handicap_market = normalized

        if match_market is None:
            return None

        if not title:
            title = match_market.question

        return WatchMatch(
            event_id=str(event.get('id')),
            slug=event.get('slug'),
            title=title,
            start_at=self._parse_dt(event.get('startDate')),
            end_at=self._parse_dt(event.get('endDate')),
            match_market=match_market,
            total_market=total_market,
            handicap_market=handicap_market,
        )

    def list_watch_matches(self, max_pages: int = 5, only_future: bool = True) -> list[WatchMatch]:
        now = datetime.now(timezone.utc)
        matches: list[WatchMatch] = []
        for event in self.iter_cs2_events(max_pages=max_pages):
            watch_match = self.build_watch_match(event)
            if watch_match is None:
                continue
            if only_future and watch_match.end_at and watch_match.end_at < now:
                continue
            matches.append(watch_match)
        return matches

    def top_watch_matches(self, limit: int = 10, max_pages: int = 5, only_future: bool = True) -> list[WatchMatch]:
        matches = self.list_watch_matches(max_pages=max_pages, only_future=only_future)
        matches.sort(key=lambda m: ((m.end_at or datetime.max.replace(tzinfo=timezone.utc)), -m.score))
        return matches[:limit]

    def collect_watchlist_snapshots(self, limit: int = 10, max_pages: int = 5) -> list[OddsSnapshot]:
        observed_at = datetime.now(timezone.utc)
        snapshots: list[OddsSnapshot] = []
        for match in self.top_watch_matches(limit=limit, max_pages=max_pages, only_future=True):
            for market_type, watch_market in (
                (MarketType.MATCH_WINNER, match.match_market),
                (MarketType.MAP_TOTALS, match.total_market),
                (MarketType.MAP_HANDICAP, match.handicap_market),
            ):
                if watch_market is None:
                    continue
                for outcome, price in zip(watch_market.outcomes, watch_market.prices):
                    snapshots.append(
                        OddsSnapshot(
                            source='polymarket',
                            market_id=f'{match.event_id}:{market_type.value}:{watch_market.question}',
                            question=watch_market.question,
                            market_type=market_type,
                            selection=str(outcome),
                            price=float(price),
                            implied_probability=float(price),
                            observed_at=observed_at,
                            raw_payload={
                                'event_id': match.event_id,
                                'slug': match.slug,
                                'title': match.title,
                                'end_at': match.end_at.isoformat() if match.end_at else None,
                                'watch_score': match.score,
                            },
                        )
                    )
        return snapshots

    def collect_cs2_market_snapshots(self, max_pages: int = 5, only_future: bool = False) -> list[OddsSnapshot]:
        observed_at = datetime.now(timezone.utc)
        snapshots: list[OddsSnapshot] = []
        matches = self.list_watch_matches(max_pages=max_pages, only_future=only_future)
        for match in matches:
            for market_type, watch_market in (
                (MarketType.MATCH_WINNER, match.match_market),
                (MarketType.MAP_TOTALS, match.total_market),
                (MarketType.MAP_HANDICAP, match.handicap_market),
            ):
                if watch_market is None:
                    continue
                for outcome, price in zip(watch_market.outcomes, watch_market.prices):
                    snapshots.append(
                        OddsSnapshot(
                            source='polymarket',
                            market_id=f'{match.event_id}:{market_type.value}:{watch_market.question}',
                            question=watch_market.question,
                            market_type=market_type,
                            selection=str(outcome),
                            price=float(price),
                            implied_probability=float(price),
                            observed_at=observed_at,
                            raw_payload={
                                'event_id': match.event_id,
                                'slug': match.slug,
                                'title': match.title,
                                'end_at': match.end_at.isoformat() if match.end_at else None,
                                'watch_score': match.score,
                            },
                        )
                    )
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
