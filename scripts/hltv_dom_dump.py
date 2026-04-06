from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright


OUT = Path('/tmp/hltv_dom_dump.json')

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        args=['--disable-blink-features=AutomationControlled', '--window-size=1920,1080'],
    )
    page = browser.new_page()
    page.goto('https://www.hltv.org/matches', wait_until='domcontentloaded', timeout=60000)
    page.wait_for_timeout(10000)

    selectors = [
        'a',
        '.match-wrapper',
        '.matchCard',
        '.match-card',
        '.upcomingMatch',
        '.liveMatch',
        '.matches-listing a',
        '.matchList a',
        '[class*="match"]',
    ]

    result = {'title': page.title(), 'samples': {}}
    for sel in selectors:
        loc = page.locator(sel)
        count = loc.count()
        samples = []
        for i in range(min(count, 8)):
            item = loc.nth(i)
            try:
                samples.append(
                    {
                        'html': item.evaluate('(el) => el.outerHTML').replace('\n', ' ')[:2000],
                        'text': item.inner_text()[:500],
                    }
                )
            except Exception as exc:
                samples.append({'error': str(exc)})
        result['samples'][sel] = {'count': count, 'items': samples}

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    browser.close()

print(str(OUT))
