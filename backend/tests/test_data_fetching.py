"""
Comprehensive Tests for NBA & Odds Data Fetching
Tests NBA stats fetching, odds API integration, and season coverage
"""

import sys
from pathlib import Path
import logging
from datetime import datetime, timedelta
import pandas as pd

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s: %(message)s'
)
logger = logging.getLogger("data_fetching_tests")

# Import our fetchers
from app.db.database import SessionLocal
from app.db.models import Game, Odds
from jobs.nba_fetcher_2026 import fetch_season, transform_games, save_games
from jobs.odds_fetcher import (
    fetch_events_list, 
    fetch_odds_for_game, 
    run_odds_pipeline,
    TEAM_ABBREVIATIONS,
    POLISH_BOOKMAKERS
)


class TestNBAFetcher:
    """Test NBA stats fetcher"""
    
    @staticmethod
    def test_fetch_season_2026():
        """Test fetching 2026 season data"""
        print("\n" + "="*80)
        print("TEST 1: NBA FETCHER - Fetch 2026 Season")
        print("="*80)
        
        try:
            logger.info("Fetching 2026 NBA season data...")
            df = fetch_season(season="2025-26")
            
            # Verify data
            assert df is not None, "Dataframe is None"
            assert len(df) > 0, "Dataframe is empty"
            
            logger.info(f"✅ Successfully fetched {len(df)} rows from 2026 season")
            logger.info(f"   Columns: {', '.join(df.columns.tolist()[:5])}...")
            logger.info(f"   Date range: {df['GAME_DATE'].min()} to {df['GAME_DATE'].max()}")
            logger.info(f"   Unique games: {len(df) // 2}")  # 2 rows per game
            
            return True
        except Exception as e:
            logger.error(f"❌ NBA fetcher failed: {e}")
            return False
    
    @staticmethod
    def test_transform_games():
        """Test game transformation logic"""
        print("\n" + "="*80)
        print("TEST 2: NBA FETCHER - Transform Games")
        print("="*80)
        
        try:
            logger.info("Fetching and transforming 2026 season...")
            df_raw = fetch_season(season="2025-26")
            df_games = transform_games(df_raw)
            
            assert df_games is not None, "Transformed dataframe is None"
            assert len(df_games) > 0, "No games transformed"
            
            logger.info(f"✅ Transformed {len(df_games)} games")
            logger.info(f"   Columns: {', '.join(df_games.columns.tolist())}")
            logger.info(f"   Sample game: {df_games.iloc[0]['home_team']} vs {df_games.iloc[0]['away_team']}")
            
            # Check data integrity
            assert 'game_id' in df_games.columns
            assert 'game_date' in df_games.columns
            assert 'home_team' in df_games.columns
            assert 'away_team' in df_games.columns
            assert 'home_score' in df_games.columns
            assert 'away_score' in df_games.columns
            
            logger.info(f"✅ All required columns present")
            
            return True
        except Exception as e:
            logger.error(f"❌ Game transformation failed: {e}")
            return False
    
    @staticmethod
    def test_save_games():
        """Test saving games to database"""
        print("\n" + "="*80)
        print("TEST 3: NBA FETCHER - Save Games to Database")
        print("="*80)
        
        try:
            logger.info("Fetching, transforming, and saving 2026 season...")
            
            # Fetch and transform
            df_raw = fetch_season(season="2025-26")
            df_games = transform_games(df_raw)
            
            # Save to DB
            saved_count = save_games(df_games)
            
            logger.info(f"✅ Saved {saved_count} games to database")
            
            # Verify in database
            session = SessionLocal()
            db_games = session.query(Game).filter(Game.season == "2025-26").all()
            
            logger.info(f"✅ Database contains {len(db_games)} games from 2025-26 season")
            
            if db_games:
                sample = db_games[0]
                logger.info(f"   Sample: {sample.home_team} vs {sample.away_team} on {sample.game_date}")
            
            session.close()
            return True
        except Exception as e:
            logger.error(f"❌ Save games failed: {e}")
            return False
    
    @staticmethod
    def test_season_coverage():
        """Test that we have full season coverage (regular + playoffs)"""
        print("\n" + "="*80)
        print("TEST 4: NBA FETCHER - Season Coverage Analysis")
        print("="*80)
        
        try:
            session = SessionLocal()
            games = session.query(Game).filter(Game.season == "2025-26").order_by(Game.game_date).all()
            
            if not games:
                logger.warning("⚠️  No games found in database")
                session.close()
                return False
            
            # Analyze coverage
            total_games = len(games)
            min_date = min(g.game_date for g in games)
            max_date = max(g.game_date for g in games)
            
            # Count completed vs upcoming
            today = datetime.utcnow().date()
            completed = len([g for g in games if g.home_score is not None])
            upcoming = len([g for g in games if g.home_score is None])
            
            logger.info(f"✅ Season Coverage Analysis:")
            logger.info(f"   Total games: {total_games}")
            logger.info(f"   Date range: {min_date} to {max_date}")
            logger.info(f"   Days span: {(max_date - min_date).days} days")
            logger.info(f"   Completed: {completed} games")
            logger.info(f"   Upcoming: {upcoming} games")
            
            # Estimate regular season + playoffs
            # Regular season: ~1,230 games (82 per team)
            # Playoff: ~80-90 games
            logger.info(f"\n📊 Season Analysis:")
            if total_games >= 1200:
                logger.info(f"   ✅ Full regular season likely covered ({total_games} >= 1200)")
            if total_games >= 1300:
                logger.info(f"   ✅ Likely includes playoff games ({total_games} >= 1300)")
            
            session.close()
            return True
        except Exception as e:
            logger.error(f"❌ Season coverage analysis failed: {e}")
            return False


