"""
was testing betclic with this odds api with betclic doesnt give data for 2026 january from what i got
"""
import os
import json
import requests
from dotenv import load_dotenv

BASE_URL = "https://api.odds-api.io/v3"


def load_key() -> str:
    # Load backend/.env explicitly (avoids python-dotenv stdin edge cases)
    here = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(dotenv_path=os.path.join(here, ".env"))

    api_key = os.getenv("ODDS_API_KEY")
    if not api_key:
        raise SystemExit("ODDS_API_KEY missing (set it in backend/.env)")
    return api_key


def fetch_events(api_key: str, start_iso: str, end_iso: str) -> list[dict]:
    params = {
        "apiKey": api_key,
        "sport": "basketball",
        "league": "usa-nba",
        "from": start_iso,
        "to": end_iso,
    }
    r = requests.get(f"{BASE_URL}/historical/events", params=params, timeout=30)
    print("events status:", r.status_code)
    r.raise_for_status()

    payload = r.json()
    if isinstance(payload, dict) and "data" in payload:
        events = payload.get("data") or []
    elif isinstance(payload, list):
        events = payload
    else:
        events = []

    print("events count:", len(events))
    if events:
        print("first event (preview):")
        print(json.dumps(events[0], indent=2)[:2000])
    return events


def fetch_betclic_only_odds(api_key: str, event_id: int) -> dict:
    params = {
        "apiKey": api_key,
        "eventId": event_id,
        "bookmakers": "betclic",
    }
    r = requests.get(f"{BASE_URL}/historical/odds", params=params, timeout=30)
    print("odds status:", r.status_code)
    r.raise_for_status()

    payload = r.json()
    bms = payload.get("bookmakers") if isinstance(payload, dict) else None
    keys = list((bms or {}).keys()) if isinstance(bms, dict) else None
    print("bookmakers keys:", keys)

    print("odds json (preview):")
    print(json.dumps(payload, indent=2)[:5000])
    return payload


if __name__ == "__main__":
    api_key = load_key()

    start = "2026-01-15T00:00:00Z"
    end = "2026-01-15T23:59:59Z"

    events = fetch_events(api_key, start, end)
    if not events:
        raise SystemExit("No events returned for the selected window.")

    event_id = events[0].get("id")
    print("chosen event_id:", event_id)

    fetch_betclic_only_odds(api_key, event_id)