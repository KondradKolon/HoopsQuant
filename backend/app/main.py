"""
HoopsQuant API - NBA Predictions & Arbitrage Finder
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import engine
from app.db import models
from app.api.routes import games, arbitrage, watchlist, dashboard
from app.api.routes.elo import router as elo_router
from jobs.scheduler import start_scheduler, stop_scheduler
import logging
import time

# Setup logging
logger = logging.getLogger(__name__)

# Initialize database tables with retry logic (non-blocking)
def init_db_with_retry(max_retries=3, initial_delay=1):
    """Initialize database tables with exponential backoff retry logic"""
    for attempt in range(max_retries):
        try:
            models.Base.metadata.create_all(bind=engine)
            logger.info("✓ Database tables initialized successfully")
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)
                logger.warning(f"⚠️  Database init attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.warning(f"⚠️  Database initialization failed after {max_retries} attempts: {e}. API will start without DB tables.")
                return False

# Try to initialize database, but don't block app startup
try:
    init_db_with_retry()
except Exception as e:
    logger.warning(f"⚠️  Database initialization error: {e}. API will function with limited features until DB is available.")

# Create FastAPI app
app = FastAPI(
    title="HoopsQuant API",
    description="NBA Game Predictions & Arbitrage Finder",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://hoops-quant.vercel.app",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": "HoopsQuant API",
        "version": "1.0.0",
        "description": "NBA Predictions & Arbitrage Finder",
        "status": "online"
    }


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "hoopsquant-api"}


# Include routers
app.include_router(games.router)
app.include_router(arbitrage.router)
app.include_router(watchlist.router)
app.include_router(dashboard.router)
app.include_router(elo_router)


# Scheduler startup and shutdown hooks
@app.on_event("startup")
async def startup_event():
    """Start scheduler when API starts"""
    logger.info("🚀 Starting HoopsQuant API...")
    try:
        start_scheduler()
    except Exception as e:
        logger.warning(f"⚠️  Scheduler startup warning: {e}")
        # Don't fail API startup if scheduler fails


@app.on_event("shutdown")
async def shutdown_event():
    """Stop scheduler when API shuts down"""
    logger.info("🛑 Shutting down HoopsQuant API...")
    stop_scheduler()

