"""
HoopsQuant API - NBA Predictions & Arbitrage Finder
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import engine
from app.db import models

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


# Routes will be included here in next steps
# from app.api.routes import games, predictions, arbitrage, watchlist
