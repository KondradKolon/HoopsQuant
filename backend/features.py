import numpy as np
import pandas as pd
from sqlalchemy import text
from database import engine

print("[FEAT] Wczytywanie meczów z bazy...")

all_games = pd.read_sql(
    text("SELECT * FROM games ORDER BY game_date ASC"),
    con=engine,
)


text_columns = {"id", "game_id", "game_date", "season", "home_team", "away_team"}
numeric_columns = [col for col in all_games.columns if col not in text_columns]
all_games[numeric_columns] = all_games[numeric_columns].astype(float)
all_games["game_date"] = pd.to_datetime(all_games["game_date"])

# Target
all_games["label"] = np.where(all_games["home_team_wins"] == 1.0, 1, 0)

print(
    f"[FEAT] Wczytano {len(all_games)} meczów z sezonów: {sorted(all_games['season'].unique())}"
)


# ─────────────────────────────────────────────────────────────────────────────
# KROK 2: PODSTAWOWE RÓŻNICE STATYSTYK
# ─────────────────────────────────────────────────────────────────────────────

print("[FEAT] Obliczanie różnic statystyk...")

all_games["score_difference"] = all_games["home_score"] - all_games["away_score"]
all_games["field_goal_pct_diff"] = all_games["home_fg_pct"] - all_games["away_fg_pct"]
all_games["three_point_pct_diff"] = (
    all_games["home_fg3_pct"] - all_games["away_fg3_pct"]
)
all_games["rebounds_difference"] = all_games["home_reb"] - all_games["away_reb"]
all_games["assists_difference"] = all_games["home_ast"] - all_games["away_ast"]
all_games["turnovers_difference"] = all_games["home_tov"] - all_games["away_tov"]
all_games["is_home_team"] = 1.0


# ─────────────────────────────────────────────────────────────────────────────
# KROK 3: ADVANCED STATS PER-POSSESSION
# ─────────────────────────────────────────────────────────────────────────────
#
# ORtg  = 100 * pts / possessions
# DRtg  = 100 * opp_pts / possessions
# Pace  = possessions per game (przybliżenie bez minut)
# eFG%  = (FGM + 0.5*FG3M) / FGA   ← lepsze niż FG%, uwzględnia wartość trójki
# TS%   = pts / (2 * (FGA + 0.44*FTA))
#
# Posiadania (Hollinger approximation):
#   poss = FGA - OREB + TOV + 0.44*FTA
# ─────────────────────────────────────────────────────────────────────────────

print("[FEAT] Obliczanie advanced stats (ORtg, DRtg, Pace, eFG%, TS%)...")

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

# Różnice advanced
all_games["ortg_diff"]     = all_games["home_ortg"]  - all_games["away_ortg"]
all_games["drtg_diff"]     = all_games["home_drtg"]  - all_games["away_drtg"]
all_games["efg_diff"]      = all_games["home_efg"]   - all_games["away_efg"]
all_games["ts_diff"]       = all_games["home_ts"]    - all_games["away_ts"]
all_games["pace_diff"]     = all_games["home_pace"]  - all_games["away_pace"]
all_games["tov_rate_diff"] = all_games["home_tov_rate"] - all_games["away_tov_rate"]


# ─────────────────────────────────────────────────────────────────────────────
# KROK 4: FORMA DRUŻYNY — ROLLING MEAN (last5, last10) BEZ LOOK-AHEAD
# ─────────────────────────────────────────────────────────────────────────────

COLUMNS_TO_AVERAGE = [
    "home_fgm", "home_fga", "home_fg_pct", "home_fg3_pct",
    "home_reb", "home_ast", "home_tov", "home_stl", "home_blk",
    "home_score",
    # Advanced stats
    "home_ortg", "home_drtg", "home_efg", "home_ts", "home_pace",
]


def calculate_team_form(games: pd.DataFrame, num_recent_games: int) -> pd.DataFrame:
    """
    Dodaje kolumny z formą drużyny (rolling mean z ostatnich N meczów).
    Używa .shift(1) żeby nie "patrzeć" na bieżący mecz.
    """
    averaged_column_names = [
        f"{col.replace('home_', '')}_last{num_recent_games}"
        for col in COLUMNS_TO_AVERAGE
    ]
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
        .loc[all_team_games["team"].isin(games["home_team"])][
            ["game_id", "team"] + averaged_column_names
        ]
        .rename(columns={col: f"home_{col}" for col in averaged_column_names})
    )
    away_team_form = (
        all_team_games[all_team_games["game_id"].isin(games["game_id"])]
        .loc[all_team_games["team"].isin(games["away_team"])][
            ["game_id", "team"] + averaged_column_names
        ]
        .rename(columns={col: f"away_{col}" for col in averaged_column_names})
    )

    games = games.merge(
        home_team_form.rename(columns={"team": "home_team"}),
        on=["game_id", "home_team"], how="left",
    )
    games = games.merge(
        away_team_form.rename(columns={"team": "away_team"}),
        on=["game_id", "away_team"], how="left",
    )
    return games


print("[FEAT] Obliczanie formy z ostatnich 5 meczów...")
all_games = calculate_team_form(all_games, num_recent_games=5)
print("[FEAT] Obliczanie formy z ostatnich 10 meczów...")
all_games = calculate_team_form(all_games, num_recent_games=10)


# ─────────────────────────────────────────────────────────────────────────────
# KROK 5: DNI ODPOCZYNKU + BACK-TO-BACK FLAG
# ─────────────────────────────────────────────────────────────────────────────

