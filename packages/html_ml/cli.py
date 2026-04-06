from __future__ import annotations

import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys

import typer
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text

from html_ml.agents.baseline import BaselineFlatBetAgent
from html_ml.collector.hltv import HLTVLiveCollector
from html_ml.collector.polymarket import PolymarketCollector
from sqlalchemy import desc, func, select

from html_ml.db.repository import save_agent_decision, save_live_match_snapshot, save_odds_snapshot
from html_ml.db.schema import LiveMatchSnapshotORM, OddsSnapshotORM, SessionLocal, init_db
from html_ml.ai import MatchAnalyst
from html_ml.linker import HltvMatchRow, PolymarketRow, link_hltv_to_polymarket
from html_ml.models.domain import AggressionProfile
from html_ml.signals import LinkedMarketView, build_candidate_bets

app = typer.Typer(no_args_is_help=True)
console = Console()


def _print_banner(title: str, subtitle: str | None = None) -> None:
    body = title if not subtitle else f'{title}\n[dim]{subtitle}[/dim]'
    console.print(Panel.fit(body, border_style='cyan'))


def _print_step(step: str, message: str) -> None:
    console.print(f'\n[bold cyan]{step}[/bold cyan] {message}')


def _compact_live_context(view: LinkedMarketView) -> str:
    parts: list[str] = []
    if view.current_map_name:
        parts.append(str(view.current_map_name))
    if view.round_score:
        parts.append(f'round {view.round_score}')
    if view.live_win_prob_team_a is not None and view.live_win_prob_team_b is not None:
        parts.append(f'wp {view.team_a} {view.live_win_prob_team_a:.1f}% / {view.team_b} {view.live_win_prob_team_b:.1f}%')
    return ' | '.join(parts) if parts else '-'


def _compact_momentum(view: LinkedMarketView) -> str:
    parts: list[str] = []
    if view.team_a_momentum is not None:
        parts.append(f'{view.team_a} {view.team_a_momentum:+.3f}')
    if view.team_b_momentum is not None:
        parts.append(f'{view.team_b} {view.team_b_momentum:+.3f}')
    if view.market_bias:
        parts.append(f'bias {view.market_bias}')
    return ' | '.join(parts) if parts else '-'


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
def research_polymarket(limit_pages: int = 2) -> None:
    poly = PolymarketCollector()
    events = list(poly.iter_cs2_events(max_pages=limit_pages))
    market_counter: Counter[str] = Counter()
    rows: list[tuple[str, str, int]] = []

    for event in events:
        title = event.get('title') or 'Untitled'
        markets = event.get('markets') or []
        rows.append((str(event.get('id')), title, len(markets)))
        for market in markets:
            mt = poly.classify_market_type(market.get('question') or '')
            market_counter[str(mt.value if mt else 'unknown')] += 1

    table = Table(title='Polymarket CS2 Events')
    table.add_column('Event ID')
    table.add_column('Title')
    table.add_column('Markets')
    for event_id, title, count in rows[:20]:
        table.add_row(event_id, title, str(count))
    console.print(table)

    summary = Table(title='Detected Market Types')
    summary.add_column('Type')
    summary.add_column('Count')
    for key, count in market_counter.most_common():
        summary.add_row(key, str(count))
    console.print(summary)
    console.print(f'[cyan]Scanned events:[/cyan] {len(events)}')


@app.command()
def collect_polymarket(max_pages: int = 2) -> None:
    init_db()
    poly = PolymarketCollector()
    snapshots = poly.collect_cs2_market_snapshots(max_pages=max_pages)
    with SessionLocal() as db:
        for odds in snapshots:
            save_odds_snapshot(db, odds)
    console.print(f'[green]Saved {len(snapshots)} Polymarket odds snapshots.[/green]')


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
def db_summary() -> None:
    init_db()
    with SessionLocal() as db:
        total_snapshots = db.scalar(select(func.count()).select_from(OddsSnapshotORM)) or 0
        by_market_type = db.execute(
            select(OddsSnapshotORM.market_type, func.count()).group_by(OddsSnapshotORM.market_type)
        ).all()

    table = Table(title='Odds Snapshot Summary')
    table.add_column('Market Type')
    table.add_column('Count')
    for market_type, count in by_market_type:
        table.add_row(str(market_type), str(count))
    console.print(table)
    console.print(f'[cyan]Total odds snapshots:[/cyan] {total_snapshots}')


