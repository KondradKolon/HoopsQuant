"""
SQL Migration for HoopsQuant Database in Supabase

Run this SQL in your Supabase SQL Editor to create all tables.
"""

SQL_MIGRATIONS = """
-- Games table
CREATE TABLE IF NOT EXISTS games (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) UNIQUE NOT NULL,
    game_date DATE NOT NULL,
    season VARCHAR(10),
    home_team VARCHAR(10),
    away_team VARCHAR(10),
    home_score FLOAT,
    away_score FLOAT,
    home_team_wins BOOLEAN,
    
    -- Home team stats
    home_fgm FLOAT,
    home_fga FLOAT,
    home_fg_pct FLOAT,
    home_fg3m FLOAT,
    home_fg3a FLOAT,
    home_fg3_pct FLOAT,
    home_ftm FLOAT,
    home_fta FLOAT,
    home_ft_pct FLOAT,
    home_oreb FLOAT,
    home_dreb FLOAT,
    home_reb FLOAT,
    home_ast FLOAT,
    home_stl FLOAT,
    home_blk FLOAT,
    home_tov FLOAT,
    home_pf FLOAT,
    home_plus_minus FLOAT,
    
    -- Away team stats
    away_fgm FLOAT,
    away_fga FLOAT,
    away_fg_pct FLOAT,
    away_fg3m FLOAT,
    away_fg3a FLOAT,
    away_fg3_pct FLOAT,
    away_ftm FLOAT,
    away_fta FLOAT,
    away_ft_pct FLOAT,
    away_oreb FLOAT,
    away_dreb FLOAT,
    away_reb FLOAT,
    away_ast FLOAT,
    away_stl FLOAT,
    away_blk FLOAT,
    away_tov FLOAT,
    away_pf FLOAT,
    away_plus_minus FLOAT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_game_date (game_date),
    INDEX idx_season (season)
);

-- Odds table
CREATE TABLE IF NOT EXISTS odds (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) REFERENCES games(game_id),
    bookmaker VARCHAR(50),
    home_win_odds FLOAT,
    away_win_odds FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(game_id, bookmaker),
    INDEX idx_game_id (game_id),
    INDEX idx_bookmaker (bookmaker)
);

-- Predictions table
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    game_id VARCHAR(20) REFERENCES games(game_id),
    model_name VARCHAR(50),
    home_win_prob FLOAT,
    away_win_prob FLOAT,
    confidence FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(game_id, model_name),
    INDEX idx_game_id (game_id)
);

-- Users table (for authentication)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    supabase_id VARCHAR(100) UNIQUE,
    email VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(100),
    provider VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_email (email)
);

-- Watchlist table
CREATE TABLE IF NOT EXISTS watchlist (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    game_id VARCHAR(20) REFERENCES games(game_id),
    added_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, game_id),
    INDEX idx_user_id (user_id)
);
"""

if __name__ == "__main__":
    print("Copy and paste this SQL into your Supabase SQL Editor:")
    print("=" * 80)
    print(SQL_MIGRATIONS)
    print("=" * 80)
