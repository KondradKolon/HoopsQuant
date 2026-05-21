"""
NBA Stats Fetcher - Fetches game data from stats.nba.com for 2026 season
Transforms and saves to database
"""
import logging
import time
import random
import pandas as pd
from datetime import datetime
from typing import Optional
from curl_cffi import requests as cffi_requests
from app.db.database import SessionLocal
from app.db.models import Game

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s: %(message)s'
)
logger = logging.getLogger("nba_fetcher_2026")

# NBA Stats API configuration
NBA_STATS_URL = "https://stats.nba.com/stats/leaguegamelog"

NBA_HEADERS = {
    "Host": "stats.nba.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/110.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
}

# Columns we care about from NBA API
STAT_COLS = [
    "GAME_ID", "GAME_DATE", "TEAM_ABBREVIATION", "MATCHUP", "WL",
    "PTS", "FGM", "FGA", "FG_PCT", "FG3M", "FG3A", "FG3_PCT",
    "FTM", "FTA", "FT_PCT", "OREB", "DREB", "REB", "AST", "STL",
    "BLK", "TOV", "PF", "PLUS_MINUS",
]


def fetch_season(season: str = "2025-26") -> pd.DataFrame:
    """
    Fetch all games for a season from NBA Stats API
    
    Args:
        season: Season in format "YYYY-YY" (default: "2025-26")
    
    Returns:
        DataFrame with 2 rows per game (home and away team stats)
    
    Raises:
        RuntimeError: If API call fails or returns no data
    """
    logger.info(f"🏀 Fetching NBA stats for season {season}...")
    
    params = {
        "Counter": "1000",
        "DateFrom": "",
        "DateTo": "",
        "Direction": "ASC",
        "LeagueID": "00",
        "PlayerOrTeam": "T",
        "Season": season,
        "SeasonType": "Regular Season",
        "Sorter": "DATE",
    }
    
    # Add random pause to avoid rate limiting
    pause = random.uniform(2, 4)
    logger.info(f"⏳ Waiting {pause:.1f}s before API call...")
    time.sleep(pause)
    
    # Retry logic
    MAX_RETRIES = 4
    BASE_WAIT = 8
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = cffi_requests.get(
                NBA_STATS_URL,
                params=params,
                headers=NBA_HEADERS,
                impersonate="chrome110",
                timeout=60,
            )
            
            if response.status_code == 500:
                raise RuntimeError(f"API returned 500 error")
            
            response.raise_for_status()
            break
        
        except Exception as e:
            if attempt == MAX_RETRIES:
                logger.error(f"❌ Failed after {MAX_RETRIES} attempts: {e}")
                raise RuntimeError(f"NBA API failed: {e}")
            
            wait_time = BASE_WAIT * (2 ** (attempt - 1)) + random.uniform(0, 5)
            logger.warning(f"⚠️ Attempt {attempt}/{MAX_RETRIES} failed. Retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)
    
    data = response.json()
    
    if "resultSets" not in data or len(data["resultSets"]) == 0:
        raise RuntimeError("API returned empty result set")
    
    result_set = data["resultSets"][0]
    headers = result_set["headers"]
    rows = result_set["rowSet"]
    
    df = pd.DataFrame(rows, columns=headers)
    df = df[STAT_COLS].copy()
    
    logger.info(f"✅ Fetched {len(df)} game records for {season}")
    return df


def transform_games(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transform NBA API data to game-level format (1 row per game)
    """
    logger.info("📊 Transforming game data...")
    
    # Parse date - API returns ISO format (YYYY-MM-DD)
    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"], format="%Y-%m-%d")
    df["SEASON"] = "2025-26"
    
    # Group by game
    games_list = []
    
    for game_id, group in df.groupby("GAME_ID"):
        if len(group) != 2:
            logger.warning(f"⚠️ Game {game_id} has {len(group)} rows (expected 2), skipping")
            continue
        
        home_rows = group[group["MATCHUP"].str.contains("vs", na=False)]
        away_rows = group[group["MATCHUP"].str.contains("@", na=False)]

        if home_rows.empty or away_rows.empty:
            logger.warning(f"⚠️ Game {game_id} missing home/away matchup rows, skipping")
            continue

        home = home_rows.iloc[0]
        away = away_rows.iloc[0]
        
        # Determine winner
        home_wins = home["WL"] == "W"
        
        game = {
            "game_id": game_id,
            "game_date": home["GAME_DATE"],
            "season": "2025-26",
            "home_team": home["TEAM_ABBREVIATION"],
            "away_team": away["TEAM_ABBREVIATION"],
            "home_score": home["PTS"],
            "away_score": away["PTS"],
            "home_team_wins": 1 if home_wins else 0,
            # Home team stats
            "home_fgm": home["FGM"],
            "home_fga": home["FGA"],
            "home_fg_pct": home["FG_PCT"],
            "home_fg3m": home["FG3M"],
            "home_fg3a": home["FG3A"],
            "home_fg3_pct": home["FG3_PCT"],
            "home_ftm": home["FTM"],
            "home_fta": home["FTA"],
            "home_ft_pct": home["FT_PCT"],
            "home_oreb": home["OREB"],
            "home_dreb": home["DREB"],
            "home_reb": home["REB"],
            "home_ast": home["AST"],
            "home_stl": home["STL"],
            "home_blk": home["BLK"],
            "home_tov": home["TOV"],
            "home_pf": home["PF"],
            "home_plus_minus": home["PLUS_MINUS"],
            # Away team stats
            "away_fgm": away["FGM"],
            "away_fga": away["FGA"],
            "away_fg_pct": away["FG_PCT"],
            "away_fg3m": away["FG3M"],
            "away_fg3a": away["FG3A"],
            "away_fg3_pct": away["FG3_PCT"],
            "away_ftm": away["FTM"],
            "away_fta": away["FTA"],
            "away_ft_pct": away["FT_PCT"],
            "away_oreb": away["OREB"],
            "away_dreb": away["DREB"],
            "away_reb": away["REB"],
            "away_ast": away["AST"],
            "away_stl": away["STL"],
            "away_blk": away["BLK"],
            "away_tov": away["TOV"],
            "away_pf": away["PF"],
            "away_plus_minus": away["PLUS_MINUS"],
        }
        
        games_list.append(game)
    
    games_df = pd.DataFrame(games_list)
    logger.info(f"✅ Transformed to {len(games_df)} games")
    return games_df


def save_games(df: pd.DataFrame):
    """
    Save games to database with upsert logic
    (update if exists, insert if new)
    """
    logger.info("💾 Saving games to database...")
    
    session = SessionLocal()
    
    try:
        saved_count = 0
        updated_count = 0
        
        for _, row in df.iterrows():
            # Check if game exists
            existing = session.query(Game).filter(
                Game.game_id == row["game_id"]
            ).first()
            
            if existing:
                # Update existing
                for col in df.columns:
                    if col != "game_id":
                        setattr(existing, col, row[col])
                updated_count += 1
            else:
                # Insert new
                game = Game(**row)
                session.add(game)
                saved_count += 1
        
        session.commit()
        
        logger.info(f"✅ Saved {saved_count} new games, updated {updated_count} existing games")
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Database error: {e}")
        raise
    finally:
        session.close()


def main():
    """Main execution"""
    try:
        logger.info("="*70)
        logger.info("NBA STATS FETCHER - 2025-26 SEASON")
        logger.info("="*70)
        
        # 1. Fetch data
        df_raw = fetch_season("2025-26")
        
        # 2. Transform
        df_games = transform_games(df_raw)
        
        # 3. Save
        save_games(df_games)
        
        logger.info("\n" + "="*70)
        logger.info("✅ PIPELINE COMPLETE")
        logger.info("="*70)
        
    except Exception as e:
        logger.error(f"\n❌ PIPELINE FAILED: {e}")
        raise


if __name__ == "__main__":
    main()
