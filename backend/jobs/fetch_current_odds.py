"""
fetch_current_odds.py — Fetch live odds via /odds/multi (10 events/call)
Runs every hour to catch new events and odds movements
"""

import logging
import hashlib
import requests
from datetime import datetime, date
from app.config import ODDS_API_KEY, BOOKMAKERS as CONFIG_BOOKMAKERS
from app.db.database import SessionLocal
from app.db.models import Game, Odds

logger = logging.getLogger(__name__)

BASE = "https://api.odds-api.io/v3"
BOOKMAKERS = CONFIG_BOOKMAKERS

TEAM_MAP = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "LA Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP", "New York Knicks": "NYK", "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC", "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR", "Utah Jazz": "UTA", "Washington Wizards": "WAS",
}

SPORTS = ["basketball"]


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
        if name == "3-way result" and bookmaker == "STS PL":
            o = odds_list[0]
            return float(o.get("home", 0)) or None, float(o.get("away", 0)) or None
    return None, None


def derive_season(game_date: date) -> str:
    y = game_date.year
    return f"{y}-{str(y+1)[-2:]}" if game_date.month >= 10 else f"{y-1}-{str(y)[-2:]}"


def fetch_and_store():
    if not ODDS_API_KEY:
        logger.error("ODDS_API_KEY not set")
        return

    session = SessionLocal()

    # 1. Collect events from multiple sports
    all_events = {}
    for sport in SPORTS:
        try:
            resp = requests.get(f"{BASE}/events", params={"apiKey": ODDS_API_KEY, "sport": sport, "limit": 50}, timeout=10)
            if resp.status_code != 200:
                continue
            data = resp.json()
            evs = data if isinstance(data, list) else [data] if isinstance(data, dict) and data.get("id") else []
            for ev in evs:
                eid = str(ev.get("id", ""))
                if eid and eid not in all_events:
                    ev["_sport"] = sport
                    all_events[eid] = ev
        except Exception:
            pass

    if not all_events:
        logger.info("No current events found")
        session.close()
        return

    logger.info(f"Found {len(all_events)} current events")

    # 2. Batch-fetch odds via /odds/multi (10 events/call)
    event_ids = list(all_events.keys())
    batches = [event_ids[i:i+10] for i in range(0, len(event_ids), 10)]

    odds_map = {}
    for batch in batches:
        try:
            resp = requests.get(
                f"{BASE}/odds/multi",
                params={"apiKey": ODDS_API_KEY, "eventIds": ",".join(batch)},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                items = data if isinstance(data, list) else [data] if isinstance(data, dict) and data.get("id") else []
                for item in items:
                    eid = str(item.get("id", ""))
                    bms = item.get("bookmakers", {})
                    if eid and bms:
                        odds_map[eid] = bms
        except Exception:
            pass

    logger.info(f"Events with our bookmakers: {len(odds_map)}")

    # 3. Store in DB
    updated = 0
    created = 0
    for eid, bms in odds_map.items():
        ev = all_events[eid]
        home_full = ev.get("home", "")
        away_full = ev.get("away", "")
        date_str = ev.get("date", "")
        home_code = TEAM_MAP.get(home_full, home_full)[:10]
        away_code = TEAM_MAP.get(away_full, away_full)[:10]
        try:
            game_date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date() if date_str else date.today()
        except Exception:
            continue
        season = derive_season(game_date)
        game_id = "ODDS" + hashlib.md5(eid.encode()).hexdigest()[:12]

        game = session.query(Game).filter(Game.game_id == game_id).first()
        if not game:
            game = Game(game_id=game_id, game_date=game_date, season=season,
                        home_team=home_code, away_team=away_code,
                        home_score=None, away_score=None, home_team_wins=None)
            session.add(game)
            session.flush()
            created += 1

        for bm in BOOKMAKERS:
            markets = bms.get(bm, [])
            ho, ao = extract_moneyline(markets, bm)
            if not ho or not ao:
                continue
            existing = session.query(Odds).filter(Odds.game_id == game_id, Odds.bookmaker == bm).first()
            if existing:
                if existing.home_win_odds != ho or existing.away_win_odds != ao:
                    existing.home_win_odds = ho
                    existing.away_win_odds = ao
                    updated += 1
                    logger.info(f"  Updated {bm} for {home_code} vs {away_code}: {ho}/{ao}")
            else:
                session.add(Odds(game_id=game_id, bookmaker=bm, home_win_odds=ho, away_win_odds=ao))
                logger.info(f"  Created {bm} for {home_code} vs {away_code}: {ho}/{ao}")

    session.commit()
    session.close()
    logger.info(f"Done: {created} games, {updated} odds updated")


if __name__ == "__main__":
    fetch_and_store()
