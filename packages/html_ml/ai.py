from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx

from html_ml.llm import OpenRouterClient
from html_ml.signals import LinkedMarketView


SYSTEM_PROMPT = """You are a disciplined esports betting analyst for Counter-Strike matches.
Return only valid JSON.
Do not invent unavailable facts.
Use only the provided structured data.
Be conservative with confidence.
Prefer PASS over weak bets.
If live context is present, use it explicitly in reasoning.
Differentiate between pre-match market price and HLTV live win probability.
A strong disagreement between live win probability and market price can justify WATCH or small BET, but only when live context is clearly available.
Schema:
{
  "action": "BET" | "WATCH" | "PASS",
  "selection": "string or empty",
  "confidence": 0.0,
  "stake_fraction": 0.0,
  "reasoning": ["short bullet", "short bullet"],
  "risk_flags": ["flag"],
  "summary": "one short sentence"
}
"""


@dataclass
class AIBetRecommendation:
    match_title: str
    action: str
    selection: str
    confidence: float
    stake_fraction: float
    summary: str
    reasoning: list[str]
    risk_flags: list[str]
    observed_at: datetime
    error: Optional[str] = None


class MatchAnalyst:
    def __init__(self, client: OpenRouterClient | None = None, api_key: str | None = None, model: str | None = None) -> None:
        self.client = client or OpenRouterClient(api_key=api_key, model=model)

    def analyze(self, row: LinkedMarketView) -> AIBetRecommendation:
        payload = {
            'match_title': row.match_title,
            'event_name': row.event_name,
            'format': row.format,
            'live': row.live,
            'time_text': row.time_text,
            'team_a': row.team_a,
            'team_b': row.team_b,
            'team_a_price': row.team_a_price,
            'team_b_price': row.team_b_price,
            'team_a_prev_price': row.team_a_prev_price,
            'team_b_prev_price': row.team_b_prev_price,
            'link_score': row.link_score,
            'matched_by': row.matched_by,
            'polymarket_question': row.polymarket_question,
            'current_map_name': row.current_map_name,
            'map_score': row.map_score,
            'round_score': row.round_score,
            'round_winner_side': row.round_winner_side,
            'live_win_probability': {
                'team_a': row.live_win_prob_team_a,
                'team_b': row.live_win_prob_team_b,
                'ot': row.live_win_prob_ot,
            },
        }
        try:
            result = self.client.chat_json(
                SYSTEM_PROMPT,
                'Analyze this linked CS2 betting market and produce a disciplined recommendation:\n' + json.dumps(payload, ensure_ascii=False),
            )
            return AIBetRecommendation(
                match_title=row.match_title,
                action=str(result.get('action') or 'PASS').upper(),
                selection=str(result.get('selection') or ''),
                confidence=float(result.get('confidence') or 0.0),
                stake_fraction=float(result.get('stake_fraction') or 0.0),
                summary=str(result.get('summary') or ''),
                reasoning=[str(x) for x in (result.get('reasoning') or [])],
                risk_flags=[str(x) for x in (result.get('risk_flags') or [])],
                observed_at=row.observed_at,
            )
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            return AIBetRecommendation(
                match_title=row.match_title,
                action='PASS',
                selection='',
                confidence=0.0,
                stake_fraction=0.0,
                summary='LLM analysis unavailable, defaulting to PASS.',
                reasoning=['Structured AI analysis failed for this market.'],
                risk_flags=['llm_unavailable'],
                observed_at=row.observed_at,
                error=str(exc),
            )
