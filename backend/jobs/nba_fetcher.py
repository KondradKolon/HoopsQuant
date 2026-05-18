"""
NBA Stats Fetcher - Fetches game data from stats.nba.com
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
logger = logging.getLogger(__name__)

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


def fetch_season(season: str) -> pd.DataFrame:
    """
    Fetch all games for a season from NBA Stats API
    
    Args:
        season: Season in format "YYYY-YY" (e.g., "2023-24")
    
    Returns:
        DataFrame with 2 rows per game (home and away team stats)
    
    Raises:
        RuntimeError: If API call fails or returns no data
    """
    logger.info(f"Fetching NBA stats for season {season}...")
    
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
    logger.info(f"Waiting {pause:.1f}s before API call...")
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
                logger.error(f"Failed after {MAX_RETRIES} attempts: {e}")
                raise RuntimeError(f"NBA API failed: {e}")
            
            wait_time = BASE_WAIT * (2 ** (attempt - 1)) + random.uniform(0, 5)
            logger.warning(f"Attempt {attempt}/{MAX_RETRIES} failed. Retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)
    
    # Parse response
    result_set = response.json()["resultSets"][0]
    headers = result_set["headers"]
    rows = result_set["rowSet"]
    
    if not rows:
        raise RuntimeError(f"API returned 0 rows for season {season}")
    
    # Create DataFrame with selected columns
    df = pd.DataFrame(rows, columns=headers)[STAT_COLS]
    logger.info(f"✓ Fetched {len(df)} rows ({len(df)//2} games)")
    
    return df


def transform_game_data(home_row: dict, away_row: dict, season: str) -> Game:
    """
    Transform raw NBA data into Game model
    
    Args:
        home_row: Home team game stats
        away_row: Away team game stats
        season: Season string
    
    Returns:
        Game model instance ready to save
    """
    try:
        game_date = pd.to_datetime(home_row["GAME_DATE"]).date()
        home_won = home_row["WL"] == "W"
        
        return Game(
            game_id=str(home_row["GAME_ID"]),
            game_date=game_date,
            season=season,
            home_team=home_row["TEAM_ABBREVIATION"],
            away_team=away_row["TEAM_ABBREVIATION"],
            home_score=float(home_row["PTS"]),
            away_score=float(away_row["PTS"]),
            home_team_wins=home_won,
            
            # Home team stats
            home_fgm=float(home_row["FGM"]) if home_row["FGM"] else None,
            home_fga=float(home_row["FGA"]) if home_row["FGA"] else None,
            home_fg_pct=float(home_row["FG_PCT"]) if home_row["FG_PCT"] else None,
            home_fg3m=float(home_row["FG3M"]) if home_row["FG3M"] else None,
            home_fg3a=float(home_row["FG3A"]) if home_row["FG3A"] else None,
            home_fg3_pct=float(home_row["FG3_PCT"]) if home_row["FG3_PCT"] else None,
            home_ftm=float(home_row["FTM"]) if home_row["FTM"] else None,
            home_fta=float(home_row["FTA"]) if home_row["FTA"] else None,
            home_ft_pct=float(home_row["FT_PCT"]) if home_row["FT_PCT"] else None,
            home_oreb=float(home_row["OREB"]) if home_row["OREB"] else None,
            home_dreb=float(home_row["DREB"]) if home_row["DREB"] else None,
            home_reb=float(home_row["REB"]) if home_row["REB"] else None,
            home_ast=float(home_row["AST"]) if home_row["AST"] else None,
            home_stl=float(home_row["STL"]) if home_row["STL"] else None,
            home_blk=float(home_row["BLK"]) if home_row["BLK"] else None,
            home_tov=float(home_row["TOV"]) if home_row["TOV"] else None,
            home_pf=float(home_row["PF"]) if home_row["PF"] else None,
            home_plus_minus=float(home_row["PLUS_MINUS"]) if home_row["PLUS_MINUS"] else None,
            
            # Away team stats
            away_fgm=float(away_row["FGM"]) if away_row["FGM"] else None,
            away_fga=float(away_row["FGA"]) if away_row["FGA"] else None,
            away_fg_pct=float(away_row["FG_PCT"]) if away_row["FG_PCT"] else None,
            away_fg3m=float(away_row["FG3M"]) if away_row["FG3M"] else None,
            away_fg3a=float(away_row["FG3A"]) if away_row["FG3A"] else None,
            away_fg3_pct=float(away_row["FG3_PCT"]) if away_row["FG3_PCT"] else None,
            away_ftm=float(away_row["FTM"]) if away_row["FTM"] else None,
            away_fta=float(away_row["FTA"]) if away_row["FTA"] else None,
            away_ft_pct=float(away_row["FT_PCT"]) if away_row["FT_PCT"] else None,
            away_oreb=float(away_row["OREB"]) if away_row["OREB"] else None,
            away_dreb=float(away_row["DREB"]) if away_row["DREB"] else None,
            away_reb=float(away_row["REB"]) if away_row["REB"] else None,
            away_ast=float(away_row["AST"]) if away_row["AST"] else None,
            away_stl=float(away_row["STL"]) if away_row["STL"] else None,
            away_blk=float(away_row["BLK"]) if away_row["BLK"] else None,
            away_tov=float(away_row["TOV"]) if away_row["TOV"] else None,
            away_pf=float(away_row["PF"]) if away_row["PF"] else None,
            away_plus_minus=float(away_row["PLUS_MINUS"]) if away_row["PLUS_MINUS"] else None,
        )
    except Exception as e:
        logger.error(f"Error transforming game data: {e}")
        raise


def load_season_to_db(season: str, overwrite: bool = False) -> int:
    """
    Fetch season data and save to database
    
    Args:
        season: Season string (e.g., "2023-24")
        overwrite: If True, replace existing games for this season
    
    Returns:
        Number of games saved
    """
    db = SessionLocal()
    saved_count = 0
    
    try:
        # Fetch data
        df = fetch_season(season)
        
        # If overwrite, delete existing games for this season
        if overwrite:
            deleted = db.query(Game).filter(Game.season == season).delete()
            db.commit()
            logger.info(f"Deleted {deleted} existing games for {season}")
        
        # Group by game ID and transform
        logger.info("Transforming and saving games...")
        grouped = df.groupby("GAME_ID")
        
        for game_id, group_df in grouped:
            if len(group_df) != 2:
                logger.warning(f"Game {game_id} has {len(group_df)} rows instead of 2, skipping")
                continue
            
            # Get home and away rows
            home_row = group_df.iloc[0].to_dict()
            away_row = group_df.iloc[1].to_dict()
            
            # Transform
            try:
                game = transform_game_data(home_row, away_row, season)
                
                # Use merge to handle duplicates (upsert)
                db.merge(game)
                saved_count += 1
            
            except Exception as e:
                logger.error(f"Error transforming game {game_id}: {e}")
                continue
        
        db.commit()
        logger.info(f"✓ Saved {saved_count} games for season {season}")
        return saved_count
    
    except Exception as e:
        logger.error(f"Error loading season {season}: {e}")
        db.rollback()
        return 0
    
    finally:
        db.close()


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Fetch recent seasons
    seasons = ["2023-24", "2024-25"]
    total_saved = 0
    
    for season in seasons:
        try:
            count = load_season_to_db(season, overwrite=False)
            total_saved += count
        except Exception as e:
            logger.error(f"Failed to load {season}: {e}")
    
    logger.info(f"\n{'='*50}")
    logger.info(f"Total games saved: {total_saved}")
    logger.info(f"{'='*50}")
