"""
seed_odds_to_supabase.py — Bulk-fetch NBA odds & store in Supabase.

Runs on Railway (where DATABASE_URL is set). Fetches:
  - Historical odds for the past 90 days (NBA games)
  - Current/live odds for upcoming games

Usage (Railway):
  python scripts/seed_odds_to_supabase.py

Idempotent: skips existing (game_id, bookmaker) pairs.
"""

import hashlib
import logging
import os
import sys
import time
from datetime import datetime, timedelta, date

import requests
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
logger = logging.getLogger("seed_odds")

KEY = os.getenv("ODDS_API_KEY")
BASE = "https://api.odds-api.io/v3"
BOOKMAKERS = [
    b.strip()
    for b in os.getenv("BOOKMAKERS", "Superbet,Stake").split(",")
    if b.strip()
]
DATABASE_URL = os.getenv("DATABASE_URL")

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


def api_get(endpoint, params, retries=5):
    for attempt in range(retries):
        try:
            r = requests.get(f"{BASE}/{endpoint}", params={"apiKey": KEY, **params}, timeout=15)
            if r.status_code == 429:
                logger.warning("Rate limited, waiting 120s...")
                time.sleep(120)
                continue
            if r.status_code == 200:
                return r.json()
            logger.warning(f"{endpoint} returned {r.status_code}")
            return None
        except Exception as e:
            logger.warning(f"Request error: {e}")
            if attempt < retries - 1:
                time.sleep(5)
    return None


def extract_ml(markets):
    for m in markets or []:
        name = (m.get("name") or "").strip().lower()
        if any(q in name for q in ("1q", "2q", "3q", "4q", "quarter", "ht", "2h")):
            continue
        odds_list = m.get("odds") or []
        if not odds_list:
            continue
        if name in ("ml", "moneyline", "3-way result"):
            o = odds_list[0]
            h = o.get("home")
            a = o.get("away")
            if h and a:
                return float(h), float(a)
    return None, None


def derive_season(game_date: date) -> str:
    y = game_date.year
    return f"{y}-{str(y+1)[-2:]}" if game_date.month >= 10 else f"{y-1}-{str(y)[-2:]}"


def game_id_from_event(eid: str) -> str:
    return "ODDS" + hashlib.md5(eid.encode()).hexdigest()[:12]


def ensure_db():
    if not DATABASE_URL:
        logger.error("DATABASE_URL not set — are you on Railway?")
        sys.exit(1)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"connect_timeout": 10})
    Session = sessionmaker(bind=engine)
    return engine, Session()


def seed_historical_odds(session):
    """Fetch historical NBA events (past 90 days, chunked into 31-day windows) and store odds."""
    today = date.today()
    chunks = []
    chunk_start = today - timedelta(days=90)
    while chunk_start < today:
        chunk_end = min(chunk_start + timedelta(days=30), today)
        chunks.append((chunk_start.isoformat() + "T00:00:00Z", chunk_end.isoformat() + "T23:59:59Z"))
        chunk_start = chunk_end + timedelta(days=1)

    total_odds = 0
    total_games = 0
    req_count = 0

    for from_date, to_date in chunks:
        logger.info(f"Fetching historical events {from_date[:10]} to {to_date[:10]}...")
        data = api_get("historical/events", {
            "sport": "basketball", "league": "usa-nba",
            "from": from_date, "to": to_date, "limit": 200
        })
        req_count += 1
        if not data:
            continue

        events = data if isinstance(data, list) else data.get("data", data.get("events", []))
        logger.info(f"  Got {len(events)} events")

        for ev in events:
            eid = str(ev.get("id", ""))
            if not eid:
                continue

            home_full = ev.get("home", "")
            away_full = ev.get("away", "")
            home_code = TEAM_MAP.get(home_full)
            away_code = TEAM_MAP.get(away_full)
            if not home_code or not away_code:
                continue

            try:
                game_date = datetime.fromisoformat((ev.get("date") or "").replace("Z", "+00:00")).date()
            except Exception:
                continue

            season = derive_season(game_date)
            gid = game_id_from_event(eid)
            scores = ev.get("scores") or {}

            # Upsert Game
            existing = session.execute(
                text("SELECT game_id FROM games WHERE game_id = :gid"),
                {"gid": gid}
            ).fetchone()

            if not existing:
                session.execute(
                    text("""
                        INSERT INTO games (game_id, game_date, season, home_team, away_team, home_score, away_score, home_team_wins)
                        VALUES (:gid, :gd, :season, :home, :away, :hs, :as, :hw)
                    """),
                    {
                        "gid": gid, "gd": game_date, "season": season,
                        "home": home_code, "away": away_code,
                        "hs": scores.get("home"), "as": scores.get("away"),
                        "hw": scores.get("home") and scores.get("away") and scores["home"] > scores["away"]
                    }
                )
                total_games += 1

            # Fetch odds for this event
            logger.info(f"  [{total_games}] {home_code} vs {away_code} ({game_date}) — fetching odds...")
            odds_data = api_get("historical/odds", {
                "eventId": eid, "bookmakers": ",".join(BOOKMAKERS)
            })
            req_count += 1
            if not odds_data:
                continue

            bms = odds_data.get("bookmakers", {})
            for bm in BOOKMAKERS:
                markets = bms.get(bm, [])
                ho, ao = extract_ml(markets)
                if not ho or not ao:
                    continue

                existing_odds = session.execute(
                    text("SELECT id FROM odds WHERE game_id = :gid AND bookmaker = :bm"),
                    {"gid": gid, "bm": bm}
                ).fetchone()

                if not existing_odds:
                    session.execute(
                        text("""
                            INSERT INTO odds (game_id, bookmaker, home_win_odds, away_win_odds)
                            VALUES (:gid, :bm, :ho, :ao)
                        """),
                        {"gid": gid, "bm": bm, "ho": ho, "ao": ao}
                    )
                    total_odds += 1
                    logger.info(f"    Stored {bm}: H={ho} A={ao}")

            time.sleep(0.3)

        session.commit()
        logger.info(f"  Chunk done. Games: {total_games}, Odds rows: {total_odds}, API calls: {req_count}")

    return total_games, total_odds, req_count


