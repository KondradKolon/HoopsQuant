"""
PIPELINE:
    nba_client.fetch_season(season)      ← 2460 wierszy (2 per mecz)
          ↓
    _merge_home_away(raw_df)             ← 1230 wierszy (pełne statystyki)
          ↓
    _build_game_objects(merged_df)       ← lista obiektów Game (SQLAlchemy)
          ↓
    _save_to_db(games, session)          ← INSERT do PostgreSQL

UŻYCIE:
    python seed.py                  # sezon domyślny: 2023-24
    python seed.py 2021-22          # konkretny sezon
    python seed.py 2021-22 2022-23  # wiele sezonów
    python seed.py --reset          # wyczyść tabelę i zacznij od nowa
"""

import sys
import pandas as pd
from datetime import datetime

from src.clients.nba_client import *
from src.db.database.database import SessionLocal, engine
from src.db.database.models import * 

DEFAULT_SEASONS = ["2023-24"]


# ── KROK 1: MERGE HOME + AWAY ─────────────────────────────────────────────


def _merge_home_away(raw: pd.DataFrame) -> pd.DataFrame:
    

    home = raw[raw["MATCHUP"].str.contains(r"vs\.", regex=True)].copy()
    away = raw[raw["MATCHUP"].str.contains(r"@", regex=True)].copy()

    merged = pd.merge(home, away, on="GAME_ID", suffixes=("_home", "_away"))

    print(f"[MERGE]  {len(home)} home + {len(away)} away → {len(merged)} meczy")
    return merged


# ── KROK 2: BUDUJ OBIEKTY SQLAlchemy ─────────────────────────────────────


def _build_game_objects(merged: pd.DataFrame, season: str) -> list[Game]:
    
    games = []

    for row in merged.itertuples(index=False):

        # Rozwiąż wynik: WL_home = "W" → gospodarz wygrał
        wl_home = getattr(row, "WL_home", None)
        won = (wl_home == "W") if wl_home else None

        # GAME_DATE może być stringiem "2023-10-24" lub datetime
        raw_date = getattr(row, "GAME_DATE_home", None)
        if isinstance(raw_date, str):
            game_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
        else:
            game_date = raw_date  # już datetime/date

        games.append(
            Game(
                game_id=str(row.GAME_ID),
                game_date=game_date,
                season=season,
                home_team=str(row.TEAM_ABBREVIATION_home),
                away_team=str(row.TEAM_ABBREVIATION_away),
                home_score=getattr(row, "PTS_home", None),
                away_score=getattr(row, "PTS_away", None),
                home_team_wins=won,
                # Home stats
                home_fgm=getattr(row, "FGM_home", None),
                home_fga=getattr(row, "FGA_home", None),
                home_fg_pct=getattr(row, "FG_PCT_home", None),
                home_fg3m=getattr(row, "FG3M_home", None),
                home_fg3a=getattr(row, "FG3A_home", None),
                home_fg3_pct=getattr(row, "FG3_PCT_home", None),
                home_ftm=getattr(row, "FTM_home", None),
                home_fta=getattr(row, "FTA_home", None),
                home_ft_pct=getattr(row, "FT_PCT_home", None),
                home_oreb=getattr(row, "OREB_home", None),
                home_dreb=getattr(row, "DREB_home", None),
                home_reb=getattr(row, "REB_home", None),
                home_ast=getattr(row, "AST_home", None),
                home_stl=getattr(row, "STL_home", None),
                home_blk=getattr(row, "BLK_home", None),
                home_tov=getattr(row, "TOV_home", None),
                home_pf=getattr(row, "PF_home", None),
                home_plus_minus=getattr(row, "PLUS_MINUS_home", None),
                # Away stats
                away_fgm=getattr(row, "FGM_away", None),
                away_fga=getattr(row, "FGA_away", None),
                away_fg_pct=getattr(row, "FG_PCT_away", None),
                away_fg3m=getattr(row, "FG3M_away", None),
                away_fg3a=getattr(row, "FG3A_away", None),
                away_fg3_pct=getattr(row, "FG3_PCT_away", None),
                away_ftm=getattr(row, "FTM_away", None),
                away_fta=getattr(row, "FTA_away", None),
                away_ft_pct=getattr(row, "FT_PCT_away", None),
                away_oreb=getattr(row, "OREB_away", None),
                away_dreb=getattr(row, "DREB_away", None),
                away_reb=getattr(row, "REB_away", None),
                away_ast=getattr(row, "AST_away", None),
                away_stl=getattr(row, "STL_away", None),
                away_blk=getattr(row, "BLK_away", None),
                away_tov=getattr(row, "TOV_away", None),
                away_pf=getattr(row, "PF_away", None),
                away_plus_minus=getattr(row, "PLUS_MINUS_away", None),
            )
        )

    return games


# ── KROK 3: ZAPIS DO BAZY ─────────────────────────────────────────────────


def _save_to_db(games: list[Game], session) -> int:
    
    # Pobierz game_id które już są w bazie
    existing_ids = {row[0] for row in session.query(Game.game_id).all()}

    # Filtruj — tylko nowe mecze
    new_games = [g for g in games if g.game_id not in existing_ids]

    if not new_games:
        print(f"[DB]     ℹ️  Brak nowych meczy — wszystkie już w bazie.")
        return 0

    session.add_all(new_games)
    session.commit()

    skipped = len(games) - len(new_games)
    if skipped:
        print(f"[DB]     ⏭️  Pominięto {skipped} duplikatów.")

    return len(new_games)


# ── PIPELINE ──────────────────────────────────────────────────────────────


def seed_season(season: str) -> None:
    """Jeden sezon: fetch → merge → build → save."""

    print(f"\n{'='*50}")
    print(f"  Sezon: {season}")
    print(f"{'='*50}")

    raw = fetch_season(season)
    merged = _merge_home_away(raw)
    games = _build_game_objects(merged, season)

    session = SessionLocal()
    try:
        saved = _save_to_db(games, session)
        print(f"[DB]     ✅ {saved} meczy zapisano.")
    except Exception as exc:
        session.rollback()
        print(f"[DB]     ❌ Błąd: {exc}")
        raise
    finally:
        session.close()


def reset_db() -> None:
    """Usuwa i odtwarza tabele — tylko do użytku w developmencie."""
    print("[RESET]  Usuwam stare tabele...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("[RESET]  Tabele odtworzone.")


# ── ENTRY POINT ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    if "--reset" in args:
        reset_db()
        args = [a for a in args if a != "--reset"]

    seasons = args if args else DEFAULT_SEASONS

    print(f"\n🏀  HoopsQuant — Seeding DB")
    print(f"    Sezony: {seasons}")

    for season in seasons:
        seed_season(season)

    print(f"\n✅  Gotowe.")
