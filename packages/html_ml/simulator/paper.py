from __future__ import annotations

from dataclasses import dataclass

from html_ml.config import settings
from html_ml.models.domain import AgentDecision


@dataclass
class PaperBankroll:
    starting_bankroll: float = settings.bankroll_usd
    current_bankroll: float = settings.bankroll_usd

    def apply_win(self, decision: AgentDecision, decimal_odds: float) -> None:
        self.current_bankroll += decision.stake_usd * max(decimal_odds - 1.0, 0)

    def apply_loss(self, decision: AgentDecision) -> None:
        self.current_bankroll -= decision.stake_usd
