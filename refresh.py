"""Refresh the numbers shown on the profile card.

MyFutureSelf traction comes from the public snapshot at
kayahickin.com/api/profile-metrics, the same feed the CTO's card reads. The
contribution count is the one GitHub shows on the profile, read with whatever
token is in GITHUB_TOKEN or GH_TOKEN; the workflow's own token is enough.

The refresh is all or nothing. A missing token, an unreachable feed or a
snapshot older than PROFILE_SITE_MAX_AGE_HOURS leaves card.json untouched and
exits 1, so the card never mixes fresh and stale numbers.

Stdlib only. Run tools/build_card.py afterwards to redraw the cards.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOGIN = "SatoshiSarti"
METRICS_URL = os.environ.get(
    "PROFILE_METRICS_URL", "https://kayahickin.com/api/profile-metrics"
)
SITE_MAX_AGE_HOURS = int(os.environ.get("PROFILE_SITE_MAX_AGE_HOURS", "48"))
CARD_PATH = ROOT / "card.json"
HISTORY_PATH = ROOT / "metrics_history.json"
HISTORY_DAYS = 400

RAW_METRICS = (
    "appDownloads",
    "appStoreRating",
    "appStoreReviews",
    "futureSelfActions",
    "paidSubscribers",
)
DISPLAY_METRICS = ("arr",)


class RefreshError(RuntimeError):
    pass


def fetch_json(url, payload=None, token=None):
    headers = {"User-Agent": "profile-card", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"bearer {token}"
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        raise RefreshError(f"{url}: {error}") from error


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def product_metrics(now):
    snapshot = fetch_json(METRICS_URL)
    generated_at = snapshot.get("generatedAt")
    metrics = snapshot.get("metrics") or {}
    if not generated_at:
        raise RefreshError("product snapshot has no generatedAt")
    age = now - parse_time(generated_at)
    if age > timedelta(hours=SITE_MAX_AGE_HOURS):
        raise RefreshError(f"product snapshot is {age} old")
    for name in RAW_METRICS:
        if not isinstance((metrics.get(name) or {}).get("raw"), (int, float)):
            raise RefreshError(f"product snapshot is missing {name}.raw")
    for name in DISPLAY_METRICS:
        if not (metrics.get(name) or {}).get("display"):
            raise RefreshError(f"product snapshot is missing {name}.display")
    return generated_at, {
        "downloads": f"{round(metrics['appDownloads']['raw']):,}",
        "paid": f"{round(metrics['paidSubscribers']['raw']):,}",
        "arr": metrics["arr"]["display"],
        "actions": f"{round(metrics['futureSelfActions']['raw']):,}",
        "rating": f"{metrics['appStoreRating']['raw']:.1f}",
        "reviews": f"{round(metrics['appStoreReviews']['raw']):,}",
    }, round(metrics["appDownloads"]["raw"])


def contributions():
    """Contributions in the last year, as the profile's own graph counts them."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise RefreshError("set GITHUB_TOKEN or GH_TOKEN to read contributions")
    query = (
        "query($login: String!) { user(login: $login) { contributionsCollection "
        "{ contributionCalendar { totalContributions } } } }"
    )
    reply = fetch_json(
        "https://api.github.com/graphql",
        {"query": query, "variables": {"login": LOGIN}},
        token,
    )
    try:
        total = reply["data"]["user"]["contributionsCollection"][
            "contributionCalendar"]["totalContributions"]
    except (KeyError, TypeError) as error:
        raise RefreshError(f"unexpected GitHub reply: {reply}") from error
    return f"{total:,}"


def record_history(generated_at, downloads):
    """Keep one downloads point per day, for the card's trend line."""
    history = {"downloads": []}
    if HISTORY_PATH.exists():
        history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    day = parse_time(generated_at).date().isoformat()
    points = {point["date"]: point["value"] for point in history.get("downloads", [])}
    points[day] = downloads
    kept = sorted(points.items())[-HISTORY_DAYS:]
    history["downloads"] = [{"date": d, "value": v} for d, v in kept]
    HISTORY_PATH.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")


def main():
    now = datetime.now(timezone.utc)
    try:
        generated_at, stats, downloads = product_metrics(now)
        stats["contributions"] = contributions()
    except RefreshError as error:
        print(f"refresh failed, card left as it was: {error}", file=sys.stderr)
        return 1
    record_history(generated_at, downloads)
    card = {
        "stats": stats,
        "metricsGeneratedAt": generated_at,
        "refreshedAt": now.isoformat().replace("+00:00", "Z"),
    }
    CARD_PATH.write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(card, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