def calculate_rest_days(games: pd.DataFrame) -> pd.DataFrame:
    home_games = games[["game_id", "game_date", "home_team"]].copy()
    home_games.columns = ["game_id", "game_date", "team"]
    away_games = games[["game_id", "game_date", "away_team"]].copy()
    away_games.columns = ["game_id", "game_date", "team"]

    all_team_games = pd.concat([home_games, away_games], ignore_index=True)
    all_team_games["game_date"] = pd.to_datetime(all_team_games["game_date"])
    all_team_games = all_team_games.sort_values(["team", "game_date"]).reset_index(drop=True)
    all_team_games["rest_days"] = (
        all_team_games.groupby("team")["game_date"].diff().dt.days.fillna(3)
    )

    home_rest = all_team_games[["game_id", "team", "rest_days"]].rename(
        columns={"team": "home_team", "rest_days": "home_rest_days"}
    )
    away_rest = all_team_games[["game_id", "team", "rest_days"]].rename(
        columns={"team": "away_team", "rest_days": "away_rest_days"}
    )

    games = games.merge(home_rest, on=["game_id", "home_team"], how="left")
    games = games.merge(away_rest, on=["game_id", "away_team"], how="left")

    # Back-to-back flag: grają drugi dzień z rzędu (1 dzień lub mniej przerwy)
    games["home_is_b2b"] = (games["home_rest_days"] <= 1).astype(float)
    games["away_is_b2b"] = (games["away_rest_days"] <= 1).astype(float)
    games["rest_days_diff"] = games["home_rest_days"] - games["away_rest_days"]

    return games


print("[FEAT] Obliczanie dni odpoczynku i back-to-back...")
all_games = calculate_rest_days(all_games)


# ─────────────────────────────────────────────────────────────────────────────
# KROK 6: ELO RATING
# ─────────────────────────────────────────────────────────────────────────────
#
# Elo: prosty system rankingowy który śledzi "siłę" drużyny w czasie.
# Po każdym meczu:
#   winner_elo += K * (1 - P_winner)   gdzie P = sigmoid(elo_diff / 400)
#   loser_elo  -= K * (1 - P_winner)
# K = 20 (standardowe NBA)
# Home court advantage: +100 Elo punktów dla gospodarza (stała NBA)
#
# Ważne: zapisujemy Elo PRE-GAME (przed meczem) jako feature —
# żeby nie mieć look-ahead bias
# ─────────────────────────────────────────────────────────────────────────────

print("[FEAT] Obliczanie Elo ratings...")

K = 20
HOME_ADVANTAGE = 100  # Elo punktów przewagi gospodarza

elo_ratings: dict[str, float] = {}  # team → bieżące Elo

home_elos = []
away_elos = []

for _, row in all_games.iterrows():
    home = row["home_team"]
    away = row["away_team"]

    home_elo = elo_ratings.get(home, 1500.0)
    away_elo = elo_ratings.get(away, 1500.0)

    # Zapisz PRE-GAME Elo (to będzie feature)
    home_elos.append(home_elo)
    away_elos.append(away_elo)

    # Oczekiwana wygrana gospodarza (z uwzgl. przewagi domowej)
    p_home = 1 / (1 + 10 ** (-(home_elo + HOME_ADVANTAGE - away_elo) / 400))

    # Aktualizacja po meczu
    if row["home_team_wins"] == 1.0:
        home_elo += K * (1 - p_home)
        away_elo -= K * (1 - p_home)
    else:
        home_elo -= K * p_home
        away_elo += K * p_home

    elo_ratings[home] = home_elo
    elo_ratings[away] = away_elo

all_games["home_elo"] = home_elos
all_games["away_elo"] = away_elos
all_games["elo_diff"] = all_games["home_elo"] - all_games["away_elo"]
all_games["elo_win_prob"] = 1 / (
    1 + 10 ** (-(all_games["home_elo"] + HOME_ADVANTAGE - all_games["away_elo"]) / 400)
)


# ─────────────────────────────────────────────────────────────────────────────
# KROK 7: MATCHUP FEATURES
# ─────────────────────────────────────────────────────────────────────────────
#
# Jak dobrze ofensywa gospodarza radzi sobie z defensywą gości?
# Używamy rolling DRtg rywala (last10) jako proxy "siły defensywy"
# a rolling ORtg drużyny jako "siły ataku"
#
# offense_vs_defense_ratio:
#   > 1.0 → gospodarz atakuje lepiej niż rywal broni
#   < 1.0 → rywal broni lepiej niż gospodarz atakuje
# ─────────────────────────────────────────────────────────────────────────────

print("[FEAT] Obliczanie matchup features...")

# home offense vs away defense
all_games["matchup_home_off_vs_away_def"] = (
    all_games["home_ortg_last10"] / (all_games["away_drtg_last10"] + EPS)
)
# away offense vs home defense
all_games["matchup_away_off_vs_home_def"] = (
    all_games["away_ortg_last10"] / (all_games["home_drtg_last10"] + EPS)
)
# Pace matchup — czy duże tempo czy małe?
all_games["matchup_pace"] = (
    all_games["home_pace_last10"] + all_games["away_pace_last10"]
) / 2

# Net matchup: ilu punktów przewagi spodziewa się model wyłącznie z matchupów
all_games["matchup_net"] = (
    all_games["matchup_home_off_vs_away_def"]
    - all_games["matchup_away_off_vs_home_def"]
)


# ─────────────────────────────────────────────────────────────────────────────
# KROK 8: ZAPIS DO CSV
# ─────────────────────────────────────────────────────────────────────────────

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
