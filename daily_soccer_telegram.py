"""Sends you today's soccer fixtures on Telegram (pretty version).

Setup:
  pip install requests tzdata
  Environment variables:
    TELEGRAM_BOT_TOKEN  - token from @BotFather
    TELEGRAM_CHAT_ID    - your chat id
    API_FOOTBALL_KEY    - free key from dashboard.api-football.com
Run once per day (Task Scheduler / GitHub Actions).
Uses only 1 API request per run (free plan allows 100/day).
"""
import os
from collections import defaultdict
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

import requests

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "PASTE_TOKEN_HERE")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "PASTE_CHAT_ID_HERE")
API_KEY = os.environ.get("API_FOOTBALL_KEY", "PASTE_API_KEY_HERE")

TIMEZONE = "America/New_York"  # Boston uses this zone (there is no America/Boston)
TZ_LABEL = "Boston time"  # text shown in the message header

# League ID: (name, emoji). Verify IDs with GET /leagues?search=<name>
LEAGUES = {
    39: ("Premier League", "🇬🇧"),
    140: ("La Liga", "🇪🇸"),
    203: ("Süper Lig", "🇹🇷"),
    1: ("World Cup", "🏆"),
    4: ("Euros", "🏆"),
    5: ("Nations League", "🌍"),
}

# National teams whose matches are always shown, in ANY competition
# (friendlies, qualifiers...). Add more names like "Germany" if you want.
NATIONAL_TEAMS = {"Turkey", "Türkiye"}


def get_fixtures(day: str) -> list:
    resp = requests.get(
        "https://v3.football.api-sports.io/fixtures",
        headers={"x-apisports-key": API_KEY},
        params={"date": day, "timezone": TIMEZONE},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("errors"):
        raise RuntimeError(f"API error: {data['errors']}")
    return data["response"]


def build_message(fixtures: list, day: str) -> str:
    pretty_day = datetime.strptime(day, "%Y-%m-%d").strftime("%A, %B %d")
    header = f"⚽ <b>Today's Matches</b>\n📅 {pretty_day} · 🕒 {TZ_LABEL}"
    order = {lid: i for i, lid in enumerate(LEAGUES)}

    groups = defaultdict(list)  # (sort order, title, emoji) -> matches
    for f in fixtures:
        lid = f["league"]["id"]
        home, away = f["teams"]["home"]["name"], f["teams"]["away"]["name"]
        if lid in LEAGUES:
            name, emoji = LEAGUES[lid]
            key = (order[lid], name, emoji)
        elif home in NATIONAL_TEAMS or away in NATIONAL_TEAMS:
            key = (99, f["league"]["name"], "🇹🇷")
        else:
            continue
        kickoff = datetime.fromisoformat(f["fixture"]["date"]).strftime("%H:%M")
        line = f"<code>{kickoff}</code>  {escape(home)} 🆚 {escape(away)}"
        groups[key].append((kickoff, line))

    if not groups:
        return header + "\n\n😴 No matches today."

    blocks = [header]
    for (_, name, emoji), matches in sorted(groups.items()):
        lines = [line for _, line in sorted(matches)]
        blocks.append(f"{emoji} <b>{escape(name)}</b>\n" + "\n".join(lines))
    return "\n\n".join(blocks)


def send_telegram(text: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(
        url,
        json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
        timeout=15,
    )
    r.raise_for_status()


if __name__ == "__main__":
    today = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d")
    message = build_message(get_fixtures(today), today)
    print(message)
    send_telegram(message)
