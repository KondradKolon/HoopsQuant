"""
features.py — Feature Engineering dla Modelów NBA
 
Wczytuje mecze z bazy, oblicza:
  - Formę (ostatnie 5/10 meczów)
  - Dni odpoczynku i B2B
  - Elo ratings z MoV multiplier
  - Advanced stats (ORtg, DRtg, eFG%, TS%, Pace, TOV Rate)
  - Matchup features
  
Output: features.csv (używany przez train.py do trenowania)
"""

import sys
from pathlib import Path

# Dodaj backend do ścieżki
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import numpy as np
import pandas as pd
from sqlalchemy import text
from app.db.database import engine

print("[FEAT] Wczytywanie meczów z bazy...")
query = text("""
    SELECT * FROM games 
    WHERE game_date >= '2022-01-01' 
    ORDER BY game_date ASC
""")

all_games = pd.read_sql(query, con=engine)

text_columns = {"id", "game_id", "game_date", "season", "home_team", "away_team"}
numeric_columns = [col for col in all_games.columns if col not in text_columns]
all_games[numeric_columns] = all_games[numeric_columns].astype(float)
all_games["game_date"] = pd.to_datetime(all_games["game_date"])

all_games["label"] = np.where(all_games["home_team_wins"] == 1.0, 1, 0)

print(
    f"[FEAT] Wczytano {len(all_games)} meczów z sezonów: {sorted(all_games['season'].unique())}"
)

print("[FEAT] Obliczanie różnic statystyk...")

all_games["score_difference"] = all_games["home_score"] - all_games["away_score"]
all_games["field_goal_pct_diff"] = all_games["home_fg_pct"] - all_games["away_fg_pct"]
all_games["three_point_pct_diff"] = all_games["home_fg3_pct"] - all_games["away_fg3_pct"]
all_games["rebounds_difference"] = all_games["home_reb"] - all_games["away_reb"]
all_games["assists_difference"] = all_games["home_ast"] - all_games["away_ast"]
all_games["turnovers_difference"] = all_games["home_tov"] - all_games["away_tov"]
all_games["is_home_team"] = 1.0

print("[FEAT] Obliczanie advanced stats (ORtg, DRtg, Pace, eFG%, TS%, TOV Rate)...")

EPS = 1e-9  # uniknięcie dzielenia przez zero

for side in ("home", "away"):
    opp = "away" if side == "home" else "home"

    fgm  = all_games[f"{side}_fgm"]
    fga  = all_games[f"{side}_fga"]
    fg3m = all_games[f"{side}_fg3m"]
    ftm  = all_games[f"{side}_ftm"]
    fta  = all_games[f"{side}_fta"]
    oreb = all_games[f"{side}_oreb"]
    tov  = all_games[f"{side}_tov"]
    pts  = all_games[f"{side}_score"]
    opp_pts = all_games[f"{opp}_score"]

    poss = fga - oreb + tov + 0.44 * fta

    all_games[f"{side}_poss"]  = poss
    all_games[f"{side}_ortg"]  = 100 * pts     / (poss + EPS)
    all_games[f"{side}_drtg"]  = 100 * opp_pts / (poss + EPS)
    all_games[f"{side}_efg"]   = (fgm + 0.5 * fg3m) / (fga + EPS)
    all_games[f"{side}_ts"]    = pts / (2 * (fga + 0.44 * fta) + EPS)
    all_games[f"{side}_pace"]  = poss  # pace przybliżone (bez normalizacji minut)
    all_games[f"{side}_tov_rate"] = tov / (poss + EPS)

all_games["ortg_diff"]     = all_games["home_ortg"]  - all_games["away_ortg"]
all_games["drtg_diff"]     = all_games["home_drtg"]  - all_games["away_drtg"]
all_games["efg_diff"]      = all_games["home_efg"]   - all_games["away_efg"]
all_games["ts_diff"]       = all_games["home_ts"]    - all_games["away_ts"]
all_games["pace_diff"]     = all_games["home_pace"]  - all_games["away_pace"]
all_games["tov_rate_diff"] = all_games["home_tov_rate"] - all_games["away_tov_rate"]

