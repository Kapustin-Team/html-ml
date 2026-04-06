from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from html_ml.config import settings


class Base(DeclarativeBase):
    pass


class LiveMatchSnapshotORM(Base):
    __tablename__ = 'live_match_snapshots'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), index=True)
    external_match_id: Mapped[str] = mapped_column(String(255), index=True)
    match_title: Mapped[str] = mapped_column(String(255))
    team_a: Mapped[str] = mapped_column(String(255))
    team_b: Mapped[str] = mapped_column(String(255))
    event_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    current_map_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    map_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score_team_a: Mapped[int] = mapped_column(Integer, default=0)
    score_team_b: Mapped[int] = mapped_column(Integer, default=0)
    maps_team_a: Mapped[int] = mapped_column(Integer, default=0)
    maps_team_b: Mapped[int] = mapped_column(Integer, default=0)
    team_a_side: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    team_b_side: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSON)
    observed_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class OddsSnapshotORM(Base):
    __tablename__ = 'odds_snapshots'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), index=True)
    market_id: Mapped[str] = mapped_column(String(255), index=True)
    question: Mapped[str] = mapped_column(Text)
    market_type: Mapped[str] = mapped_column(String(50), index=True)
    selection: Mapped[str] = mapped_column(String(255), index=True)
    price: Mapped[float] = mapped_column(Float)
    implied_probability: Mapped[float] = mapped_column(Float)
    raw_payload: Mapped[dict] = mapped_column(JSON)
    observed_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class AgentDecisionORM(Base):
    __tablename__ = 'agent_decisions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_name: Mapped[str] = mapped_column(String(100), index=True)
    model_name: Mapped[str] = mapped_column(String(100), index=True)
    aggression: Mapped[str] = mapped_column(String(50), index=True)
    market_type: Mapped[str] = mapped_column(String(50), index=True)
    selection: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(50), index=True)
    stake_usd: Mapped[float] = mapped_column(Float, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime, index=True)


engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
