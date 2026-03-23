import os
import time
import requests
import pandas as pd
from dotenv import load_dotenv
from datetime import timedelta
import argparse
import re

from src.db.database.database import SessionLocal
from src.db.database.models import Game, Odds


TEAM_ABBREVIATIONS = {
    "Atlanta Hawks": "ATL",
    "Boston Celtics": "BOS",
    "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA",
    "Chicago Bulls": "CHI",
    "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL",
    "Denver Nuggets": "DEN",
    "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW",
    "Houston Rockets": "HOU",
    "Indiana Pacers": "IND",
    "LA Clippers": "LAC",
    "Los Angeles Lakers": "LAL",
    "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA",
    "Milwaukee Bucks": "MIL",
    "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP",
    "New York Knicks": "NYK",
    "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL",
    "Philadelphia 76ers": "PHI",
    "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR",
    "Sacramento Kings": "SAC",
    "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR",
    "Utah Jazz": "UTA",
    "Washington Wizards": "WAS",
}


# 1. Setup & Config
load_dotenv()
API_KEY = os.getenv("ODDS_API_KEY")
BASE_URL = "https://api.odds-api.io/v3"
BOOKMAKERS_LIST = ["Polymarket", "Superbet"]  # The ones we want to isolate


def _norm_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def _resolve_bookmaker_key(target_name: str, all_markets: dict) -> str | None:
    if not isinstance(all_markets, dict) or not all_markets:
        return None

    if target_name in all_markets:
        return target_name

    target_norm = _norm_name(target_name)
    for key in all_markets.keys():
        if _norm_name(str(key)) == target_norm:
            return str(key)

    # fallback: containment match
    for key in all_markets.keys():
        key_norm = _norm_name(str(key))
        if target_norm and (target_norm in key_norm or key_norm in target_norm):
            return str(key)

    return None

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def fetch_events_list(start_date, end_date):
    """Step 1: Get the 'Calendar' of games (IDs and Teams)."""
    print(f"--- Fetching Event List: {start_date} to {end_date} ---")
    params = {
        "apiKey": API_KEY,
        "sport": "basketball",
        "league": "usa-nba",
        "from": start_date,
        "to": end_date
    }
    response = requests.get(f"{BASE_URL}/historical/events", params=params)
    response.raise_for_status()
    payload = response.json()
    # API sometimes returns list directly, sometimes {"data": [...]}
    if isinstance(payload, dict) and "data" in payload:
        return payload.get("data") or []
    if isinstance(payload, list):
        return payload
    return []

def extract_ml_from_json(bookmaker_name, all_markets):
    """Surgical extraction of the full-game Moneyline (ML)."""
    # Filter markets for the specific bookmaker (case-insensitive / normalized)
    bm_key = _resolve_bookmaker_key(bookmaker_name, all_markets)
    bm_data = all_markets.get(bm_key, []) if bm_key else []
    
    # Prefer full-game moneyline; avoid 1Q/2Q/3Q/4Q variants
    try:
        def is_full_game_ml(market_name: str) -> bool:
            name = (market_name or "").strip().lower()
            if any(q in name for q in ("1q", "2q", "3q", "4q", "quarter")):
                return False
            return name in ("ml", "moneyline")

        ml_market = next(m for m in bm_data if is_full_game_ml(m.get("name", "")))
        odds_list = ml_market.get("odds") or []
        odds = odds_list[0]
        return {
            "home": float(odds.get('home', 0)),
            "away": float(odds.get('away', 0))
        }
    except (StopIteration, KeyError, IndexError):
        # Return None if the bookmaker doesn't have a full-game ML for this game
        return {"home": None, "away": None}

def fetch_odds_for_game(event_id, bookmakers=None):
    """Step 2: Get the detailed odds for a single specific Game ID."""
    bookmakers = bookmakers or BOOKMAKERS_LIST
    params = {
        "apiKey": API_KEY,
        "eventId": event_id,
        "bookmakers": ",".join(bookmakers)
    }
    response = requests.get(f"{BASE_URL}/historical/odds", params=params)
    response.raise_for_status()
    return response.json()

