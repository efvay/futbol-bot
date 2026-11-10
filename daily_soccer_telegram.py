"""Sends you today's soccer fixtures on Telegram.

Setup:
  pip install requests
  Environment variables:
    TELEGRAM_BOT_TOKEN  - token from @BotFather
    TELEGRAM_CHAT_ID    - your chat id
    API_FOOTBALL_KEY    - free key from dashboard.api-football.com
Run once per day (cron / Task Scheduler / GitHub Actions).
Uses only 1 API request per run (free plan allows 100/day).
"""
import os
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "PASTE_TOKEN_HERE")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "PASTE_CHAT_ID_HERE")
API_KEY = os.environ.get("API_FOOTBALL_KEY", "PASTE_API_KEY_HERE")

TIMEZONE = "America/New_York"  # times in the message use this zone

# League IDs from API-Football. Verify with GET /leagues?search=<name>
# because IDs can differ from what I list here.
LEAGUES = {
    39: "Premier League",
    140: "La Liga",
    
    
    203: "Turkish Super Lig",
    2: "UEFA Champions League",
    3: "UEFA Europa League",
    848: "UEFA Conference League",
    5: "UEFA Nations League",
    1: "World Cup",
    4: "Euros",
    32: "World Cup Qualifiers (Europe)",
    10: "International Friendlies",
}


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
    by_league = defaultdict(list)
    for f in fixtures:
        lid = f["league"]["id"]
        if lid in LEAGUES:
            kickoff = datetime.fromisoformat(f["fixture"]["date"]).strftime("%H:%M")
            line = f"{kickoff}  {f['teams']['home']['name']} vs {f['teams']['away']['name']}"
            by_league[lid].append((kickoff, line))

    if not by_league:
        return f"No matches in your selected competitions today ({day})."

    parts = [f"Soccer today ({day}, {TIMEZONE})"]
    for lid, name in LEAGUES.items():  # keeps your priority order
        if lid in by_league:
            parts.append(f"\n{name}")
            parts.extend(line for _, line in sorted(by_league[lid]))
    return "\n".join(parts)


def send_telegram(text: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    # Telegram messages max out at 4096 characters, so split if needed.
    for i in range(0, len(text), 4000):
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": text[i:i + 4000]}, timeout=15)
        r.raise_for_status()


if __name__ == "__main__":
    today = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d")
    
    message = build_message(get_fixtures(today), today)
    print(message)
    send_telegram(message)