@app.command()
def watch_today(limit: int = 12, max_pages: int = 5) -> None:
    poly = PolymarketCollector()
    matches = poly.list_watch_matches(max_pages=max_pages, only_future=True)
    matches.sort(key=lambda m: ((m.end_at or datetime.max.replace(tzinfo=timezone.utc)), -m.score))

    table = Table(title='Today / Upcoming CS2 Watchlist')
    table.add_column('End (UTC)')
    table.add_column('Match')
    table.add_column('Moneyline')
    table.add_column('O/U 2.5')
    table.add_column('Handicap')
    table.add_column('Score')

    for match in matches[:limit]:
        end_at = match.end_at.isoformat(timespec='minutes') if match.end_at else '-'
        moneyline = '-'
        total = '-'
        handicap = '-'

        if match.match_market and len(match.match_market.outcomes) >= 2 and len(match.match_market.prices) >= 2:
            moneyline = (
                f"{match.match_market.outcomes[0]} {match.match_market.prices[0]:.3f} | "
                f"{match.match_market.outcomes[1]} {match.match_market.prices[1]:.3f}"
            )
        if match.total_market and len(match.total_market.outcomes) >= 2 and len(match.total_market.prices) >= 2:
            total = f"{match.total_market.prices[0]:.3f} / {match.total_market.prices[1]:.3f}"
        if match.handicap_market and len(match.handicap_market.outcomes) >= 2 and len(match.handicap_market.prices) >= 2:
            handicap = (
                f"{match.handicap_market.outcomes[0]} {match.handicap_market.prices[0]:.3f} | "
                f"{match.handicap_market.outcomes[1]} {match.handicap_market.prices[1]:.3f}"
            )

        table.add_row(end_at, match.title, moneyline, total, handicap, f'{match.score:.2f}')

    console.print(table)


@app.command()
def poll_watchlist(iterations: int = 3, interval_sec: int = 30, limit: int = 10, max_pages: int = 5) -> None:
    init_db()
    poly = PolymarketCollector()
    total_saved = 0
    for idx in range(iterations):
        snapshots = poly.collect_watchlist_snapshots(limit=limit, max_pages=max_pages)
        with SessionLocal() as db:
            for snapshot in snapshots:
                save_odds_snapshot(db, snapshot)
        total_saved += len(snapshots)
        console.print(
            f'[green]poll {idx + 1}/{iterations}[/green] saved {len(snapshots)} snapshots '
            f'(total {total_saved}) at {datetime.now(timezone.utc).isoformat(timespec="seconds")}'
        )
        if idx < iterations - 1:
            time.sleep(interval_sec)


def _latest_previous_prices() -> dict[tuple[str, str], tuple[float, datetime]]:
    with SessionLocal() as db:
        rows = db.execute(
            select(OddsSnapshotORM.market_id, OddsSnapshotORM.selection, OddsSnapshotORM.price, OddsSnapshotORM.observed_at)
            .order_by(OddsSnapshotORM.market_id, OddsSnapshotORM.selection, desc(OddsSnapshotORM.observed_at))
        ).all()

    latest: dict[tuple[str, str], tuple[float, datetime]] = {}
    previous: dict[tuple[str, str], tuple[float, datetime]] = {}
    for market_id, selection, price, observed_at in rows:
        key = (str(market_id), str(selection))
        if key not in latest:
            latest[key] = (float(price), observed_at)
        elif key not in previous:
            previous[key] = (float(price), observed_at)
    return previous


