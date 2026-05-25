"""
fetch_current_odds.py — Fetch live NBA odds via /odds/multi (10 events/call)
Runs every hour to catch new events and odds movements
"""

import logging
import hashlib
import requests
from datetime import datetime, date, timedelta
from app.config import ODDS_API_KEY, BOOKMAKERS as CONFIG_BOOKMAKERS
from app.constants import TEAM_ABBREVIATIONS as TEAM_MAP
from app.db.database import SessionLocal
from app.db.models import Game, Odds

logger = logging.getLogger(__name__)

BASE = "https://api.odds-api.io/v3"
BOOKMAKERS = CONFIG_BOOKMAKERS

NBA_LEAGUE = "usa-nba"
EVENT_LOOKAHEAD_DAYS = 21


def extract_moneyline(market_list: list, bookmaker: str) -> tuple:
    for market in market_list or []:
        name = (market.get("name") or "").strip().lower()
        if any(k in name for k in ("1q", "2q", "3q", "4q", "quarter", "ht", "2h")):
            continue
        odds_list = market.get("odds") or []
        if not odds_list:
            continue
        if name in ("ml", "moneyline"):
            o = odds_list[0]
            return float(o.get("home", 0)) or None, float(o.get("away", 0)) or None
        if name == "3-way result":
            o = odds_list[0]
            return float(o.get("home", 0)) or None, float(o.get("away", 0)) or None
    return None, None


def derive_season(game_date: date) -> str:
    y = game_date.year
    return f"{y}-{str(y+1)[-2:]}" if game_date.month >= 10 else f"{y-1}-{str(y)[-2:]}"


def fetch_nba_events() -> dict:
    """Load NBA events (upcoming + recent) keyed by event id."""
    if not ODDS_API_KEY:
        logger.error("ODDS_API_KEY not set")
        return {}

    now = datetime.utcnow()
    start = (now - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
    end = (now + timedelta(days=EVENT_LOOKAHEAD_DAYS)).strftime("%Y-%m-%dT23:59:59Z")

    all_events = {}
    try:
        resp = requests.get(
            f"{BASE}/events",
            params={
                "apiKey": ODDS_API_KEY,
                "sport": "basketball",
                "league": NBA_LEAGUE,
                "from": start,
                "to": end,
                "limit": 200,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            logger.warning("NBA /events returned %s: %s", resp.status_code, resp.text[:200])
            return {}
        data = resp.json()
        events = data if isinstance(data, list) else data.get("data", data.get("events", []))
        for ev in events or []:
            eid = str(ev.get("id", ""))
            home_full = ev.get("home", "")
            away_full = ev.get("away", "")
            if not eid or not TEAM_MAP.get(home_full) or not TEAM_MAP.get(away_full):
                continue
            all_events[eid] = ev
    except Exception as e:
        logger.error("Failed to fetch NBA events: %s", e)

    return all_events


def fetch_and_store():
    if not ODDS_API_KEY:
        logger.error("ODDS_API_KEY not set")
        return

    if not BOOKMAKERS:
        logger.error("BOOKMAKERS env is empty — set e.g. BOOKMAKERS=Superbet,Stake on Railway")
        return

    session = SessionLocal()

    all_events = fetch_nba_events()
    if not all_events:
        logger.info("No NBA events found for current window")
        session.close()
        return

    logger.info("Found %s NBA events (bookmakers: %s)", len(all_events), BOOKMAKERS)

    event_ids = list(all_events.keys())
    batches = [event_ids[i : i + 10] for i in range(0, len(event_ids), 10)]
    bookmakers_param = ",".join(BOOKMAKERS)

    odds_map = {}
    for batch in batches:
        try:
            resp = requests.get(
                f"{BASE}/odds/multi",
                params={
                    "apiKey": ODDS_API_KEY,
                    "eventIds": ",".join(batch),
                    "bookmakers": bookmakers_param,
                },
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning(
                    "/odds/multi returned %s: %s", resp.status_code, resp.text[:200]
                )
                continue
            data = resp.json()
            items = (
                data
                if isinstance(data, list)
                else [data]
                if isinstance(data, dict) and data.get("id")
                else data.get("data", data.get("odds", []))
            )
            for item in items or []:
                eid = str(item.get("id", ""))
                bms = item.get("bookmakers", {})
                if eid and bms:
                    odds_map[eid] = bms
        except Exception as e:
            logger.warning("odds/multi batch failed: %s", e)

    logger.info("Events with odds from API: %s / %s", len(odds_map), len(all_events))

    created_games = 0
    created_odds = 0
    updated_odds = 0
    skipped_no_ml = 0

    for eid, bms in odds_map.items():
        ev = all_events[eid]
        home_full = ev.get("home", "")
        away_full = ev.get("away", "")
        home_code = TEAM_MAP.get(home_full)
        away_code = TEAM_MAP.get(away_full)
        if not home_code or not away_code:
            continue
        date_str = ev.get("date", "")
        try:
            game_date = (
                datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
                if date_str
                else date.today()
            )
        except Exception:
            continue

        season = derive_season(game_date)
        game_id = "ODDS" + hashlib.md5(eid.encode()).hexdigest()[:12]

        game = session.query(Game).filter(Game.game_id == game_id).first()
        if not game:
            game = Game(
                game_id=game_id,
                game_date=game_date,
                season=season,
                home_team=home_code,
                away_team=away_code,
                home_score=None,
                away_score=None,
                home_team_wins=None,
            )
            session.add(game)
            session.flush()
            created_games += 1

        for bm in BOOKMAKERS:
            markets = bms.get(bm, [])
            ho, ao = extract_moneyline(markets, bm)
            if not ho or not ao:
                skipped_no_ml += 1
                continue
            existing = (
                session.query(Odds)
                .filter(Odds.game_id == game_id, Odds.bookmaker == bm)
                .first()
            )
            if existing:
                if existing.home_win_odds != ho or existing.away_win_odds != ao:
                    existing.home_win_odds = ho
                    existing.away_win_odds = ao
                    updated_odds += 1
            else:
                session.add(
                    Odds(
                        game_id=game_id,
                        bookmaker=bm,
                        home_win_odds=ho,
                        away_win_odds=ao,
                    )
                )
                created_odds += 1

    session.commit()
    session.close()
    logger.info(
        "Current odds done: %s games created, %s odds created, %s updated, %s missing ML",
        created_games,
        created_odds,
        updated_odds,
        skipped_no_ml,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetch_and_store()