def run_odds_pipeline(start_iso, end_iso, db, max_games: int = 45, sleep_sec: float = 0.1, debug: bool = False):
    """The main coordinator that runs the whole process."""
    # A. Get the games
    events = fetch_events_list(start_iso, end_iso)
    
    # Process only up to 45 games
    events_to_process = events[:max_games]
    
    print(f"Found {len(events)} games. Processing first {len(events_to_process)} games...")
    
    for event in events_to_process:
        odds_eid = event.get('id')
        home_team_full = event.get('home')
        away_team_full = event.get('away')
        game_date = pd.to_datetime(event.get('date'), utc=True).date()

        home_team_abbr = TEAM_ABBREVIATIONS.get(home_team_full)
        away_team_abbr = TEAM_ABBREVIATIONS.get(away_team_full)

        if not home_team_abbr or not away_team_abbr:
            print(f"Warning: Could not find abbreviation for {home_team_full} or {away_team_full}. Skipping.")
            continue
        
        print(f"Processing: {home_team_full} vs {away_team_full} ({game_date})")
        
        try:
            # Find the game in our DB by team names and a 3-day window for the date
            date_from = game_date - timedelta(days=1)
            date_to = game_date + timedelta(days=1)

            game_in_db = db.query(Game).filter(
                Game.game_date.between(date_from, date_to),
                Game.home_team == home_team_abbr,
                Game.away_team == away_team_abbr
            ).first()

            if not game_in_db:
                print(f"Warning: Game not found in DB for {home_team_abbr} vs {away_team_abbr} on {game_date}. Skipping.")
                continue

            game_id_from_db = game_in_db.game_id
            print(f"Found matching game in DB with id: {game_id_from_db}")

            # If we already have odds for all requested bookmakers, skip API call
            existing_books = {
                row[0]
                for row in db.query(Odds.bookmaker)
                .filter(Odds.game_id == game_id_from_db)
                .all()
            }
            missing_books = [bm for bm in BOOKMAKERS_LIST if bm not in existing_books]
            if not missing_books:
                if debug:
                    print("   -> Odds already complete; skipping API call")
                continue

            # Fetch the big messy JSON for this one game from Odds API
            raw_odds_data = fetch_odds_for_game(odds_eid, bookmakers=missing_books)
            all_markets = raw_odds_data.get('bookmakers', {})

            if debug and isinstance(all_markets, dict):
                print(f"   -> Bookmakers returned: {list(all_markets.keys())}")
            
            # C. Extract and Clean
            new_rows = 0
            for bm in missing_books:
                clean_odds = extract_ml_from_json(bm, all_markets)

                if debug and clean_odds['home'] is None:
                    bm_key = _resolve_bookmaker_key(bm, all_markets)
                    bm_data = all_markets.get(bm_key, []) if bm_key else []
                    market_names = [m.get('name') for m in bm_data if isinstance(m, dict)]
                    print(f"   -> No full-game ML for {bm} (resolved={bm_key}). Markets: {market_names}")
                
                # Check if odds exist for our internal game_id
                odds_exist = db.query(Odds).filter(
                    Odds.game_id == game_id_from_db, 
                    Odds.bookmaker == bm
                ).first()

                if not odds_exist and clean_odds['home'] is not None:
                    new_odds = Odds(
                        game_id=game_id_from_db,
                        bookmaker=bm,
                        home_win_odds=clean_odds['home'],
                        away_win_odds=clean_odds['away']
                    )
                    db.add(new_odds)
                    new_rows += 1
            
            if new_rows:
                db.commit()
                print(f"   -> Saved {new_rows} odds rows")
            else:
                db.rollback()
            
            # Tiny sleep to be polite to the API
            time.sleep(sleep_sec)
            
        except Exception as e:
            print(f"Error processing odds for {home_team_full} vs {away_team_full}: {e}")
            db.rollback()

    print(f"\n--- SUCCESS ---")
    print(f"Finished processing odds for {len(events_to_process)} games.")

# --- START THE ENGINE ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch NBA odds and store them in DB")
    parser.add_argument("--start", default="2026-01-01T00:00:00Z")
    parser.add_argument("--end", default="2026-01-31T23:59:59Z")
    parser.add_argument("--max-games", type=int, default=45)
    parser.add_argument("--sleep-sec", type=float, default=float(os.getenv("ODDS_API_SLEEP_SEC", "0.1")))
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    db_session = next(get_db())
    run_odds_pipeline(args.start, args.end, db_session, max_games=args.max_games, sleep_sec=args.sleep_sec, debug=args.debug)
    db_session.close()