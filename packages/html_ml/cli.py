from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table

from html_ml.agents.baseline import BaselineFlatBetAgent
from html_ml.collector.hltv import HLTVLiveCollector
from html_ml.collector.polymarket import PolymarketCollector
from html_ml.db.repository import save_agent_decision, save_live_match_snapshot, save_odds_snapshot
from html_ml.db.schema import SessionLocal, init_db
from html_ml.models.domain import AggressionProfile

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def initdb() -> None:
    init_db()
    console.print('[green]Database initialized.[/green]')


@app.command()
def collect_stub() -> None:
    init_db()
    hltv = HLTVLiveCollector()
    poly = PolymarketCollector()
    with SessionLocal() as db:
        for snapshot in hltv.collect_once_stub():
            save_live_match_snapshot(db, snapshot)
        for odds in poly.collect_once_stub():
            save_odds_snapshot(db, odds)
    console.print('[green]Stub live snapshots saved.[/green]')


@app.command()
def run_baseline(aggression: AggressionProfile = AggressionProfile.BALANCED) -> None:
    init_db()
    hltv = HLTVLiveCollector()
    poly = PolymarketCollector()
    agent = BaselineFlatBetAgent()

    snapshots = hltv.collect_once_stub()
    odds_list = poly.collect_once_stub()
    decisions = []

    with SessionLocal() as db:
        for snapshot in snapshots:
            save_live_match_snapshot(db, snapshot)
        for odds in odds_list:
            save_odds_snapshot(db, odds)

        for snapshot in snapshots:
            for odds in odds_list:
                decision = agent.decide(snapshot, odds, aggression=aggression)
                save_agent_decision(db, decision)
                decisions.append(decision)

    table = Table(title='Baseline Decisions')
    table.add_column('Agent')
    table.add_column('Aggression')
    table.add_column('Selection')
    table.add_column('Action')
    table.add_column('Stake')
    table.add_column('Confidence')

    for d in decisions:
        table.add_row(d.agent_name, d.aggression.value, d.selection, d.action, f'${d.stake_usd:.2f}', f'{d.confidence:.2f}')

    console.print(table)


@app.command()
def print_config() -> None:
    from html_ml.config import settings

    console.print_json(json.dumps(settings.model_dump(), default=str))


if __name__ == '__main__':
    app()
