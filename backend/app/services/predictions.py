"""
predictions.py — Prediction Service

Funkcje:
  - load_model() - wczytuje model.pkl, scaler.pkl, feature_cols.pkl
  - predict_game(game) - generuje predykcję dla jednego meczu
  - generate_features_for_game(game, session) - oblicza cechy dla meczu
"""

import logging
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Globalne zmienne do cachowania modelu (ładujemy raz na startup)
_model = None
_scaler = None
_feature_cols = None


def load_model():
    """Wczytuje model i scaler z plików pickle"""
    global _model, _scaler, _feature_cols
    
    if _model is not None:
        return _model, _scaler, _feature_cols
    
    # Model jest w katalogu backend/models/
    model_dir = Path(__file__).parent.parent.parent / "models"
    
    try:
        _model = joblib.load(model_dir / "model.pkl")
        _scaler = joblib.load(model_dir / "scaler.pkl")
        _feature_cols = joblib.load(model_dir / "feature_cols.pkl")
        
        logger.info(f"✅ Model wczytany ({len(_feature_cols)} cech)")
        return _model, _scaler, _feature_cols
    except FileNotFoundError as e:
        logger.error(f"❌ Model nie znaleziony: {e}")
        raise


def calculate_team_form(
    all_games: pd.DataFrame,
    team: str,
    game_date: pd.Timestamp,
    num_recent_games: int = 10
) -> dict:
    """
    Oblicza formę drużyny z ostatnich N meczów PRZED danym meczem.
    Używa shift(1) aby uniknąć look-ahead bias.
    """
    
    COLUMNS_TO_AVERAGE = [
        "reb", "ast", "stl", "blk", "tov_rate",
        "ortg", "drtg", "efg", "ts", "pace",
    ]
    
    # Filtrujemy mecze drużyny które już się odbędą
    team_games = all_games[
        ((all_games["home_team"] == team) | (all_games["away_team"] == team))
        & (all_games["game_date"] < game_date)
    ].copy()
    
    if len(team_games) == 0:
        # Jeśli brak historii, zwracamy neutralne wartości
        logger.warning(f"Brak historii dla {team}")
        return {f"{col}_last{num_recent_games}": np.nan for col in COLUMNS_TO_AVERAGE}
    
    # Przygotowujemy dane do rolling window
    home_games = team_games[team_games["home_team"] == team].copy()
    away_games = team_games[team_games["away_team"] == team].copy()
    
    team_stats = []
    
    for _, row in home_games.iterrows():
        stats = {col: row[f"home_{col}"] for col in COLUMNS_TO_AVERAGE}
        stats["game_date"] = row["game_date"]
        team_stats.append(stats)
    
    for _, row in away_games.iterrows():
        stats = {col: row[f"away_{col}"] for col in COLUMNS_TO_AVERAGE}
        stats["game_date"] = row["game_date"]
        team_stats.append(stats)
    
    if not team_stats:
        return {f"{col}_last{num_recent_games}": np.nan for col in COLUMNS_TO_AVERAGE}
    
    stats_df = pd.DataFrame(team_stats).sort_values("game_date")
    
    # Rolling mean z shift(1) — średnia z poprzednich N meczów
    rolled = stats_df[COLUMNS_TO_AVERAGE].rolling(num_recent_games, min_periods=1).mean().shift(1)
    
    # Bierzemy ostatni wiersz (najbliżej do game_date)
    last_form = rolled.iloc[-1]
    
    return {
        f"{col}_last{num_recent_games}": last_form[col]
        for col in COLUMNS_TO_AVERAGE
    }


