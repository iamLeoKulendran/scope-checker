#!/usr/bin/env python3
"""
Scope Cinemas showtime availability checker.

Checks whether a target date's showtimes have opened for booking for a
given movie, and sends a free push notification via ntfy.sh when found.

Setup:
    pip install playwright
    playwright install chromium --with-deps

Usage:
    python3 check_scope.py
"""

import json
import os
import sys
import urllib.request

# ---- CONFIG: edit these ----
MOVIE_URL = "https://www.scopecinemas.com/movies/the-odyssey/showtimes"
TARGET_DATE_LABEL = "Jul25"          # as it appears on the date tabs, e.g. "Jul25Sat"

# ntfy is optional - leave as None to skip it and use Telegram only.
NTFY_TOPIC = None  # e.g. "scope-odyssey-jul25-xy9k" - set this to enable ntfy

# Telegram is optional - leave these as None to skip it and use ntfy only.
# Set as GitHub repo Secrets (never hardcode a real token in the file itself).
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
# -----------------------------


def page_contains_target_date() -> bool:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        # "load" fires once and reliably; "networkidle" can hang forever on sites
        # with persistent background connections (analytics, chat widgets, etc).
        page.goto(MOVIE_URL, wait_until="load", timeout=45000)
        # The date tabs are rendered client-side after load, so give the JS
        # a few seconds to finish before reading the page content.
        page.wait_for_timeout(5000)
        content = page.content()
        browser.close()
        return TARGET_DATE_LABEL in content


def notify_ntfy(message: str) -> None:
    if not NTFY_TOPIC:
        return  # ntfy not configured - skip silently
    req = urllib.request.Request(
        url=f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={"Title": "Scope Cinemas booking open!"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=15)


def notify_telegram(message: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return  # Telegram not configured - skip silently
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": message}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    urllib.request.urlopen(req, timeout=15)


def notify(message: str) -> None:
    notify_ntfy(message)
    notify_telegram(message)


def main() -> None:
    try:
        found = page_contains_target_date()
    except Exception as e:
        print(f"Check failed: {e}", file=sys.stderr)
        sys.exit(1)

    if found:
        notify(f"{TARGET_DATE_LABEL} showtimes are open for booking: {MOVIE_URL}")
        print(f"{TARGET_DATE_LABEL} is available — notification sent.")
    else:
        print(f"{TARGET_DATE_LABEL} not open yet.")


if __name__ == "__main__":
    main()
