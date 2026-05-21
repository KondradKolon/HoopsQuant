"""
Elo Rankings API Route
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.db.models import Game
from app.services.predictions import calculate_elo
import pandas as pd

router = APIRouter(prefix="/api/v1/elo", tags=["elo"])

NBA_CONFERENCES = {
    "east": {"BOS", "NYK", "BKN", "PHI", "TOR", "CLE", "MIL", "IND", "CHI", "DET", "MIA", "ATL", "CHA", "ORL", "WAS"},
    "west": {"DEN", "MIN", "OKC", "POR", "UTA", "LAL", "LAC", "GSW", "SAC", "PHX", "DAL", "HOU", "SAS", "MEM", "NOP"},
}


@router.get("/rankings")
async def get_elo_rankings(
    conference: str = Query("all", regex="^(east|west|all)$"),
    season: str = Query("2025-26"),
    db: Session = Depends(get_db),
):
    """Get Elo rankings for all NBA teams"""
    try:
        games = db.query(Game).filter(
            Game.season == season,
            Game.home_score.isnot(None),
        ).order_by(Game.game_date).all()

        if not games:
            return {"teams": [], "season": season, "conference": conference}

        games_data = []
        for g in games:
            games_data.append({
                "game_date": pd.to_datetime(g.game_date),
                "season": g.season,
                "home_team": g.home_team,
                "away_team": g.away_team,
                "home_score": g.home_score,
                "away_score": g.away_score,
                "home_team_wins": float(g.home_team_wins) if g.home_team_wins is not None else None,
            })

        df = pd.DataFrame(games_data)
        df = df.dropna(subset=["home_team_wins"])
        if df.empty:
            return {"teams": [], "season": season, "conference": conference}

        all_teams = set(df["home_team"].unique()) | set(df["away_team"].unique())
        latest_date = df["game_date"].max()

        rankings = []
        for team in sorted(all_teams):
            elo = calculate_elo(df, team, latest_date + pd.Timedelta(days=1))

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

        return {
            "teams": rankings,
            "season": season,
            "conference": conference,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute Elo rankings: {str(e)}",
        )
