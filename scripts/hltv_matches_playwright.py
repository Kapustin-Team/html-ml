from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://www.hltv.org/matches')
    parser.add_argument('--wait-sec', type=int, default=12)
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

            cards = page.locator('.match-wrapper[data-match-id]')
            count = cards.count()
            matches = []
            seen_ids = set()
            for idx in range(count):
                card = cards.nth(idx)
                match_id = card.get_attribute('data-match-id')
                href = None
                link_loc = card.locator('a[href*="/matches/"]').first
                if link_loc.count() > 0:
                    href = link_loc.get_attribute('href')

                team_names = card.locator('.match-teamname')
                team1 = None
                team2 = None
                if team_names.count() >= 2:
                    team1 = team_names.nth(0).inner_text().strip()
                    team2 = team_names.nth(1).inner_text().strip()

                event_name = None
                event_loc = card.locator('.match-event .text-ellipsis').first
                if event_loc.count() > 0:
                    event_name = event_loc.inner_text().strip()

                format_text = None
                format_loc = card.locator('.match-meta').first
                if format_loc.count() > 0:
                    format_text = format_loc.inner_text().strip()

                time_text = None
                time_loc = card.locator('.match-time, .match-meta-live').first
                if time_loc.count() > 0:
                    time_text = time_loc.inner_text().strip()

                live = (card.get_attribute('live') or 'false').lower() == 'true'
                stars = card.get_attribute('data-stars')
                if not event_name:
                    event_alt = card.locator('.match-event').first
                    if event_alt.count() > 0:
                        raw_event = event_alt.inner_text().strip().splitlines()
                        if raw_event:
                            event_name = raw_event[0].strip() or None

                if team1 and team2 and match_id and match_id not in seen_ids:
                    seen_ids.add(match_id)
                    matches.append(
                        {
                            'match_id': match_id,
                            'href': href,
                            'team1': team1,
                            'team2': team2,
                            'event_name': event_name,
                            'format': format_text,
                            'time_text': time_text,
                            'live': live,
                            'stars': int(stars) if stars and stars.isdigit() else None,
                        }
                    )

            payload = {
                'ok': True,
                'url': args.url,
                'title': page.title(),
                'count': len(matches),
                'matches': matches,
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
