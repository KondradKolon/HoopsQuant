import joblib
import argparse
import pandas as pd
from datetime import date, datetime
from typing import List, Optional
from dataclasses import dataclass

from sqlalchemy.orm import joinedload
from database import SessionLocal
from models import Game, Odds

@dataclass
class BetRecord:
    game_date: date
    team_bet_on: str
    odds_taken: float
    model_prob: float
    implied_prob: float
    ev_edge: float
    bet_won: bool
    profit_loss: float


def calculate_ev(model_probability: float, decimal_odds: float) -> float:
    """Returns the Expected Value (Edge) margin. > 0 means profitable long-term."""
    if not decimal_odds or decimal_odds <= 0:
        return -1.0
    return (model_probability * decimal_odds) - 1.0


def find_best_odds(odds_list: List[Odds], team_side: str, allowed_books: set) -> float:
    """Finds the highest available odds for a specific side across allowed bookmakers."""
    valid_odds = [
        getattr(o, f"{team_side}_win_odds") 
        for o in odds_list 
        if getattr(o, f"{team_side}_win_odds") > 0 
        and (not allowed_books or o.bookmaker in allowed_books)
    ]
    return max(valid_odds) if valid_odds else 0.0


def run_simulation(
    features_df: pd.DataFrame, 
    model, 
    scaler, 
    feature_cols: list, 
    min_edge: float, 
    stake_size: float,
    allowed_books: set
) -> List[BetRecord]:
    
    bet_history = []
    
    # Scale features and predict all probabilities at once for efficiency
    X = features_df[feature_cols]
    X_scaled = pd.DataFrame(scaler.transform(X), columns=feature_cols)
    features_df['home_win_prob'] = model.predict_proba(X_scaled)[:, 1]
    features_df['away_win_prob'] = 1.0 - features_df['home_win_prob']

    with SessionLocal() as db:
        # Fetch all games in the dataset date range with their odds
        start_dt = features_df['game_date'].min()
        end_dt = features_df['game_date'].max()
        
        db_games = {
            (g.game_date, g.home_team, g.away_team): g
            for g in db.query(Game).options(joinedload(Game.odds))
            .filter(Game.game_date >= start_dt, Game.game_date <= end_dt).all()
        }

    for _, row in features_df.iterrows():
        game_key = (row['game_date'].date(), row['home_team'], row['away_team'])
        db_game = db_games.get(game_key)
        
        if not db_game or not db_game.odds:
            continue

        best_home_odds = find_best_odds(db_game.odds, "home", allowed_books)
        best_away_odds = find_best_odds(db_game.odds, "away", allowed_books)

        home_ev = calculate_ev(row['home_win_prob'], best_home_odds)
        away_ev = calculate_ev(row['away_win_prob'], best_away_odds)

        actual_home_won = bool(row['label'] == 1)

        # Check if we have a valid bet on the HOME team
        if home_ev > min_edge and best_home_odds > 0:
            profit = (best_home_odds * stake_size) - stake_size if actual_home_won else -stake_size
            bet_history.append(BetRecord(
                game_date=row['game_date'].date(),
                team_bet_on=row['home_team'],
                odds_taken=best_home_odds,
                model_prob=row['home_win_prob'],
                implied_prob=1.0 / best_home_odds,
                ev_edge=home_ev,
                bet_won=actual_home_won,
                profit_loss=profit
            ))

        # Check if we have a valid bet on the AWAY team
        elif away_ev > min_edge and best_away_odds > 0:
            profit = (best_away_odds * stake_size) - stake_size if not actual_home_won else -stake_size
            bet_history.append(BetRecord(
                game_date=row['game_date'].date(),
                team_bet_on=row['away_team'],
                odds_taken=best_away_odds,
                model_prob=row['away_win_prob'],
                implied_prob=1.0 / best_away_odds,
                ev_edge=away_ev,
                bet_won=not actual_home_won,
                profit_loss=profit
            ))

    return bet_history


def print_report(bets: List[BetRecord], stake: float):
    if not bets:
        print("\n❌ No bets met the EV threshold. Model found no edge.")
        return

    total_bets = len(bets)
    wins = sum(1 for b in bets if b.bet_won)
    win_rate = wins / total_bets
    total_staked = total_bets * stake
    total_profit = sum(b.profit_loss for b in bets)
    roi = (total_profit / total_staked) * 100

    print("\n" + "="*50)
    print("💰 MODEL PROFITABILITY REPORT 💰")
    print("="*50)
    print(f"Total Bets Placed : {total_bets}")
    print(f"Bets Won          : {wins} ({win_rate:.2%})")
    print(f"Total Staked      : ${total_staked:.2f}")
    print(f"Net Profit / Loss : ${total_profit:.2f}")
    print(f"R.O.I.            : {roi:.2f}%")
    print("="*50)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-start", default="2024-09-01", help="Start date for backtesting")
    parser.add_argument("--test-end", default="2025-06-01", help="End date for backtesting")
    parser.add_argument("--min-edge", type=float, default=0.02, help="Minimum EV required to bet (e.g. 0.02 = 2%)")
    parser.add_argument("--stake", type=float, default=100.0, help="Flat bet size per game")
    parser.add_argument("--bookmakers", nargs="*", default=None, help="Filter specific bookmakers")
    args = parser.parse_args()

    print("[1] Loading Model and Data...")
    model = joblib.load("model.pkl")
    scaler = joblib.load("scaler.pkl")
    feature_cols = joblib.load("feature_cols.pkl")
    
    df = pd.read_csv("features.csv", parse_dates=["game_date"])
    df = df[(df["game_date"] >= args.test_start) & (df["game_date"] < args.test_end)]
    df = df.dropna(subset=feature_cols + ["label"])

    print(f"[2] Simulating bets over {len(df)} matches...")
    bets = run_simulation(
        features_df=df,
        model=model,
        scaler=scaler,
        feature_cols=feature_cols,
        min_edge=args.min_edge,
        stake_size=args.stake,
        allowed_books=set(args.bookmakers or [])
    )

    print_report(bets, args.stake)


if __name__ == "__main__":
    main()