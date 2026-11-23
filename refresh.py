"""Refresh the numbers shown on the profile card.

Reads this account's public contribution calendar from GitHub and writes
card.json. Any token works, because the calendar is what the profile page
already shows; the scheduled workflow uses its own.

    GH_TOKEN=$(gh auth token) python3 refresh.py
    python3 tools/build_card.py

All or nothing: on any failure card.json is left as it was and the exit code
is 1, so the card never shows a half-fresh set of numbers. Stdlib only.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOGIN = "SatoshiSarti"
CARD_PATH = ROOT / "card.json"

QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


class RefreshError(RuntimeError):
    pass


def fetch_calendar():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise RefreshError("set GITHUB_TOKEN or GH_TOKEN")
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-card"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            reply = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        raise RefreshError(f"GitHub: {error}") from error
    try:
        user = reply["data"]["user"]
        calendar = user["contributionsCollection"]["contributionCalendar"]
        weeks = [
            {
                "start": week["contributionDays"][0]["date"],
                "days": [day["contributionCount"] for day in week["contributionDays"]],
            }
            for week in calendar["weeks"]
        ]
        last_day = calendar["weeks"][-1]["contributionDays"][-1]["date"]
        return {
            "createdAt": user["createdAt"],
            "total": calendar["totalContributions"],
            "lastDay": last_day,
            "weeks": weeks,
        }
    except (KeyError, TypeError, IndexError) as error:
        raise RefreshError(f"unexpected GitHub reply: {str(reply)[:300]}") from error


def main():
    try:
        card = fetch_calendar()
    except RefreshError as error:
        print(f"refresh failed, card left as it was: {error}", file=sys.stderr)
        return 1
    if len(card["weeks"]) < 26:
        print("refresh failed, card left as it was: calendar too short", file=sys.stderr)
        return 1
    card["refreshedAt"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    CARD_PATH.write_text(json.dumps(card) + "\n", encoding="utf-8")
    print(f'{card["total"]} contributions through {card["lastDay"]}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
