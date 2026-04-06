from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://www.hltv.org/matches')
    parser.add_argument('--wait-sec', type=int, default=15)
    parser.add_argument('--output', default='-')
    args = parser.parse_args()

    try:
        import undetected_chromedriver as uc
    except Exception as exc:  # pragma: no cover
        print(json.dumps({'ok': False, 'error': f'failed to import undetected_chromedriver: {exc}'}))
        return 1

    options = uc.ChromeOptions()
    options.binary_location = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--lang=en-US')
    options.add_argument('--disable-blink-features=AutomationControlled')

    driver = None
    try:
        driver = uc.Chrome(options=options, use_subprocess=True, headless=False, driver_executable_path='/opt/homebrew/bin/chromedriver')
        driver.get(args.url)
        time.sleep(args.wait_sec)
        title = driver.title
        body = driver.find_element('tag name', 'body').text[:5000]
        payload = {
            'ok': True,
            'url': args.url,
            'title': title,
            'body_excerpt': body,
            'contains_cloudflare': 'Just a moment' in title or 'Checking your browser' in body,
        }
    except Exception as exc:  # pragma: no cover
        payload = {'ok': False, 'url': args.url, 'error': str(exc)}
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output == '-':
        print(text)
    else:
        Path(args.output).write_text(text, encoding='utf-8')
        print(args.output)
    return 0 if payload.get('ok') else 1


if __name__ == '__main__':
    raise SystemExit(main())
