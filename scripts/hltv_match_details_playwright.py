from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright


def extract_first(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else None


def extract_match_state(text: str) -> dict:
    map_name = extract_first(r'R:\s*\d+\s*-\s*([A-Za-z0-9_\-]+)', text)
    map_index_match = re.search(r'R:\s*(\d+)\s*-', text, flags=re.IGNORECASE)
    map_index = int(map_index_match.group(1)) if map_index_match else None

    live_block_match = re.search(
        r'R:\s*\d+\s*-\s*[A-Za-z0-9_\-]+\s*(\d+)\s*:\s*(\d+)\s*([0-9]+:[0-9]+)',
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    score_team_a = int(live_block_match.group(1)) if live_block_match else None
    score_team_b = int(live_block_match.group(2)) if live_block_match else None
    round_timer = live_block_match.group(3) if live_block_match else None

    score_match = re.search(r'Round over - Winner: (CT|T) \((\d+)\s*-\s*(\d+)\)', text, flags=re.IGNORECASE)
    if score_match:
        score_team_a = int(score_match.group(2))
        score_team_b = int(score_match.group(3))
    round_winner_side = score_match.group(1).upper() if score_match else None

    probability_match = re.search(
        r'Live win probability\s*([0-9]+(?:\.[0-9]+)?)%\s*OT\s*([0-9]+(?:\.[0-9]+)?)%\s*([0-9]+(?:\.[0-9]+)?)%',
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    live_win_probabilities = None
    if probability_match:
        live_win_probabilities = {
            'team_a': float(probability_match.group(1)),
            'ot': float(probability_match.group(2)),
            'team_b': float(probability_match.group(3)),
        }

    return {
        'current_map_name': map_name,
        'map_index': map_index,
        'score_team_a': score_team_a,
        'score_team_b': score_team_b,
        'round_timer': round_timer,
        'round_winner_side': round_winner_side,
        'live_win_probabilities': live_win_probabilities,
        'has_live_score': score_team_a is not None and score_team_b is not None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--wait-sec', type=int, default=10)
    parser.add_argument('--output', default='-')
    args = parser.parse_args()

    payload: dict
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                args=['--disable-blink-features=AutomationControlled', '--window-size=1920,1080'],
            )
            page = browser.new_page()
            page.goto(args.url, wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(args.wait_sec * 1000)
            text = page.locator('body').inner_text()
            title = page.title()
            payload = {
                'ok': True,
                'url': args.url,
                'title': title,
                'state': extract_match_state(text),
                'snippet': text[:4000],
            }
            browser.close()
    except Exception as exc:
        payload = {'ok': False, 'url': args.url, 'error': str(exc)}

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output == '-':
        print(text)
    else:
        Path(args.output).write_text(text, encoding='utf-8')
        print(args.output)
    return 0 if payload.get('ok') else 1


if __name__ == '__main__':
    raise SystemExit(main())