def calculate_elo(all_games: pd.DataFrame, team: str, game_date: pd.Timestamp) -> float:
    """
    Oblicza Elo drużyny NA DZIEŃ PRZED MECZEM
    """
    
    K = 20
    HOME_ADVANTAGE = 50
    MEAN_ELO = 1500.0
    REGRESSION_FACTOR = 0.80
    
    elo_ratings = {}
    current_season = None
    
    # Iterujemy po wszystkich meczach do game_date
    for row in all_games[all_games["game_date"] < game_date].itertuples():
        # Regresja na nowy sezon
        if current_season is not None and row.season != current_season:
            for t in elo_ratings:
                elo_ratings[t] = (elo_ratings[t] * REGRESSION_FACTOR) + (MEAN_ELO * (1 - REGRESSION_FACTOR))
        
        current_season = row.season
        
        home = row.home_team
        away = row.away_team
        
        home_elo = elo_ratings.get(home, MEAN_ELO)
        away_elo = elo_ratings.get(away, MEAN_ELO)
        
        # MoV multiplier
        score_diff = abs(row.home_score - row.away_score)
        
        if row.home_team_wins == 1.0:
            winner_elo = home_elo + HOME_ADVANTAGE
            loser_elo = away_elo
        else:
            winner_elo = away_elo
            loser_elo = home_elo + HOME_ADVANTAGE
        
        elo_diff_winner = winner_elo - loser_elo
        mov_multiplier = ((score_diff + 3) ** 0.8) / (7.5 + 0.006 * elo_diff_winner)
        
        # Update
        elo_diff = home_elo + HOME_ADVANTAGE - away_elo
        p_home = 1 / (1 + 10 ** (-elo_diff / 400))
        
        if row.home_team_wins == 1.0:
            shift = K * mov_multiplier * (1 - p_home)
        else:
            shift = -K * mov_multiplier * p_home
        
        elo_ratings[home] = home_elo + shift
        elo_ratings[away] = away_elo - shift
    
    return elo_ratings.get(team, MEAN_ELO)


def generate_features_for_game(
    game_id: str,
    home_team: str,
    away_team: str,
    game_date: pd.Timestamp,
    session: Session
) -> Optional[dict]:
    """
    Generuje cechy (features) dla meczu bazując na historii
    """
    
    TEAM_MAP = {
        "Oklahoma C": "OKC", "San Antoni": "SAS",
        "New York K": "NYK", "Cleveland ": "CLE",
    }

    def _compute_derived(df):
        for prefix in ("home_", "away_"):
            fgm = df[f"{prefix}fgm"]
            fga = df[f"{prefix}fga"]
            fg3m = df[f"{prefix}fg3m"]
            ftm = df[f"{prefix}ftm"]
            fta = df[f"{prefix}fta"]
            tov = df[f"{prefix}tov"]
            oreb = df[f"{prefix}oreb"]
            pts = 2 * fgm + fg3m + ftm
            poss = fga + 0.44 * fta - oreb + tov
            df[f"{prefix}pts"] = pts
            df[f"{prefix}efg"] = (fgm + 0.5 * fg3m) / fga.replace(0, np.nan)
            df[f"{prefix}ts"] = pts / (2 * (fga + 0.44 * fta)).replace(0, np.nan)
            df[f"{prefix}tov_rate"] = tov / (fga + 0.44 * fta + tov).replace(0, np.nan)
            df[f"{prefix}ortg"] = pts / poss.replace(0, np.nan) * 100
            df[f"{prefix}poss"] = poss
        opp_prefix = {"home_": "away_", "away_": "home_"}
        for prefix in ("home_", "away_"):
            opp = opp_prefix[prefix]
            df[f"{prefix}drtg"] = df[f"{opp}pts"] / df[f"{opp}poss"].replace(0, np.nan) * 100
            df[f"{prefix}pace"] = (df[f"{prefix}poss"] + df[f"{opp}poss"]) / 2
        return df

    try:
        # Mapowanie nazw drużyn z Odds API na kody NBA
        home_team = TEAM_MAP.get(home_team, home_team)
        away_team = TEAM_MAP.get(away_team, away_team)

        # Normalizacja game_date do pd.Timestamp
        if not isinstance(game_date, pd.Timestamp):
            game_date = pd.Timestamp(game_date)
        game_date_str = game_date.strftime("%Y-%m-%d")

        # Wczytujemy wszystkie mecze z bazy (do cachowania)
        query = text("SELECT * FROM games WHERE game_date <= :date ORDER BY game_date ASC")
        df_games = pd.read_sql(query, con=session.connection(), params={"date": game_date_str})
        
        if df_games.empty:
            logger.error(f"Brak meczów w bazie dla {home_team} vs {away_team}")
            return None
        
        df_games["game_date"] = pd.to_datetime(df_games["game_date"])
        # Tylko zakończone mecze (mają wyniki i statystyki)
        df_games = df_games[df_games["home_score"].notna()].copy()
        if df_games.empty:
            logger.warning("Brak zakończonych meczów w bazie")
            return None
        df_games = _compute_derived(df_games)
        
        # Obliczamy cechy
        features = {}
        
        # 1. Forma z ostatnich 10 meczów
        home_form = calculate_team_form(df_games, home_team, game_date, num_recent_games=10)
        away_form = calculate_team_form(df_games, away_team, game_date, num_recent_games=10)
        
        features.update({f"home_{k}": v for k, v in home_form.items()})
        features.update({f"away_{k}": v for k, v in away_form.items()})
        
        # 2. Elo ratings
        home_elo = calculate_elo(df_games, home_team, game_date)
        away_elo = calculate_elo(df_games, away_team, game_date)
        
        features["home_elo"] = home_elo
        features["away_elo"] = away_elo
        features["elo_diff"] = home_elo - away_elo
        
        return features
    
    except Exception as e:
        logger.error(f"Błąd przy generowaniu cech: {e}")
        return None