def seed_current_odds(session):
    """Fetch current NBA events and their odds, store in DB."""
    logger.info("Fetching current NBA events...")
    today = date.today()
    from_iso = (today - timedelta(days=1)).isoformat() + "T00:00:00Z"
    to_iso = (today + timedelta(days=21)).isoformat() + "T23:59:59Z"
    events_data = api_get(
        "events",
        {
            "sport": "basketball",
            "league": "usa-nba",
            "from": from_iso,
            "to": to_iso,
            "limit": 200,
        },
    )
    if not events_data:
        logger.warning("No current events")
        return 0, 0

    events = events_data if isinstance(events_data, list) else events_data.get("events", events_data.get("data", []))
    nba_events = []
    for ev in events:
        home = ev.get("home", "")
        away = ev.get("away", "")
        if TEAM_MAP.get(home) and TEAM_MAP.get(away):
            nba_events.append(ev)

    logger.info(f"  Found {len(nba_events)} current NBA events")

    # Fetch odds via /odds/multi
    eids = [str(ev["id"]) for ev in nba_events if ev.get("id")]
    odds_map = {}
    batches = [eids[i:i+10] for i in range(0, len(eids), 10)]
    req_used = 0

    for batch in batches:
        data = api_get("odds/multi", {"eventIds": ",".join(batch), "bookmakers": ",".join(BOOKMAKERS)})
        req_used += 1
        if not data:
            continue
        items = data if isinstance(data, list) else data.get("odds", data.get("data", []))
        for item in items:
            eid = str(item.get("id", ""))
            if eid:
                odds_map[eid] = item.get("bookmakers", {})

    total_games = 0
    total_odds = 0

    for ev in nba_events:
        eid = str(ev["id"])
        home_full = ev.get("home", "")
        away_full = ev.get("away", "")
        home_code = TEAM_MAP[home_full]
        away_code = TEAM_MAP[away_full]

        try:
            game_date = datetime.fromisoformat((ev.get("date") or "").replace("Z", "+00:00")).date()
        except Exception:
            continue

        season = derive_season(game_date)
        gid = game_id_from_event(eid)
        bms = odds_map.get(eid, {})

        existing = session.execute(
            text("SELECT game_id FROM games WHERE game_id = :gid"), {"gid": gid}
        ).fetchone()

        if not existing:
            session.execute(
                text("""
                    INSERT INTO games (game_id, game_date, season, home_team, away_team)
                    VALUES (:gid, :gd, :season, :home, :away)
                """),
                {"gid": gid, "gd": game_date, "season": season, "home": home_code, "away": away_code}
            )
            total_games += 1

        for bm in BOOKMAKERS:
            markets = bms.get(bm, [])
            ho, ao = extract_ml(markets)
            if not ho or not ao:
                continue

            existing = session.execute(
                text("SELECT id FROM odds WHERE game_id = :gid AND bookmaker = :bm"),
                {"gid": gid, "bm": bm}
            ).fetchone()

            if not existing:
                session.execute(
                    text("INSERT INTO odds (game_id, bookmaker, home_win_odds, away_win_odds) VALUES (:gid, :bm, :ho, :ao)"),
                    {"gid": gid, "bm": bm, "ho": ho, "ao": ao}
                )
                total_odds += 1
            else:
                session.execute(
                    text(
                        "UPDATE odds SET home_win_odds = :ho, away_win_odds = :ao "
                        "WHERE game_id = :gid AND bookmaker = :bm"
                    ),
                    {"gid": gid, "bm": bm, "ho": ho, "ao": ao},
                )

    session.commit()
    logger.info(f"Current odds done. Games: {total_games}, Odds: {total_odds}, API calls: {req_used}")
    return total_games, total_odds, req_used


def main():
    if not KEY:
        logger.error("ODDS_API_KEY not set")
        sys.exit(1)

    engine, session = ensure_db()

    logger.info("=" * 60)
    logger.info("SEEDING HISTORICAL NBA ODDS TO SUPABASE")
    logger.info("=" * 60)
    g_hist, o_hist, r_hist = seed_historical_odds(session)

    logger.info("\n" + "=" * 60)
    logger.info("SEEDING CURRENT NBA ODDS TO SUPABASE")
    logger.info("=" * 60)
    g_cur, o_cur, r_cur = seed_current_odds(session)

    session.close()
    engine.dispose()

    total_req = r_hist + r_cur
    logger.info("\n" + "=" * 60)
    logger.info("SEED COMPLETE")
    logger.info(f"  Games created:  {g_hist + g_cur}")
    logger.info(f"  Odds rows:      {o_hist + o_cur}")
    logger.info(f"  API calls used: {total_req}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
