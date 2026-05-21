"""
Job Scheduler - APScheduler for automated data collection and predictions
Runs all background jobs on a schedule
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
import logging
import sys
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s: %(message)s'
)
logger = logging.getLogger("scheduler")

# Ensure imports work from backend root
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import job functions
from jobs.nba_fetcher_2026 import main as fetch_nba_2026
from jobs.odds_fetcher import run_odds_pipeline
from jobs.fetch_current_odds import fetch_and_store as fetch_current_odds
from jobs.generate_predictions import main as generate_predictions
from jobs.odds_tracker import track_odds

# Create scheduler instance
scheduler = BackgroundScheduler(
    executors={
        'default': ThreadPoolExecutor(max_workers=5)
    },
    job_defaults={
        'max_instances': 1,
        'coalesce': True
    }
)


def start_scheduler():
    """Start all scheduled jobs"""
    
    try:
        # NBA games - fetch once daily at 3 AM UTC
        scheduler.add_job(
            fetch_nba_2026,
            'cron',
            hour=3,
            minute=0,
            id='fetch_nba_games',
            name='Fetch NBA Games',
            misfire_grace_time=900  # 15 minutes grace period
        )
        logger.info("📅 Scheduled: NBA games fetch at 03:00 UTC")
        
        # Odds - fetch every 2 hours
        scheduler.add_job(
            run_odds_pipeline,
            'cron',
            hour='*/2',
            id='fetch_odds',
            name='Fetch Odds',
            misfire_grace_time=600,  # 10 minutes grace period
            kwargs={
                'start_iso': datetime.now().date().isoformat(),
                'end_iso': datetime.now().date().isoformat(),
                'max_games': 50
            }
        )
        logger.info("📅 Scheduled: Odds fetch every 2 hours")
        
        # Current/live odds - every hour (catches new events and odds movements)
        scheduler.add_job(
            fetch_current_odds,
            'cron',
            minute='0',
            id='fetch_current_odds',
            name='Fetch Current Odds',
            misfire_grace_time=300
        )
        logger.info("📅 Scheduled: Current odds fetch every hour")

        # Odds history tracking - every 30 minutes (for sharp detection)
        scheduler.add_job(
            track_odds,
            'cron',
            minute='*/30',
            id='track_odds_history',
            name='Track Odds History',
            misfire_grace_time=300  # 5 minutes grace period
        )
        logger.info("📅 Scheduled: Odds history tracking every 30 minutes")
        
        # Predictions - every 6 hours
        scheduler.add_job(
            generate_predictions,
            'cron',
            hour='*/6',
            id='generate_predictions',
            name='Generate Predictions',
            misfire_grace_time=600  # 10 minutes grace period
        )
        logger.info("📅 Scheduled: Predictions generation every 6 hours")
        
        scheduler.start()
        logger.info("✅ Scheduler started successfully")
        
    except Exception as e:
        logger.warning(f"⚠️  Scheduler setup warning: {e}. App will continue without background jobs.")
        # Don't re-raise - let app continue even if scheduler fails


def stop_scheduler():
    """Stop scheduler gracefully"""
    try:
        if scheduler.running:
            scheduler.shutdown(wait=True)
            logger.info("🛑 Scheduler stopped")
    except Exception as e:
        logger.error(f"❌ Error stopping scheduler: {e}")
