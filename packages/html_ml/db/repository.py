from sqlalchemy.orm import Session

from html_ml.db.schema import AgentDecisionORM, LiveMatchSnapshotORM, OddsSnapshotORM
from html_ml.models.domain import AgentDecision, LiveMatchState, OddsSnapshot


def save_live_match_snapshot(db: Session, snapshot: LiveMatchState) -> LiveMatchSnapshotORM:
    row = LiveMatchSnapshotORM(**snapshot.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def save_odds_snapshot(db: Session, snapshot: OddsSnapshot) -> OddsSnapshotORM:
    row = OddsSnapshotORM(**snapshot.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def save_agent_decision(db: Session, decision: AgentDecision) -> AgentDecisionORM:
    row = AgentDecisionORM(**decision.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