def _market_momentum_index(max_points: int = 6) -> dict[tuple[str, str], list[float]]:
    with SessionLocal() as db:
        rows = db.execute(
            select(OddsSnapshotORM.market_id, OddsSnapshotORM.selection, OddsSnapshotORM.price, OddsSnapshotORM.observed_at)
            .where(OddsSnapshotORM.source == 'polymarket')
            .order_by(OddsSnapshotORM.market_id, OddsSnapshotORM.selection, desc(OddsSnapshotORM.observed_at), desc(OddsSnapshotORM.id))
            .limit(8000)
        ).all()

    grouped: dict[tuple[str, str], list[float]] = {}
    for market_id, selection, price, _ in rows:
        key = (str(market_id), str(selection))
        bucket = grouped.setdefault(key, [])
        if len(bucket) < max_points:
            bucket.append(float(price))
    return grouped


def _compute_momentum(prices_desc: list[float]) -> float | None:
    if len(prices_desc) < 2:
        return None
    newest = prices_desc[0]
    oldest = prices_desc[-1]
    return newest - oldest


@app.command()
def market_moves(limit: int = 20) -> None:
    previous = _latest_previous_prices()
    with SessionLocal() as db:
        rows = db.execute(
            select(
                OddsSnapshotORM.market_id,
                OddsSnapshotORM.question,
                OddsSnapshotORM.selection,
                OddsSnapshotORM.price,
                OddsSnapshotORM.observed_at,
            ).order_by(desc(OddsSnapshotORM.observed_at), desc(OddsSnapshotORM.id))
        ).all()

    seen: set[tuple[str, str]] = set()
    moves: list[tuple[float, str, str, float, float, datetime]] = []
    for market_id, question, selection, price, observed_at in rows:
        key = (str(market_id), str(selection))
        if key in seen:
            continue
        seen.add(key)
        if key not in previous:
            continue
        prev_price, _ = previous[key]
        current_price = float(price)
        delta = current_price - prev_price
        moves.append((abs(delta), str(question), str(selection), prev_price, current_price, observed_at))

    moves.sort(key=lambda row: row[0], reverse=True)

    table = Table(title='Top Market Moves')
    table.add_column('Observed (UTC)')
    table.add_column('Question')
    table.add_column('Selection')
    table.add_column('Prev')
    table.add_column('Now')
    table.add_column('Delta')

    for _, question, selection, prev_price, current_price, observed_at in moves[:limit]:
        delta = current_price - prev_price
        arrow = '↑' if delta > 0 else '↓' if delta < 0 else '→'
        table.add_row(
            observed_at.isoformat(timespec='seconds'),
            question,
            selection,
            f'{prev_price:.3f}',
            f'{current_price:.3f}',
            f'{arrow} {delta:+.3f}',
        )
    console.print(table)


@app.command()
def dashboard(limit: int = 10, max_pages: int = 5, refresh_sec: int = 15, cycles: int = 20) -> None:
    poly = PolymarketCollector()

    def build_table() -> Table:
        previous = _latest_previous_prices()
        matches = poly.top_watch_matches(limit=limit, max_pages=max_pages, only_future=True)
        table = Table(title='html-ml live dashboard')
        table.add_column('End (UTC)')
        table.add_column('Match')
        table.add_column('Moneyline')
        table.add_column('Move')
        table.add_column('O/U')
        table.add_column('HCAP')
        table.add_column('Score')

        for match in matches:
            end_at = match.end_at.isoformat(timespec='minutes') if match.end_at else '-'
            moneyline = '-'
            total = '-'
            handicap = '-'
            move = '-'

            if match.match_market and len(match.match_market.outcomes) >= 2 and len(match.match_market.prices) >= 2:
                moneyline = (
                    f"{match.match_market.outcomes[0]} {match.match_market.prices[0]:.3f} | "
                    f"{match.match_market.outcomes[1]} {match.match_market.prices[1]:.3f}"
                )
                deltas: list[str] = []
                market_id = f'{match.event_id}:match_winner:{match.match_market.question}'
                for outcome, price in zip(match.match_market.outcomes, match.match_market.prices):
                    prev = previous.get((market_id, str(outcome)))
                    if prev is None:
                        continue
                    prev_price, _ = prev
                    delta = float(price) - prev_price
                    if abs(delta) < 0.0005:
                        continue
                    arrow = '↑' if delta > 0 else '↓'
                    deltas.append(f'{outcome} {arrow}{delta:+.3f}')
                if deltas:
                    move = '; '.join(deltas)
            if match.total_market and len(match.total_market.prices) >= 2:
                total = f"{match.total_market.prices[0]:.3f} / {match.total_market.prices[1]:.3f}"
            if match.handicap_market and len(match.handicap_market.outcomes) >= 2 and len(match.handicap_market.prices) >= 2:
                handicap = (
                    f"{match.handicap_market.outcomes[0]} {match.handicap_market.prices[0]:.3f} | "
                    f"{match.handicap_market.outcomes[1]} {match.handicap_market.prices[1]:.3f}"
                )

            table.add_row(end_at, match.title, moneyline, move, total, handicap, f'{match.score:.2f}')

        return table

    with Live(build_table(), console=console, refresh_per_second=4) as live:
        for _ in range(cycles - 1):
            time.sleep(refresh_sec)
            live.update(build_table())


