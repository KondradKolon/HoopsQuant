"""
Job Scheduler - APScheduler for automated data collection and predictions
Runs all background jobs on a schedule
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s: %(message)s'
)
logger = logging.getLogger("scheduler")

# Import job functions
from jobs.nba_fetcher_2026 import main as fetch_nba_2026
from jobs.odds_schedule import scheduled_nba_odds_pipeline, scheduled_current_odds
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
        
        # NBA odds pipeline — every 2 hours (rolling date window, see odds_schedule.py)
        scheduler.add_job(
            scheduled_nba_odds_pipeline,
            'cron',
            hour='*/2',
            minute=15,
            id='fetch_odds',
            name='Fetch NBA Odds Pipeline',
            misfire_grace_time=600,
        )
        logger.info("📅 Scheduled: NBA odds pipeline every 2 hours (at :15)")
        
        # Current/live odds — every hour via /odds/multi (NBA-filtered)
        scheduler.add_job(
            scheduled_current_odds,
            'cron',
            minute='5',
            id='fetch_current_odds',
            name='Fetch Current Odds',
            misfire_grace_time=300,
        )
        logger.info("📅 Scheduled: Current NBA odds every hour (at :05)")

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
        
        # Run an immediate data seed in a background thread
        # so the dashboard has data as soon as possible after deployment
        import threading
        def initial_seed():
            logger.info("🌱 Running initial seed (background)...")
            try:
                # Fetch odds for all 4 rounds (past 90 days) + current odds
                scheduled_current_odds()
                scheduled_nba_odds_pipeline()
                generate_predictions()
                track_odds()
                logger.info("🌱 Initial seed complete")
            except Exception as e:
                logger.warning(f"🌱 Initial seed warning (non-fatal): {e}")
        threading.Thread(target=initial_seed, daemon=True).start()
        
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
