"""
Elo Rankings API Route — rankings, historical trend, upcoming predictions
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.db.models import Game
from app.services.predictions import calculate_elo
import pandas as pd
from datetime import date

router = APIRouter(prefix="/api/v1/elo", tags=["elo"])

HOME_ADVANTAGE = 50

NBA_CONFERENCES = {
    "east": {"BOS", "NYK", "BKN", "PHI", "TOR", "CLE", "MIL", "IND", "CHI", "DET", "MIA", "ATL", "CHA", "ORL", "WAS"},
    "west": {"DEN", "MIN", "OKC", "POR", "UTA", "LAL", "LAC", "GSW", "SAC", "PHX", "DAL", "HOU", "SAS", "MEM", "NOP"},
}


def load_games_df(db: Session, season: str) -> pd.DataFrame:
    games = db.query(Game).filter(Game.season == season).order_by(Game.game_date).all()
    if not games:
        return pd.DataFrame()
    data = []
    for g in games:
        data.append({
            "game_date": pd.to_datetime(g.game_date),
            "season": g.season,
            "home_team": g.home_team,
            "away_team": g.away_team,
            "home_score": g.home_score,
            "away_score": g.away_score,
            "home_team_wins": float(g.home_team_wins) if g.home_team_wins is not None else None,
        })
    return pd.DataFrame(data)


def elo_prob(home_elo: float, away_elo: float) -> float:
    return 1 / (1 + 10 ** (-(home_elo + HOME_ADVANTAGE - away_elo) / 400))


def compute_team_record(df: pd.DataFrame, team: str):
    team_games = df[(df["home_team"] == team) | (df["away_team"] == team)]
    wins = 0
    losses = 0
    for _, row in team_games.iterrows():
        if row["home_team"] == team and row["home_team_wins"] == 1.0:
            wins += 1
        elif row["home_team"] == team and row["home_team_wins"] == 0.0:
            losses += 1
        elif row["away_team"] == team and row["home_team_wins"] == 0.0:
            wins += 1
        elif row["away_team"] == team and row["home_team_wins"] == 1.0:
            losses += 1
    return wins, losses


@router.get("/rankings")
async def get_elo_rankings(
    conference: str = Query("all", regex="^(east|west|all)$"),
    season: str = Query("2025-26"),
    db: Session = Depends(get_db),
):
    """Get Elo rankings for all NBA teams"""
    try:
        df = load_games_df(db, season)
        if df.empty:
            return {"teams": [], "season": season, "conference": conference}
        completed = df.dropna(subset=["home_team_wins"])
        if completed.empty:
            return {"teams": [], "season": season, "conference": conference}

        all_teams = set(completed["home_team"].unique()) | set(completed["away_team"].unique())
        latest_date = completed["game_date"].max()

        rankings = []
        for team in sorted(all_teams):
            elo = calculate_elo(completed, team, latest_date + pd.Timedelta(days=1))
            wins, losses = compute_team_record(completed, team)
            team_conf = "east" if team in NBA_CONFERENCES["east"] else "west"
            rankings.append({
                "team": team,
                "elo": round(elo, 1),
                "conference": team_conf,
                "wins": wins,
                "losses": losses,
                "win_pct": round(wins / (wins + losses), 3) if (wins + losses) > 0 else 0,
            })

        if conference != "all":
            rankings = [r for r in rankings if r["conference"] == conference]

        rankings.sort(key=lambda x: x["elo"], reverse=True)
        for i, r in enumerate(rankings):
            r["rank"] = i + 1

        return {"teams": rankings, "season": season, "conference": conference}

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/trend")
async def get_elo_trend(
    team: str = Query(..., min_length=2, max_length=5),
    season: str = Query("2025-26"),
    db: Session = Depends(get_db),
):
    """Get historical Elo trend for a single team over the season"""
    try:
        df = load_games_df(db, season)
        if df.empty:
            return {"team": team, "points": []}

        completed = df.dropna(subset=["home_team_wins"])
        if completed.empty:
            return {"team": team, "points": []}

        game_dates = sorted(completed["game_date"].unique())
        points = []
        for d in game_dates:
            elo = calculate_elo(completed, team, d)
            points.append({"date": d.strftime("%Y-%m-%d"), "elo": round(elo, 1)})

        return {"team": team, "points": points}

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/upcoming")
async def get_elo_upcoming(
    limit: int = Query(20, le=50),
    season: str = Query("2025-26"),
    db: Session = Depends(get_db),
):
    """Get upcoming games with Elo-based win probabilities"""
    try:
        df = load_games_df(db, season)
        completed = df.dropna(subset=["home_team_wins"])

        today = date.today()
        upcoming = db.query(Game).filter(
            Game.season == season,
            Game.home_score.is_(None),
            Game.game_date >= today,
        ).order_by(Game.game_date).limit(limit).all()

        if not upcoming:
            return {"games": []}

        if not completed.empty:
            latest_date = completed["game_date"].max()
            next_day = latest_date + pd.Timedelta(days=1)

        result = []
        for g in upcoming:
            pred = None
            if not completed.empty:
                home_elo = calculate_elo(completed, g.home_team, next_day)
                away_elo = calculate_elo(completed, g.away_team, next_day)
                prob = elo_prob(home_elo, away_elo)
                pred = {
                    "home_win_prob": round(prob, 3),
                    "away_win_prob": round(1 - prob, 3),
                    "home_elo": round(home_elo, 1),
                    "away_elo": round(away_elo, 1),
                }

            result.append({
                "game_id": g.game_id,
                "game_date": g.game_date.isoformat() if g.game_date else None,
                "home_team": g.home_team,
                "away_team": g.away_team,
                "prediction": pred,
            })

        return {"games": result}

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