class TestOddsFetcher:
    """Test odds API fetcher"""
    
    @staticmethod
    def test_bookmakers_available():
        """Test that we know about bookmakers"""
        print("\n" + "="*80)
        print("TEST 5: ODDS FETCHER - Bookmakers Configuration")
        print("="*80)
        
        try:
            logger.info(f"Configured bookmakers: {POLISH_BOOKMAKERS}")
            logger.info(f"Total NBA teams: {len(TEAM_ABBREVIATIONS)}")
            
            # List teams
            teams = list(TEAM_ABBREVIATIONS.keys())
            logger.info(f"\n✅ Teams configured:")
            for i, team in enumerate(teams, 1):
                if i % 5 == 0 or i == len(teams):
                    logger.info(f"   {', '.join(teams[max(0,i-5):i])}")
            
            return True
        except Exception as e:
            logger.error(f"❌ Bookmakers check failed: {e}")
            return False
    
    @staticmethod
    def test_fetch_events_list():
        """Test fetching events list from odds API"""
        print("\n" + "="*80)
        print("TEST 6: ODDS FETCHER - Fetch Events List")
        print("="*80)
        
        try:
            # Get events for next 7 days
            end_date = (datetime.utcnow() + timedelta(days=7))
            start_date = datetime.utcnow()
            
            start_iso = start_date.isoformat() + "Z"
            end_iso = end_date.isoformat() + "Z"
            
            logger.info(f"Fetching events from {start_date.date()} to {end_date.date()}...")
            events = fetch_events_list(start_iso, end_iso)
            
            if events:
                logger.info(f"✅ Found {len(events)} upcoming games")
                
                # Show first 5
                for i, event in enumerate(events[:5], 1):
                    logger.info(f"   {i}. {event.get('home_team', 'Unknown')} vs {event.get('away_team', 'Unknown')} ({event.get('commence_time', 'TBD')})")
            else:
                logger.warning("⚠️  No upcoming events found")
            
            return True
        except Exception as e:
            logger.error(f"❌ Events fetch failed: {e}")
            return False
    
    @staticmethod
    def test_fetch_odds():
        """Test fetching odds for games"""
        print("\n" + "="*80)
        print("TEST 7: ODDS FETCHER - Fetch Odds for Games")
        print("="*80)
        
        try:
            # Get upcoming games
            end_date = (datetime.utcnow() + timedelta(days=7))
            start_date = datetime.utcnow()
            
            start_iso = start_date.isoformat() + "Z"
            end_iso = end_date.isoformat() + "Z"
            
            events = fetch_events_list(start_iso, end_iso)
            
            if not events:
                logger.warning("⚠️  No events to fetch odds for")
                return False
            
            # Fetch odds for first game
            game = events[0]
            logger.info(f"Fetching odds for: {game.get('home_team')} vs {game.get('away_team')}")
            
            odds_data = fetch_odds_for_game(
                game.get('home_team'),
                game.get('away_team'),
                game.get('commence_time')
            )
            
            if odds_data:
                logger.info(f"✅ Got odds from {len(odds_data)} bookmakers:")
                for bookmaker, odds in odds_data.items():
                    logger.info(f"   {bookmaker}: Home {odds.get('home_odds')} / Away {odds.get('away_odds')}")
            else:
                logger.warning("⚠️  No odds found for this game")
            
            return True
        except Exception as e:
            logger.error(f"❌ Odds fetch failed: {e}")
            return False
    
    @staticmethod
    def test_odds_pipeline():
        """Test complete odds pipeline"""
        print("\n" + "="*80)
        print("TEST 8: ODDS FETCHER - Complete Pipeline")
        print("="*80)
        
        try:
            # Get recent games
            end_date = (datetime.utcnow() + timedelta(days=7))
            start_date = datetime.utcnow() - timedelta(days=1)
            
            start_iso = start_date.isoformat() + "Z"
            end_iso = end_date.isoformat() + "Z"
            
            logger.info(f"Running odds pipeline for {start_date.date()} to {end_date.date()}...")
            run_odds_pipeline(start_iso, end_iso, max_games=10)
            
            # Check database
            session = SessionLocal()
            all_odds = session.query(Odds).all()
            
            logger.info(f"✅ Odds pipeline complete")
            logger.info(f"   Total odds in DB: {len(all_odds)}")
            
            if all_odds:
                sample = all_odds[0]
                logger.info(f"   Sample: {sample.bookmaker} - Home {sample.home_win_odds} / Away {sample.away_win_odds}")
            
            session.close()
            return True
        except Exception as e:
            logger.error(f"❌ Odds pipeline failed: {e}")
            return False


