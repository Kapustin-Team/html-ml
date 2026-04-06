from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://www.hltv.org/matches')
    parser.add_argument('--wait-sec', type=int, default=15)
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
            title = page.title()
            body = page.locator('body').inner_text()[:5000]
            payload = {
                'ok': True,
                'url': args.url,
                'title': title,
                'body_excerpt': body,
                'contains_cloudflare': 'Just a moment' in title or 'Checking your browser' in body,
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
