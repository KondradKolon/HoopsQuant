from fastapi import FastAPI, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import date

from database import engine, SessionLocal
import models

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="HoopsQuant API", version="0.2.0")


# ── PYDANTIC SCHEMA ──────────────────────────────────────────────────────────
# Pydantic definiuje kształt JSON który wychodzi z API.
# Oddzielony od modelu SQLAlchemy — możemy zwracać mniej lub więcej pól
# niż przechowujemy w bazie, niezależnie od siebie.
# model_config from_attributes: pozwala skonstruować ten model
# bezpośrednio z obiektu SQLAlchemy (bez ręcznego mapowania).


class GameResponse(BaseModel):
    id: int
    game_id: str
    game_date: date
    season: str

    home_team: str
    away_team: str

    # Wynik
    home_score: Optional[float]
    away_score: Optional[float]
    home_team_wins: Optional[bool]

    # Statystyki gospodarza
    home_fg_pct: Optional[float]
    home_fg3_pct: Optional[float]
    home_ft_pct: Optional[float]
    home_reb: Optional[float]
    home_ast: Optional[float]
    home_stl: Optional[float]
    home_blk: Optional[float]
    home_tov: Optional[float]
    home_plus_minus: Optional[float]

    # Statystyki gości
    away_fg_pct: Optional[float]
    away_fg3_pct: Optional[float]
    away_ft_pct: Optional[float]
    away_reb: Optional[float]
    away_ast: Optional[float]
    away_stl: Optional[float]
    away_blk: Optional[float]
    away_tov: Optional[float]
    away_plus_minus: Optional[float]

    model_config = {"from_attributes": True}


# ── DEPENDENCY: sesja bazy danych ────────────────────────────────────────────
# FastAPI woła get_db() automatycznie dla każdego requestu.
# yield = "daj sesję, po zakończeniu requestu wróć tu i zamknij"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── ENDPOINTS ────────────────────────────────────────────────────────────────


@app.get("/")
def read_root():
    return {"message": "HoopsQuant API v0.2.0 — full stats enabled"}


@app.get("/games", response_model=list[GameResponse])
def get_games(
    season: str = Query(default="2023-24", description="Sezon, np. 2023-24"),
    limit: int = Query(default=20, le=100, description="Max wyników (max 100)"),
    db: Session = Depends(get_db),
):
    """Zwraca listę meczy z pełnymi statystykami obu drużyn."""
    return (
        db.query(models.Game)
        .filter(models.Game.season == season)
        .order_by(models.Game.game_date)
        .limit(limit)
        .all()
    )


@app.get("/games/count")
def count_games(
    season: str = Query(default="2023-24"),
    db: Session = Depends(get_db),
):
    """Zwraca liczbę meczy w bazie dla danego sezonu."""
    count = db.query(models.Game).filter(models.Game.season == season).count()
    return {"season": season, "total_games": count}
