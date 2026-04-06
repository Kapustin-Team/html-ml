from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from html_ml.models.domain import MatchLink


@dataclass
class LinkedMarketView:
    hltv_match_id: str
    match_title: str
    event_name: str | None
    format: str | None
    live: bool
    time_text: str | None
    polymarket_market_id: str
    polymarket_question: str
    link_score: float
    matched_by: str
    team_a: str
    team_b: str
    team_a_price: float | None
    team_b_price: float | None
    team_a_prev_price: float | None
    team_b_prev_price: float | None
    current_map_name: str | None = None
    map_score: str | None = None
    round_score: str | None = None
    round_winner_side: str | None = None
    live_win_prob_team_a: float | None = None
    live_win_prob_team_b: float | None = None
    live_win_prob_ot: float | None = None
    observed_at: datetime = None  # type: ignore[assignment]


@dataclass
class CandidateBet:
    match_title: str
    selection: str
    price: float
    edge_score: float
    confidence: float
    reason: str
    live: bool
    link_score: float
    observed_at: datetime


def price_delta(now: float | None, prev: float | None) -> float | None:
    if now is None or prev is None:
        return None
    return now - prev


def build_candidate_bets(rows: list[LinkedMarketView], min_link_score: float = 0.68) -> list[CandidateBet]:
    candidates: list[CandidateBet] = []
    for row in rows:
        if row.link_score < min_link_score:
            continue
        if row.team_a_price is None or row.team_b_price is None:
            continue

        spread = abs(row.team_a_price - row.team_b_price)
        a_delta = price_delta(row.team_a_price, row.team_a_prev_price)
        b_delta = price_delta(row.team_b_price, row.team_b_prev_price)

        # Heuristic v1:
        # - prefer tighter markets (information-rich)
        # - prefer side with recent downward move (price shortening)
        # - slightly prefer live markets once linked confidently
        if spread > 0.22:
            continue

        preferred_selection: str | None = None
        preferred_price: float | None = None
        move_bonus = 0.0
        reason_parts: list[str] = []

        if a_delta is not None and a_delta < -0.015:
            preferred_selection = row.team_a
            preferred_price = row.team_a_price
            move_bonus = min(0.12, abs(a_delta) * 2.5)
            reason_parts.append(f'{row.team_a} shortened {a_delta:+.3f}')
        elif b_delta is not None and b_delta < -0.015:
            preferred_selection = row.team_b
            preferred_price = row.team_b_price
            move_bonus = min(0.12, abs(b_delta) * 2.5)
            reason_parts.append(f'{row.team_b} shortened {b_delta:+.3f}')
        else:
            if row.team_a_price <= row.team_b_price:
                preferred_selection = row.team_a
                preferred_price = row.team_a_price
            else:
                preferred_selection = row.team_b
                preferred_price = row.team_b_price
            reason_parts.append('tight market without strong recent move')

        if preferred_selection is None or preferred_price is None:
            continue

        tightness = max(0.0, 0.22 - spread) / 0.22
        live_bonus = 0.05 if row.live else 0.0
        edge_score = min(1.0, 0.45 * row.link_score + 0.35 * tightness + move_bonus + live_bonus)
        confidence = min(0.95, 0.5 + edge_score * 0.4)
        reason_parts.append(f'link {row.link_score:.3f}')
        reason_parts.append(f'spread {spread:.3f}')
        if row.live:
            reason_parts.append('live match')

        candidates.append(
            CandidateBet(
                match_title=row.match_title,
                selection=preferred_selection,
                price=preferred_price,
                edge_score=round(edge_score, 4),
                confidence=round(confidence, 4),
                reason='; '.join(reason_parts),
                live=row.live,
                link_score=row.link_score,
                observed_at=row.observed_at,
            )
        )

    candidates.sort(key=lambda item: (item.edge_score, item.confidence), reverse=True)
    return candidates


def match_link_index(links: list[MatchLink]) -> dict[str, MatchLink]:
    return {link.hltv_match_id: link for link in links}