# UWAGA: Usunięto fgm, fga, fg_pct, fg3_pct, score i zwykłe tov. 
# Zostawiamy tylko zaawansowane metryki i kluczowe surowe (reb, ast, stl, blk), aby uniknąć współliniowości!
COLUMNS_TO_AVERAGE = [
    "home_reb", "home_ast", "home_stl", "home_blk", "home_tov_rate",
    "home_ortg", "home_drtg", "home_efg", "home_ts", "home_pace",
]

def calculate_team_form(games: pd.DataFrame, num_recent_games: int) -> pd.DataFrame:
    averaged_column_names = [f"{col.replace('home_', '')}_last{num_recent_games}" for col in COLUMNS_TO_AVERAGE]
    stat_names = [col.replace("home_", "") for col in COLUMNS_TO_AVERAGE]

    home_games = games[["game_id", "game_date", "home_team"] + COLUMNS_TO_AVERAGE].copy()
    home_games.columns = ["game_id", "game_date", "team"] + stat_names

    away_stat_columns = [col.replace("home_", "away_") for col in COLUMNS_TO_AVERAGE]
    away_games = games[["game_id", "game_date", "away_team"] + away_stat_columns].copy()
    away_games.columns = ["game_id", "game_date", "team"] + stat_names

    all_team_games = pd.concat([home_games, away_games], ignore_index=True)
    all_team_games = all_team_games.sort_values(["team", "game_date"]).reset_index(drop=True)

    team_form_averages = all_team_games.groupby("team")[stat_names].transform(
        lambda col: col.rolling(num_recent_games, min_periods=1).mean().shift(1)
    )
    all_team_games[averaged_column_names] = team_form_averages

    home_team_form = (
        all_team_games[all_team_games["game_id"].isin(games["game_id"])]
        .loc[all_team_games["team"].isin(games["home_team"])][["game_id", "team"] + averaged_column_names]
        .rename(columns={col: f"home_{col}" for col in averaged_column_names})
    )
    away_team_form = (
        all_team_games[all_team_games["game_id"].isin(games["game_id"])]
        .loc[all_team_games["team"].isin(games["away_team"])][["game_id", "team"] + averaged_column_names]
        .rename(columns={col: f"away_{col}" for col in averaged_column_names})
    )

    games = games.merge(home_team_form.rename(columns={"team": "home_team"}), on=["game_id", "home_team"], how="left")
    games = games.merge(away_team_form.rename(columns={"team": "away_team"}), on=["game_id", "away_team"], how="left")
    
    return games

print("[FEAT] Obliczanie formy z ostatnich 5 meczów...")
all_games = calculate_team_form(all_games, num_recent_games=5)
print("[FEAT] Obliczanie formy z ostatnich 10 meczów...")
all_games = calculate_team_form(all_games, num_recent_games=10)

def calculate_rest_days(games: pd.DataFrame) -> pd.DataFrame:
    home_games = games[["game_id", "game_date", "home_team"]].copy()
    home_games.columns = ["game_id", "game_date", "team"]
    away_games = games[["game_id", "game_date", "away_team"]].copy()
    away_games.columns = ["game_id", "game_date", "team"]

    all_team_games = pd.concat([home_games, away_games], ignore_index=True)
    all_team_games["game_date"] = pd.to_datetime(all_team_games["game_date"])
    all_team_games = all_team_games.sort_values(["team", "game_date"]).reset_index(drop=True)
    
    # Clip upper limit na 7 zabezpiecza przed off-season outlierami
    all_team_games["rest_days"] = all_team_games.groupby("team")["game_date"].diff().dt.days.fillna(3).clip(upper=7)

    home_rest = all_team_games[["game_id", "team", "rest_days"]].rename(columns={"team": "home_team", "rest_days": "home_rest_days"})
    away_rest = all_team_games[["game_id", "team", "rest_days"]].rename(columns={"team": "away_team", "rest_days": "away_rest_days"})

    games = games.merge(home_rest, on=["game_id", "home_team"], how="left")
    games = games.merge(away_rest, on=["game_id", "away_team"], how="left")

    games["home_is_b2b"] = (games["home_rest_days"] <= 1).astype(float)
    games["away_is_b2b"] = (games["away_rest_days"] <= 1).astype(float)
    games["rest_days_diff"] = games["home_rest_days"] - games["away_rest_days"]

    return games

print("[FEAT] Obliczanie dni odpoczynku i back-to-back...")
all_games = calculate_rest_days(all_games)

print("[FEAT] Obliczanie Elo ratings z regresją do średniej i Margin of Victory (MoV)...")

