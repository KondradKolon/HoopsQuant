"""
HoopsQuant API - NBA Predictions & Arbitrage Finder
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import engine
from app.db import models
from app.api.routes import games, arbitrage, watchlist, dashboard
from jobs.scheduler import start_scheduler, stop_scheduler
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Create database tables
models.Base.metadata.create_all(bind=engine)

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
        "https://*.vercel.app",
        "https://hoopsquant.vercel.app",
    ],
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

