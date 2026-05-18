"""
Odds API Client - Fetches real-time betting odds from odds-api.io
Fetches Polish bookmakers: Betclic, bet365, Fortuna
"""
import os
import time
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from app.config import ODDS_API_KEY
from app.db.database import SessionLocal
from app.db.models import Game, Odds

# Setup logging
logger = logging.getLogger(__name__)

# Polish bookmakers we track
POLISH_BOOKMAKERS = ["Betclic", "bet365", "Fortuna"]

# All NBA team name → abbreviation mapping
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

# API Configuration
BASE_URL = "https://api.odds-api.io/v3"


def normalize_name(value: str) -> str:
    """Normalize string for comparison (remove special chars, lowercase)"""
    import re
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def resolve_bookmaker_key(target_name: str, all_markets: dict) -> Optional[str]:
    """
    Find the actual bookmaker key from the API response
    Handles case sensitivity and slight naming variations
    """
    if not isinstance(all_markets, dict) or not all_markets:
        return None

    # Exact match first
    if target_name in all_markets:
        return target_name

    # Normalized match
    target_norm = normalize_name(target_name)
    for key in all_markets.keys():
        if normalize_name(str(key)) == target_norm:
            return str(key)

    # Partial match fallback
    for key in all_markets.keys():
        key_norm = normalize_name(str(key))
        if target_norm and (target_norm in key_norm or key_norm in target_norm):
            return str(key)

    return None


