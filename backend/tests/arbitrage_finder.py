import argparse
from datetime import date, datetime
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.orm import joinedload

from database import SessionLocal
from models import Game, Odds


@dataclass
class BestOdd:
    bookmaker: str
    value: float


@dataclass
class ArbitrageOpportunity:
    game_date: date
    home_team: str
    away_team: str
    game_id: str
    home_bet: BestOdd
    away_bet: BestOdd
    profit_margin: float


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def get_implied_probability(decimal_odds: float) -> float:
    if not decimal_odds or decimal_odds <= 0:
        return float('inf')
    return 1.0 / decimal_odds


def find_best_odds(odds_list: List[Odds], team_side: str) -> Optional[BestOdd]:
    valid_odds = [o for o in odds_list if getattr(o, f"{team_side}_win_odds") and getattr(o, f"{team_side}_win_odds") > 0]
    if not valid_odds:
        return None
    
    best = max(valid_odds, key=lambda o: getattr(o, f"{team_side}_win_odds"))
    return BestOdd(bookmaker=best.bookmaker, value=getattr(best, f"{team_side}_win_odds"))


def evaluate_arbitrage(game: Game, available_odds: List[Odds]) -> Optional[ArbitrageOpportunity]:
    best_home = find_best_odds(available_odds, "home")
    best_away = find_best_odds(available_odds, "away")

    if not best_home or not best_away:
        return None

    implied_home = get_implied_probability(best_home.value)
    implied_away = get_implied_probability(best_away.value)
    total_implied_probability = implied_home + implied_away

    if total_implied_probability < 1.0:
        profit_margin = (1.0 / total_implied_probability - 1.0) * 100
        
        return ArbitrageOpportunity(
            game_date=game.game_date,
            home_team=game.home_team,
            away_team=game.away_team,
            game_id=game.game_id,
            home_bet=best_home,
            away_bet=best_away,
            profit_margin=profit_margin
        )
        
    return None


def print_arbitrage_report(opportunities: List[ArbitrageOpportunity]) -> None:
    if not opportunities:
        print("\n No arbitrage opportunities found for this period.")
        return

    print(f"\n  Found {len(opportunities)} Arbitrage Opportunities!\n" + "="*50)
    
    for arb in opportunities:
        print(f"\n {arb.away_team} @ {arb.home_team} | Date: {arb.game_date} | ID: {arb.game_id}")
        print(f"PROFIT MARGIN: {arb.profit_margin:.2f}%")
        print(f"   -> Bet HOME ({arb.home_team}) on {arb.home_bet.bookmaker} @ {arb.home_bet.value}")
        print(f"   -> Bet AWAY ({arb.away_team}) on {arb.away_bet.bookmaker} @ {arb.away_bet.value}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Find Arbitrage Opportunities in DB")
    parser.add_argument("--start", default="2026-01-01")
    parser.add_argument("--end", default="2026-02-01")
    parser.add_argument("--bookmakers", nargs="*", default=None)
    args = parser.parse_args()

    start_date = parse_date(args.start)
    end_date = parse_date(args.end)
    allowed_bookmakers = set(args.bookmakers or [])

    with SessionLocal() as db:
        games = (
            db.query(Game)
            .options(joinedload(Game.odds))
            .filter(Game.game_date >= start_date)
            .filter(Game.game_date < end_date)
            .order_by(Game.game_date.asc())
            .all()
        )

        found_arbitrages = []

        for game in games:
            game_odds = list(game.odds or [])
            
            if allowed_bookmakers:
                game_odds = [o for o in game_odds if o.bookmaker in allowed_bookmakers]

            if len(game_odds) < 2:
                continue

            arbitrage = evaluate_arbitrage(game, game_odds)
            if arbitrage:
                found_arbitrages.append(arbitrage)

        print_arbitrage_report(found_arbitrages)


if __name__ == "__main__":
    main()