K = 20
HOME_ADVANTAGE = 50
MEAN_ELO = 1500.0
REGRESSION_FACTOR = 0.80  # 80% carryover z poprzedniego sezonu, 20% resetu do 1500

elo_ratings: dict[str, float] = {}  

home_elos = []
away_elos = []

current_season = None

for row in all_games.itertuples():
    # 1. Regresja do średniej na starcie nowego sezonu
    if current_season is not None and row.season != current_season:
        for team in elo_ratings:
            elo_ratings[team] = (elo_ratings[team] * REGRESSION_FACTOR) + (MEAN_ELO * (1 - REGRESSION_FACTOR))
    
    current_season = row.season

    # 2. Pobranie bieżącego Elo (przed meczem)
    home = row.home_team
    away = row.away_team

    home_elo = elo_ratings.get(home, MEAN_ELO)
    away_elo = elo_ratings.get(away, MEAN_ELO)

    home_elos.append(home_elo)
    away_elos.append(away_elo)

    # 3. Prawdopodobieństwo wygranej (na bazie Elo diff)
    elo_diff = home_elo + HOME_ADVANTAGE - away_elo
    p_home = 1 / (1 + 10 ** (-elo_diff / 400))

    # ==========================================
    # 4. MARGIN OF VICTORY (MoV) MULTIPLIER
    # ==========================================
    score_diff = abs(row.home_score - row.away_score)
    
    # Kto był faworytem, a kto underdogiem w oczach Elo?
    if row.home_team_wins == 1.0:
        winner_elo = home_elo + HOME_ADVANTAGE
        loser_elo = away_elo
    else:
        winner_elo = away_elo
        loser_elo = home_elo + HOME_ADVANTAGE
        
    elo_diff_winner = winner_elo - loser_elo
    
    # Klasyczny mnożnik MoV dla koszykówki 
    # (zabezpieczenie przed ujemnym mianownikiem przy ogromnych upsetach)
    mov_multiplier = ((score_diff + 3) ** 0.8) / (7.5 + 0.006 * elo_diff_winner)
    # ==========================================

    # 5. Aktualizacja po meczu (z uwzględnieniem mnożnika!)
    if row.home_team_wins == 1.0:
        shift = K * mov_multiplier * (1 - p_home)
    else:
        shift = -K * mov_multiplier * p_home 

    elo_ratings[home] = home_elo + shift
    elo_ratings[away] = away_elo - shift

# Przypisanie do DataFrame
all_games["home_elo"] = home_elos
all_games["away_elo"] = away_elos
all_games["elo_diff"] = all_games["home_elo"] - all_games["away_elo"]

all_games["elo_win_prob"] = 1 / (
    1 + 10 ** (-(all_games["home_elo"] + HOME_ADVANTAGE - all_games["away_elo"]) / 400)
)

print("[FEAT] Obliczanie matchup features...")

# Czyste odejmowanie - bez niepotrzebnego EPS
all_games["matchup_home_off_vs_away_def"] = all_games["home_ortg_last10"] - all_games["away_drtg_last10"]
all_games["matchup_away_off_vs_home_def"] = all_games["away_ortg_last10"] - all_games["home_drtg_last10"]

all_games["matchup_pace"] = (all_games["home_pace_last10"] + all_games["away_pace_last10"]) / 2
all_games["matchup_net"] = all_games["matchup_home_off_vs_away_def"] - all_games["matchup_away_off_vs_home_def"]

output_file = "features.csv"
all_games.to_csv(output_file, index=False)

form_columns = [col for col in all_games.columns if "last" in col]
adv_columns  = [col for col in all_games.columns if any(
    x in col for x in ["ortg", "drtg", "efg", "ts_", "elo", "matchup", "b2b"]
)]

print(f"\n[FEAT] Zapis do {output_file}")
print(f"       Łącznie: {len(all_games)} meczów × {all_games.shape[1]} kolumn")
print(f"       Kolumny z formą ({len(form_columns)} szt.): {form_columns[:4]} ...")
print(f"       Advanced stats ({len(adv_columns)} szt.): {adv_columns[:6]} ...")
print(f"       Gospodarz wygrał: {all_games['label'].mean():.1%} meczów")
print(f"       Elo diff (mean): {all_games['elo_diff'].mean():.1f}  std: {all_games['elo_diff'].std():.1f}")