def fetch_events_list(start_date: str, end_date: str) -> List[dict]:
    """
    Fetch list of NBA games for a date range
    
    Args:
        start_date: ISO format (e.g., "2025-01-01T00:00:00Z")
        end_date: ISO format (e.g., "2025-01-31T23:59:59Z")
    
    Returns:
        List of game objects with id, home, away, date
    """
    logger.info(f"Fetching events: {start_date} to {end_date}")
    
    if not ODDS_API_KEY:
        logger.error("ODDS_API_KEY not set in environment")
        return []
    
    params = {
        "apiKey": ODDS_API_KEY,
        "sport": "basketball",
        "league": "usa-nba",
        "from": start_date,
        "to": end_date
    }
    
    try:
        response = requests.get(f"{BASE_URL}/historical/events", params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
        
        # Handle different response formats
        if isinstance(payload, dict) and "data" in payload:
            return payload.get("data") or []
        if isinstance(payload, list):
            return payload
        
        logger.warning(f"Unexpected API response format: {type(payload)}")
        return []
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching events: {e}")
        return []


def extract_moneyline_odds(bookmaker_name: str, all_markets: dict) -> Dict[str, Optional[float]]:
    """
    Extract full-game moneyline odds for a specific bookmaker
    
    Args:
        bookmaker_name: Name of bookmaker (e.g., "Betclic")
        all_markets: Dict of all available bookmakers and their markets
    
    Returns:
        Dict with 'home' and 'away' odds (or None if not available)
    """
    bm_key = resolve_bookmaker_key(bookmaker_name, all_markets)
    if not bm_key:
        return {"home": None, "away": None}
    
    bm_data = all_markets.get(bm_key, [])
    
    try:
        # Find full-game moneyline (avoid 1Q/2Q/3Q/4Q variants)
        for market in bm_data:
            market_name = (market.get("name") or "").strip().lower()
            
            # Skip quarter-specific markets
            if any(q in market_name for q in ("1q", "2q", "3q", "4q", "quarter")):
                continue
            
            # Found moneyline
            if market_name == "ml" or market_name == "moneyline":
                odds_list = market.get("odds") or []
                if odds_list:
                    odd = odds_list[0]
                    return {
                        "home": float(odd.get("home", 0)) or None,
                        "away": float(odd.get("away", 0)) or None
                    }
    
    except (KeyError, IndexError, ValueError) as e:
        logger.warning(f"Error extracting odds for {bookmaker_name}: {e}")
    
    return {"home": None, "away": None}


def fetch_odds_for_game(event_id: str, bookmakers: Optional[List[str]] = None) -> dict:
    """
    Fetch detailed odds for a specific game
    
    Args:
        event_id: Odds API event ID
        bookmakers: List of bookmakers to fetch (defaults to POLISH_BOOKMAKERS)
    
    Returns:
        Dict with bookmakers and their market data
    """
    bookmakers = bookmakers or POLISH_BOOKMAKERS
    
    if not ODDS_API_KEY:
        return {}
    
    params = {
        "apiKey": ODDS_API_KEY,
        "eventId": event_id,
        "bookmakers": ",".join(bookmakers)
    }
    
    try:
        response = requests.get(f"{BASE_URL}/historical/odds", params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching odds for event {event_id}: {e}")
        return {}


def run_odds_pipeline(start_iso: str, end_iso: str, max_games: int = 50, sleep_sec: float = 0.5):
    """
    Main pipeline to fetch and store odds
    
    Args:
        start_iso: Start date in ISO format
        end_iso: End date in ISO format
        max_games: Maximum games to process (API rate limiting)
        sleep_sec: Sleep between API calls
    """
    db = SessionLocal()
    
    try:
        logger.info("Starting odds pipeline...")
        
        # Step 1: Get list of games
        events = fetch_events_list(start_iso, end_iso)
        if not events:
            logger.warning("No events found")
            return
        
        events_to_process = events[:max_games]
        logger.info(f"Found {len(events)} games, processing {len(events_to_process)}")
        
        # Step 2: Process each game
        for idx, event in enumerate(events_to_process, 1):
            try:
                odds_event_id = event.get("id")
                home_team_full = event.get("home")
                away_team_full = event.get("away")
                game_date_str = event.get("date")
                
                if not all([odds_event_id, home_team_full, away_team_full, game_date_str]):
                    logger.warning(f"Skipping event {idx} - missing required fields")
                    continue
                
                # Convert team names to abbreviations
                home_team_abbr = TEAM_ABBREVIATIONS.get(home_team_full)
                away_team_abbr = TEAM_ABBREVIATIONS.get(away_team_full)
                
                if not home_team_abbr or not away_team_abbr:
                    logger.warning(f"Event {idx}: Unknown team names - {home_team_full} vs {away_team_full}")
                    continue
                
                game_date = pd.to_datetime(game_date_str, utc=True).date()
                logger.info(f"[{idx}/{len(events_to_process)}] {home_team_abbr} vs {away_team_abbr} ({game_date})")
                
                # Step 3: Find matching game in database
                date_from = game_date - timedelta(days=1)
                date_to = game_date + timedelta(days=1)
                
                game_in_db = db.query(Game).filter(
                    Game.game_date.between(date_from, date_to),
                    Game.home_team == home_team_abbr,
                    Game.away_team == away_team_abbr
                ).first()
                
                if not game_in_db:
                    logger.warning(f"  → Game not found in DB for {home_team_abbr} vs {away_team_abbr}")
                    time.sleep(sleep_sec)
                    continue
                
                game_id = game_in_db.game_id
                logger.info(f"  → Found game in DB: {game_id}")
                
                # Step 4: Check what odds we already have
                existing_bookmakers = {
                    row[0]
                    for row in db.query(Odds.bookmaker)
                    .filter(Odds.game_id == game_id)
                    .all()
                }
                missing_bookmakers = [bm for bm in POLISH_BOOKMAKERS if bm not in existing_bookmakers]
                
                if not missing_bookmakers:
                    logger.info(f"  → Odds already complete for all bookmakers")
                    time.sleep(sleep_sec)
                    continue
                
                logger.info(f"  → Fetching odds from: {missing_bookmakers}")
                
                # Step 5: Fetch odds from API
                raw_odds_data = fetch_odds_for_game(odds_event_id, bookmakers=missing_bookmakers)
                all_markets = raw_odds_data.get("bookmakers", {})
                
                # Step 6: Extract and save odds
                saved_count = 0
                for bookmaker in missing_bookmakers:
                    clean_odds = extract_moneyline_odds(bookmaker, all_markets)
                    
                    if clean_odds["home"] is None or clean_odds["away"] is None:
                        logger.warning(f"  → No moneyline found for {bookmaker}")
                        continue
                    
                    # Check if odds already exist
                    existing = db.query(Odds).filter(
                        Odds.game_id == game_id,
                        Odds.bookmaker == bookmaker
                    ).first()
                    
                    if not existing:
                        new_odds = Odds(
                            game_id=game_id,
                            bookmaker=bookmaker,
                            home_win_odds=clean_odds["home"],
                            away_win_odds=clean_odds["away"]
                        )
                        db.add(new_odds)
                        saved_count += 1
                
                if saved_count > 0:
                    db.commit()
                    logger.info(f"  → Saved {saved_count} odds entries")
                else:
                    db.rollback()
                
                time.sleep(sleep_sec)
            
            except Exception as e:
                logger.error(f"Error processing event {idx}: {e}")
                db.rollback()
                continue
        
        logger.info("✓ Odds pipeline completed successfully")
    
    except Exception as e:
        logger.error(f"Fatal error in odds pipeline: {e}")
        db.rollback()
    
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Default to recent games
    end_date = datetime.now().isoformat() + "Z"
    start_date = (datetime.now() - timedelta(days=30)).isoformat() + "Z"
    
    logger.info(f"Running odds pipeline from {start_date} to {end_date}")
    run_odds_pipeline(start_date, end_date, max_games=50)