def _enrich_hltv_live_state(item: dict, wait_sec: int = 8) -> dict:
    href = item.get('href')
    if not href or not item.get('live'):
        return item
    url = href if str(href).startswith('http') else f'https://www.hltv.org{href}'
    script = Path(__file__).resolve().parents[2] / 'scripts' / 'hltv_match_details_playwright.py'
    cmd = [sys.executable, str(script), '--url', url, '--wait-sec', str(wait_sec)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        item['detail_error'] = result.stderr.strip() or result.stdout.strip() or 'detail probe failed'
        return item
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        item['detail_error'] = 'detail probe returned invalid json'
        return item
    state = payload.get('state') or {}
    item['live_detail'] = state
    return item


@app.command()
def probe_hltv(wait_sec: int = 15) -> None:
    script = Path(__file__).resolve().parents[2] / 'scripts' / 'hltv_probe.py'
    cmd = [sys.executable, str(script), '--wait-sec', str(wait_sec)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        console.print(result.stdout)
    if result.stderr:
        console.print(f'[yellow]{result.stderr}[/yellow]')
    if result.returncode != 0:
        raise typer.Exit(code=result.returncode)


@app.command()
def collect_hltv_matches(wait_sec: int = 12, limit: int = 20) -> None:
    import subprocess
    import sys
    from pathlib import Path

    script = Path(__file__).resolve().parents[2] / 'scripts' / 'hltv_matches_playwright.py'
    cmd = [sys.executable, str(script), '--wait-sec', str(wait_sec)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        if result.stdout:
            console.print(result.stdout)
        if result.stderr:
            console.print(f'[yellow]{result.stderr}[/yellow]')
        raise typer.Exit(code=result.returncode)

    payload = json.loads(result.stdout)
    collector = HLTVLiveCollector()
    raw_items = payload.get('matches', [])[:limit]
    enriched_items = [_enrich_hltv_live_state(item, wait_sec=max(6, min(wait_sec, 10))) for item in raw_items]
    rows = [collector.match_entry_to_state(item) for item in enriched_items]

    init_db()
    with SessionLocal() as db:
        for row in rows:
            save_live_match_snapshot(db, row)

    table = Table(title='HLTV Matches')
    table.add_column('Match ID')
    table.add_column('Match')
    table.add_column('Event')
    table.add_column('Format')
    table.add_column('Time')
    for state in rows:
        raw = state.raw_payload
        table.add_row(
            state.external_match_id,
            state.match_title,
            str(state.event_name or '-'),
            str(state.format or '-'),
            str(raw.get('time_text') or '-'),
        )
    console.print(table)
    console.print(f'[cyan]Saved HLTV match snapshots:[/cyan] {len(rows)}')


def _load_link_context(min_score: float = 0.72) -> tuple[list[LiveMatchSnapshotORM], list[OddsSnapshotORM], list]:
    init_db()
    with SessionLocal() as db:
        latest_hltv_rows = db.execute(
            select(LiveMatchSnapshotORM)
            .where(LiveMatchSnapshotORM.source == 'hltv')
            .order_by(desc(LiveMatchSnapshotORM.observed_at), desc(LiveMatchSnapshotORM.id))
            .limit(200)
        ).scalars().all()
        latest_odds_rows = db.execute(
            select(OddsSnapshotORM)
            .where(OddsSnapshotORM.source == 'polymarket')
            .order_by(desc(OddsSnapshotORM.observed_at), desc(OddsSnapshotORM.id))
            .limit(2000)
        ).scalars().all()

    dedup_hltv: dict[str, HltvMatchRow] = {}
    for row in latest_hltv_rows:
        dedup_hltv.setdefault(
            row.external_match_id,
            HltvMatchRow(
                match_id=row.external_match_id,
                match_title=row.match_title,
                team_a=row.team_a,
                team_b=row.team_b,
                event_name=row.event_name,
                observed_at=row.observed_at,
            ),
        )

    dedup_pm: dict[str, PolymarketRow] = {}
    for row in latest_odds_rows:
        dedup_pm.setdefault(
            row.market_id,
            PolymarketRow(
                market_id=row.market_id,
                question=row.question,
                market_type=row.market_type,
                observed_at=row.observed_at,
            ),
        )

    links = link_hltv_to_polymarket(dedup_hltv.values(), dedup_pm.values(), min_score=min_score)
    return latest_hltv_rows, latest_odds_rows, links


def _build_linked_market_views(min_score: float = 0.72) -> list[LinkedMarketView]:
    latest_hltv_rows, latest_odds_rows, links = _load_link_context(min_score=min_score)
    latest_hltv_by_match: dict[str, LiveMatchSnapshotORM] = {}
    for row in latest_hltv_rows:
        latest_hltv_by_match.setdefault(row.external_match_id, row)

    odds_by_market: dict[str, list[OddsSnapshotORM]] = {}
    for row in latest_odds_rows:
        odds_by_market.setdefault(row.market_id, []).append(row)

    previous_by_key = _latest_previous_prices()
    momentum_by_key = _market_momentum_index()
    views: list[LinkedMarketView] = []
    for link in links:
        match_row = latest_hltv_by_match.get(link.hltv_match_id)
        market_rows = odds_by_market.get(link.polymarket_market_id, [])
        if match_row is None or not market_rows:
            continue

        latest_by_selection: dict[str, OddsSnapshotORM] = {}
        for row in market_rows:
            latest_by_selection.setdefault(row.selection, row)

        team_a_row = latest_by_selection.get(match_row.team_a)
        team_b_row = latest_by_selection.get(match_row.team_b)
        if team_a_row is None or team_b_row is None:
            team_a_row = market_rows[0] if market_rows else None
            team_b_row = market_rows[1] if len(market_rows) > 1 else None
        if team_a_row is None or team_b_row is None:
            continue

        raw = match_row.raw_payload or {}
        live_detail = raw.get('live_detail') or {}
        live_probs = live_detail.get('live_win_probabilities') or {}
        map_score = None
        if match_row.maps_team_a is not None and match_row.maps_team_b is not None:
            map_score = f'{match_row.maps_team_a}-{match_row.maps_team_b}'
        round_score = None
        if live_detail.get('score_team_a') is not None and live_detail.get('score_team_b') is not None:
            round_score = f"{live_detail.get('score_team_a')}-{live_detail.get('score_team_b')}"
        team_a_momentum = _compute_momentum(momentum_by_key.get((team_a_row.market_id, team_a_row.selection), []))
        team_b_momentum = _compute_momentum(momentum_by_key.get((team_b_row.market_id, team_b_row.selection), []))
        market_tightness = 1.0 - abs(float(team_a_row.price) - float(team_b_row.price))
        market_bias = None
        if team_a_momentum is not None and team_b_momentum is not None:
            if team_a_momentum < team_b_momentum:
                market_bias = match_row.team_a
            elif team_b_momentum < team_a_momentum:
                market_bias = match_row.team_b
        views.append(
            LinkedMarketView(
                hltv_match_id=match_row.external_match_id,
                match_title=match_row.match_title,
                event_name=match_row.event_name,
                format=match_row.format,
                live=bool(raw.get('live')),
                time_text=raw.get('time_text'),
                polymarket_market_id=link.polymarket_market_id,
                polymarket_question=link.polymarket_question,
                link_score=link.score,
                matched_by=link.matched_by,
                team_a=match_row.team_a,
                team_b=match_row.team_b,
                team_a_price=float(team_a_row.price),
                team_b_price=float(team_b_row.price),
                team_a_prev_price=previous_by_key.get((team_a_row.market_id, team_a_row.selection), (None, None))[0],
                team_b_prev_price=previous_by_key.get((team_b_row.market_id, team_b_row.selection), (None, None))[0],
                current_map_name=match_row.current_map_name or raw.get('current_map_name'),
                map_score=map_score,
                round_score=round_score,
                round_winner_side=live_detail.get('round_winner_side'),
                live_win_prob_team_a=live_probs.get('team_a'),
                live_win_prob_team_b=live_probs.get('team_b'),
                live_win_prob_ot=live_probs.get('ot'),
                team_a_momentum=team_a_momentum,
                team_b_momentum=team_b_momentum,
                market_tightness=market_tightness,
                market_bias=market_bias,
                observed_at=max(match_row.observed_at, team_a_row.observed_at, team_b_row.observed_at),
            )
        )
    views.sort(key=lambda item: (item.live, item.link_score), reverse=True)
    return views


@app.command()
def link_markets(limit: int = 15, min_score: float = 0.72) -> None:
    _, _, links = _load_link_context(min_score=min_score)
    table = Table(title='HLTV ↔ Polymarket Links')
    table.add_column('HLTV Match ID')
    table.add_column('Match')
    table.add_column('Polymarket')
    table.add_column('Score')
    table.add_column('Method')
    for link in links[:limit]:
        table.add_row(
            link.hltv_match_id,
            link.hltv_match_title,
            link.polymarket_question,
            f'{link.score:.3f}',
            link.matched_by,
        )
    console.print(table)
    console.print(f'[cyan]Links found:[/cyan] {len(links[:limit])}')


@app.command()
def linked_dashboard(limit: int = 12, min_score: float = 0.68) -> None:
    views = _build_linked_market_views(min_score=min_score)[:limit]
    table = Table(title='html-ml linked dashboard')
    table.add_column('Status')
    table.add_column('Match')
    table.add_column('Moneyline')
    table.add_column('Move')
    table.add_column('Link')
    table.add_column('Live ctx')
    table.add_column('Momentum')
    table.add_column('Polymarket')

    for view in views:
        status = 'LIVE' if view.live else (view.time_text or '-')
        move_parts: list[str] = []
        if view.team_a_prev_price is not None:
            delta_a = view.team_a_price - view.team_a_prev_price
            if abs(delta_a) >= 0.0005:
                move_parts.append(f'{view.team_a} {delta_a:+.3f}')
        if view.team_b_prev_price is not None:
            delta_b = view.team_b_price - view.team_b_prev_price
            if abs(delta_b) >= 0.0005:
                move_parts.append(f'{view.team_b} {delta_b:+.3f}')
        live_ctx_parts: list[str] = []
        if view.current_map_name:
            live_ctx_parts.append(str(view.current_map_name))
        if view.round_score:
            live_ctx_parts.append(f'round {view.round_score}')
        if view.live_win_prob_team_a is not None and view.live_win_prob_team_b is not None:
            live_ctx_parts.append(f'wp {view.team_a} {view.live_win_prob_team_a:.1f}% / {view.team_b} {view.live_win_prob_team_b:.1f}%')
        momentum_parts: list[str] = []
        if view.team_a_momentum is not None:
            momentum_parts.append(f'{view.team_a} {view.team_a_momentum:+.3f}')
        if view.team_b_momentum is not None:
            momentum_parts.append(f'{view.team_b} {view.team_b_momentum:+.3f}')
        if view.market_bias:
            momentum_parts.append(f'bias {view.market_bias}')
        table.add_row(
            status,
            view.match_title,
            f'{view.team_a} {view.team_a_price:.3f} | {view.team_b} {view.team_b_price:.3f}',
            '; '.join(move_parts) if move_parts else '-',
            f'{view.link_score:.3f}',
            ' | '.join(live_ctx_parts) if live_ctx_parts else '-',
            ' | '.join(momentum_parts) if momentum_parts else '-',
            view.polymarket_question,
        )
    console.print(table)
    console.print(f'[cyan]Rows:[/cyan] {len(views)}')


@app.command()
def candidate_bets(limit: int = 10, min_link_score: float = 0.68) -> None:
    views = _build_linked_market_views(min_score=min_link_score)
    candidates = build_candidate_bets(views, min_link_score=min_link_score)[:limit]
    table = Table(title='Candidate Bets')
    table.add_column('Match')
    table.add_column('Pick')
    table.add_column('Price')
    table.add_column('Edge')
    table.add_column('Conf')
    table.add_column('Reason')
    for item in candidates:
        table.add_row(
            item.match_title,
            item.selection,
            f'{item.price:.3f}',
            f'{item.edge_score:.3f}',
            f'{item.confidence:.3f}',
            item.reason,
        )
    console.print(table)
    console.print(f'[cyan]Candidates:[/cyan] {len(candidates)}')


def _print_ai_bets(results: list) -> None:
    table = Table(title='AI Bets')
    table.add_column('Match')
    table.add_column('Action')
    table.add_column('Pick')
    table.add_column('Conf')
    table.add_column('Stake %')
    table.add_column('Summary')
    for item in results:
        action_style = {
            'BET': '[green]BET[/green]',
            'WATCH': '[yellow]WATCH[/yellow]',
            'PASS': '[dim]PASS[/dim]',
        }.get(item.action, item.action)
        table.add_row(
            item.match_title,
            action_style,
            item.selection or '-',
            f'{item.confidence:.2f}',
            f'{item.stake_fraction:.2%}',
            item.summary,
        )
    console.print(table)

    cards = []
    for item in results:
        lines: list[str] = []
        lines.append(f'[bold]{item.action}[/bold]  {item.selection or "-"}')
        lines.append(f'conf {item.confidence:.2f} • stake {item.stake_fraction:.2%}')
        lines.append('')
        for reason in (item.reasoning or [])[:4]:
            lines.append(f'• {reason}')
        if item.risk_flags:
            lines.append('')
            lines.append('[yellow]Risk:[/yellow] ' + '; '.join(item.risk_flags))
        if getattr(item, 'error', None):
            lines.append(f'[dim]LLM error: {item.error}[/dim]')
        border = 'green' if item.action == 'BET' else 'yellow' if item.action == 'WATCH' else 'dim'
        cards.append(Panel('\n'.join(lines), title=item.match_title, border_style=border))
    if cards:
        console.print(Columns(cards))


@app.command()
def ai_bets(
    limit: int = 5,
    min_link_score: float = 0.7,
    api_key: str = typer.Option('', help='Optional OpenRouter API key override for this run.'),
    model: str = typer.Option('', help='Optional OpenRouter model override.'),
) -> None:
    views = _build_linked_market_views(min_score=min_link_score)[:limit]
    analyst = MatchAnalyst(api_key=api_key or None, model=model or None)
    results = [analyst.analyze(view) for view in views]
    _print_ai_bets(results)


@app.command()
def live_match_test(
    limit: int = 5,
    wait_sec: int = 8,
    pages: int = 2,
    poll_cycles: int = 1,
    poll_interval_sec: int = 45,
    min_link_score: float = 0.72,
    api_key: str = typer.Option('', help='Optional OpenRouter API key override for this run.'),
    model: str = typer.Option('', help='Optional OpenRouter model override.'),
) -> None:
    _print_banner('html-ml live match test', 'Current live matches → linked markets → AI call')
    _print_step('Step 1/4', 'Collecting current live HLTV matches...')
    collect_hltv_matches(wait_sec=wait_sec, limit=max(limit * 2, 8))
    _print_step('Step 2/4', 'Refreshing Polymarket odds...')
    collect_polymarket(max_pages=pages)
    if poll_cycles > 1:
        _print_step('Step 3/4', f'Building short-term price history: {poll_cycles} cycles × {poll_interval_sec}s')
        with console.status('[bold cyan]Polling watchlist for momentum...[/bold cyan]', spinner='dots'):
            poll_watchlist(iterations=poll_cycles, interval_sec=poll_interval_sec, limit=max(limit * 2, 8), max_pages=pages)
    else:
        _print_step('Step 3/4', 'Skipping extra polling, using current snapshots only')

    _print_step('Step 4/4', 'Building live linked shortlist and running AI analysis...')
    all_views = _build_linked_market_views(min_score=min_link_score)
    live_views = [view for view in all_views if view.live][:limit]

    table = Table(title='Current live linked matches')
    table.add_column('Match')
    table.add_column('Moneyline')
    table.add_column('Live ctx')
    table.add_column('Momentum')
    table.add_column('Link')
    for view in live_views:
        table.add_row(
            view.match_title,
            f'{view.team_a} {view.team_a_price:.3f} | {view.team_b} {view.team_b_price:.3f}',
            _compact_live_context(view),
            _compact_momentum(view),
            f'{view.link_score:.3f}',
        )
    console.print(table)

    analyst = MatchAnalyst(api_key=api_key or None, model=model or None)
    results = [analyst.analyze(view) for view in live_views]
    _print_ai_bets(results)

    next_steps = Panel(
        '• Save this snapshot for 1–3 live matches\n'
        '• Re-run in 5–10 minutes or use poll_cycles > 1\n'
        '• Compare AI action changes vs price and live probability\n'
        '• Mark each read as good / neutral / bad',
        title='How to test right now',
        border_style='green',
    )
    console.print(next_steps)


@app.command()
def live_bets(
    hltv_limit: int = 20,
    pages: int = 5,
    linked_limit: int = 10,
    ai_limit: int = 5,
    wait_sec: int = 8,
    min_link_score: float = 0.7,
    api_key: str = typer.Option('', help='Optional OpenRouter API key override for this run.'),
    model: str = typer.Option('', help='Optional OpenRouter model override.'),
) -> None:
    console.print('[bold cyan]Step 1/4[/bold cyan] Collecting HLTV matches...')
    collect_hltv_matches(wait_sec=wait_sec, limit=hltv_limit)

    console.print('\n[bold cyan]Step 2/4[/bold cyan] Collecting Polymarket odds...')
    collect_polymarket(max_pages=pages)

    console.print('\n[bold cyan]Step 3/4[/bold cyan] Building linked dashboard...')
    linked_dashboard(limit=linked_limit, min_score=min_link_score)

    console.print('\n[bold cyan]Step 4/4[/bold cyan] Running AI analysis...')
    views = _build_linked_market_views(min_score=min_link_score)[:ai_limit]
    analyst = MatchAnalyst(api_key=api_key or None, model=model or None)
    results = [analyst.analyze(view) for view in views]
    _print_ai_bets(results)

    bet_count = sum(1 for item in results if item.action == 'BET')
    watch_count = sum(1 for item in results if item.action == 'WATCH')
    pass_count = sum(1 for item in results if item.action == 'PASS')
    console.print('\n[bold green]Summary[/bold green]')
    console.print(f'• Linked matches analyzed: {len(views)}')
    console.print(f'• BET: {bet_count}')
    console.print(f'• WATCH: {watch_count}')
    console.print(f'• PASS: {pass_count}')


@app.command()
def print_config() -> None:
    from html_ml.config import settings

    console.print_json(json.dumps(settings.model_dump(), default=str))


if __name__ == '__main__':
    app()
