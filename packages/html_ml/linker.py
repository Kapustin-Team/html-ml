from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from typing import Iterable

from html_ml.models.domain import MatchLink

STOPWORDS = {
    'esports', 'esport', 'team', 'gaming', 'club', 'clan', 'cs2', 'cs', 'counter', 'strike'
}

ALIASES = {
    'mongolz': 'the mongolz',
    'eyeballers': 'eyeballers',
    'parivision': 'parivision',
    'bcgame': 'bc game',
}


@dataclass
class HltvMatchRow:
    match_id: str
    match_title: str
    team_a: str
    team_b: str
    event_name: str | None
    observed_at: datetime


@dataclass
class PolymarketRow:
    market_id: str
    question: str
    market_type: str
    observed_at: datetime


@dataclass
class CandidateLink:
    market_id: str
    question: str
    score: float
    matched_by: str


def normalize_name(value: str) -> str:
    text = value.lower().strip()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if text in ALIASES:
        text = ALIASES[text]
    tokens = [token for token in text.split() if token not in STOPWORDS]
    return ' '.join(tokens).strip()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_name(a), normalize_name(b)).ratio()


def extract_question_teams(question: str) -> tuple[str | None, str | None]:
    patterns = [
        r'(?P<a>.+?)\s+vs\.?\s+(?P<b>.+?)(?:$|\?| for | at | in )',
        r'(?P<a>.+?)\s+versus\s+(?P<b>.+?)(?:$|\?| for | at | in )',
    ]
    q = question.strip()
    for pattern in patterns:
        match = re.search(pattern, q, flags=re.IGNORECASE)
        if match:
            return match.group('a').strip(), match.group('b').strip()
    return None, None


def score_link(team_a: str, team_b: str, question: str) -> tuple[float, str]:
    normalized_question = normalize_name(question)
    q_team_a, q_team_b = extract_question_teams(question)
    if not q_team_a or not q_team_b:
        a_score = max(similarity(team_a, question), 0.0)
        b_score = max(similarity(team_b, question), 0.0)
        contains_bonus = 0.15 if normalize_name(team_a) in normalized_question and normalize_name(team_b) in normalized_question else 0.0
        score = min(1.0, ((a_score + b_score) / 2.0) + contains_bonus)
        return score, 'question-fuzzy'

    direct = (similarity(team_a, q_team_a) + similarity(team_b, q_team_b)) / 2.0
    swapped = (similarity(team_a, q_team_b) + similarity(team_b, q_team_a)) / 2.0

    exact_direct = normalize_name(team_a) in normalize_name(q_team_a) and normalize_name(team_b) in normalize_name(q_team_b)
    exact_swapped = normalize_name(team_a) in normalize_name(q_team_b) and normalize_name(team_b) in normalize_name(q_team_a)

    if exact_swapped and swapped >= direct:
        return min(1.0, swapped + 0.1), 'team-swap-fuzzy'
    if exact_direct and direct >= swapped:
        return min(1.0, direct + 0.1), 'team-order-fuzzy'
    if swapped > direct:
        return swapped, 'team-swap-fuzzy'
    return direct, 'team-order-fuzzy'


def link_hltv_to_polymarket(
    hltv_rows: Iterable[HltvMatchRow],
    polymarket_rows: Iterable[PolymarketRow],
    min_score: float = 0.72,
) -> list[MatchLink]:
    rows = [row for row in polymarket_rows if row.market_type == 'match_winner']
    links: list[MatchLink] = []
    seen_hltv: set[str] = set()

    for match in hltv_rows:
        best: CandidateLink | None = None
        for market in rows:
            score, matched_by = score_link(match.team_a, match.team_b, market.question)
            if score < min_score:
                continue
            if best is None or score > best.score:
                best = CandidateLink(
                    market_id=market.market_id,
                    question=market.question,
                    score=score,
                    matched_by=matched_by,
                )
        if best and match.match_id not in seen_hltv:
            seen_hltv.add(match.match_id)
            links.append(
                MatchLink(
                    hltv_match_id=match.match_id,
                    hltv_match_title=match.match_title,
                    polymarket_market_id=best.market_id,
                    polymarket_question=best.question,
                    score=round(best.score, 4),
                    matched_by=best.matched_by,
                    observed_at=match.observed_at,
                    raw_payload={
                        'event_name': match.event_name,
                    },
                )
            )
    links.sort(key=lambda item: item.score, reverse=True)
    return links