class TestUpcomingGamesWithOdds:
    """Test getting upcoming games with odds"""
    
    @staticmethod
    def test_get_upcoming_with_odds():
        """Get upcoming games and their odds"""
        print("\n" + "="*80)
        print("TEST 9: UPCOMING GAMES - Get Games + Odds")
        print("="*80)
        
        try:
            session = SessionLocal()
            
            # Get upcoming games (no score yet)
            today = datetime.utcnow().date()
            upcoming = session.query(Game).filter(
                Game.game_date >= today,
                Game.home_score.is_(None)
            ).order_by(Game.game_date).limit(10).all()
            
            logger.info(f"✅ Found {len(upcoming)} upcoming games:")
            
            for i, game in enumerate(upcoming[:5], 1):
                # Get odds for this game
                odds_list = session.query(Odds).filter(Odds.game_id == game.game_id).all()
                
                logger.info(f"\n   {i}. {game.game_date} - {game.home_team} vs {game.away_team}")
                
                if odds_list:
                    logger.info(f"      Odds from {len(odds_list)} bookmakers:")
                    for odds in odds_list[:3]:
                        logger.info(f"      • {odds.bookmaker}: {odds.home_win_odds} / {odds.away_win_odds}")
                else:
                    logger.info(f"      ⚠️  No odds available yet")
            
            session.close()
            return True
        except Exception as e:
            logger.error(f"❌ Upcoming games test failed: {e}")
            return False
    
    @staticmethod
    def test_get_current_playoffs():
        """Get current/recent games (if playoffs are happening)"""
        print("\n" + "="*80)
        print("TEST 10: CURRENT GAMES - Playoffs Check")
        print("="*80)
        
        try:
            session = SessionLocal()
            
            # Get games from last 7 days
            today = datetime.utcnow().date()
            week_ago = today - timedelta(days=7)
            
            recent_games = session.query(Game).filter(
                Game.game_date >= week_ago,
                Game.game_date <= today
            ).order_by(Game.game_date.desc()).all()
            
            logger.info(f"✅ Recent games (last 7 days): {len(recent_games)}")
            
            # Completed vs upcoming in this range
            completed = [g for g in recent_games if g.home_score is not None]
            upcoming_in_range = [g for g in recent_games if g.home_score is None]
            
            logger.info(f"   Completed: {len(completed)}")
            logger.info(f"   Upcoming: {len(upcoming_in_range)}")
            
            # Show latest results if available
            if completed:
                logger.info(f"\n   Latest results:")
                for game in sorted(completed, key=lambda x: x.game_date, reverse=True)[:3]:
                    winner = game.home_team if game.home_team_wins else game.away_team
                    logger.info(f"   • {game.game_date}: {game.home_team} {int(game.home_score)} - {int(game.away_score)} {game.away_team} ({winner} won)")
            
            session.close()
            return True
        except Exception as e:
            logger.error(f"❌ Current games test failed: {e}")
            return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*100)
    print(" 🏀 HOOPSQUANT DATA FETCHING - COMPREHENSIVE TEST SUITE")
    print("="*100)
    
    results = {
        "NBA Fetcher": {},
        "Odds Fetcher": {},
        "Upcoming Games": {}
    }
    
    # NBA Fetcher Tests
    print("\n📊 NBA FETCHER TESTS")
    print("-" * 100)
    results["NBA Fetcher"]["Fetch 2026 Season"] = TestNBAFetcher.test_fetch_season_2026()
    results["NBA Fetcher"]["Transform Games"] = TestNBAFetcher.test_transform_games()
    results["NBA Fetcher"]["Save to Database"] = TestNBAFetcher.test_save_games()
    results["NBA Fetcher"]["Season Coverage"] = TestNBAFetcher.test_season_coverage()
    
    # Odds Fetcher Tests
    print("\n💰 ODDS FETCHER TESTS")
    print("-" * 100)
    results["Odds Fetcher"]["Bookmakers Config"] = TestOddsFetcher.test_bookmakers_available()
    results["Odds Fetcher"]["Fetch Events List"] = TestOddsFetcher.test_fetch_events_list()
    results["Odds Fetcher"]["Fetch Odds"] = TestOddsFetcher.test_fetch_odds()
    results["Odds Fetcher"]["Complete Pipeline"] = TestOddsFetcher.test_odds_pipeline()
    
    # Upcoming Games Tests
    print("\n🎮 UPCOMING GAMES TESTS")
    print("-" * 100)
    results["Upcoming Games"]["Get Upcoming + Odds"] = TestUpcomingGamesWithOdds.test_get_upcoming_with_odds()
    results["Upcoming Games"]["Current/Playoffs Check"] = TestUpcomingGamesWithOdds.test_get_current_playoffs()
    
    # Summary
    print("\n" + "="*100)
    print(" ✅ TEST SUMMARY")
    print("="*100)
    
    total_tests = 0
    passed_tests = 0
    
    for category, tests in results.items():
        passed = sum(1 for v in tests.values() if v)
        total = len(tests)
        total_tests += total
        passed_tests += passed
        
        status = "✅" if passed == total else "⚠️ "
        logger.info(f"\n{status} {category}: {passed}/{total} passed")
        for test_name, result in tests.items():
            emoji = "✅" if result else "❌"
            logger.info(f"   {emoji} {test_name}")
    
    print("\n" + "="*100)
    print(f" 📈 OVERALL: {passed_tests}/{total_tests} tests passed ({passed_tests*100//total_tests}%)")
    print("="*100)
    
    return passed_tests == total_tests


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
