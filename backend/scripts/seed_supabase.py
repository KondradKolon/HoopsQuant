"""
seed_supabase.py — One-time local seed of historical NBA data + predictions to Supabase

Usage:
  1. Set your local .env DATABASE_URL to your Supabase connection string:
     DATABASE_URL=postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres

  2. Run: python -m scripts.seed_supabase

This will:
  - Fetch all 2025-26 NBA historical games from stats.nba.com
  - Generate ML predictions for any upcoming games
  - Write everything to Supabase

After this runs, the Railway API will serve pre-computed predictions immediately.
"""

import sys
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(name)s: %(message)s")
logger = logging.getLogger("seed_supabase")

from jobs.nba_fetcher_2026 import main as fetch_nba
from jobs.generate_predictions import main as generate_preds
from jobs.odds_fetcher import run_odds_pipeline
from datetime import date


def main():
    logger.info("=" * 60)
    logger.info("SEEDING SUPABASE WITH HISTORICAL NBA DATA")
    logger.info("=" * 60)

    # 1. Fetch all historical games (2025-26 season)
    logger.info("\n[1/3] Fetching historical NBA games...")
    fetch_nba()

    # 2. Fetch today's odds (so we have games to predict)
    logger.info("\n[2/3] Fetching today's odds...")
    today = date.today().isoformat()
    run_odds_pipeline(start_iso=today, end_iso=today, max_games=50)

    # 3. Generate predictions for all upcoming games
    logger.info("\n[3/3] Generating predictions...")
    generate_preds()

    logger.info("\n" + "=" * 60)
    logger.info("SEED COMPLETE")
    logger.info("=" * 60)
    logger.info("\nYour Supabase DB now has historical games + predictions.")
    logger.info("Railway will handle live odds and predictions for new games going forward.")


if __name__ == "__main__":
    main()