def prob_to_min_decimal(prob: float) -> float:
    """Minimum decimal odds needed for positive EV given a probability"""
    if prob <= 0 or prob >= 1:
        return 0.0
    return round(1 / prob, 2)


def prob_to_min_american(prob: float) -> int:
    """Minimum American odds needed for positive EV"""
    dec = prob_to_min_decimal(prob)
    if dec <= 0:
        return 0
    if dec >= 2:
        return int(round((dec - 1) * 100))
    return int(round(-100 / (dec - 1)))


def predict_game(features: dict, feature_cols: list) -> dict:
    """
    Generuje predykcję dla gry używając modelu ML
    
    Returns:
        {
            "home_win_prob": float,
            "away_win_prob": float,
            "confidence": float,
            "min_home_odds_decimal": float,
            "min_away_odds_decimal": float,
            "min_home_odds_american": int,
            "min_away_odds_american": int,
        }
    """
    
    model, scaler, feature_cols_from_model = load_model()
    
    # Sprawdzamy czy mamy wszystkie cechy
    missing_cols = [col for col in feature_cols_from_model if col not in features or pd.isna(features.get(col))]
    if missing_cols:
        logger.warning(f"Brakuje cech: {missing_cols}")
        return {
            "home_win_prob": 0.5,
            "away_win_prob": 0.5,
            "confidence": 0.5,
            "min_home_odds_decimal": 0.0,
            "min_away_odds_decimal": 0.0,
            "min_home_odds_american": 0,
            "min_away_odds_american": 0,
        }
    
    # Przygotowujemy dane do predykcji
    X = np.array([[features[col] for col in feature_cols_from_model]])
    
    # Skalowanie
    X_scaled = scaler.transform(X)
    
    # Predykcja
    proba = model.predict_proba(X_scaled)[0]  # [prob_away_wins, prob_home_wins]
    home_win_prob = proba[1]
    away_win_prob = proba[0]
    confidence = max(home_win_prob, away_win_prob)
    
    return {
        "home_win_prob": float(home_win_prob),
        "away_win_prob": float(away_win_prob),
        "confidence": float(confidence),
        "min_home_odds_decimal": prob_to_min_decimal(home_win_prob),
        "min_away_odds_decimal": prob_to_min_decimal(away_win_prob),
        "min_home_odds_american": prob_to_min_american(home_win_prob),
        "min_away_odds_american": prob_to_min_american(away_win_prob),
    }
