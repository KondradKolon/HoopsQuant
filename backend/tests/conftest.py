"""
conftest.py — Shared test fixtures for HoopsQuant.

Provides:
  - db_session: in-memory SQLite session, isolated per test
  - client: FastAPI TestClient with all routes + DB override
  - sample_game, sample_odds, sample_prediction: factory functions
"""

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import arbitrage, dashboard, games, watchlist
from app.api.routes.elo import router as elo_router
from app.db.models import Base, Game, Odds, Prediction, User
from app.dependencies import get_db

# ── In-memory SQLite engine with StaticPool ──────────────────────────
# Standard pool creates a new connection (and thus a new :memory: DB)
# per thread. StaticPool forces all operations onto one connection so
# the tables we create are visible to every query.
engine = create_engine(
    "sqlite:///:memory:",
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine)


# ── Test app (avoids importing app.main which has module-level side effects) ──
def _build_test_app() -> FastAPI:
    app = FastAPI(title="HoopsQuant Test")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root():
        return {"name": "HoopsQuant API", "version": "1.0.0", "status": "online"}

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok", "service": "hoopsquant-api"}

    app.include_router(games.router)
    app.include_router(arbitrage.router)
    app.include_router(watchlist.router)
    app.include_router(dashboard.router)
    app.include_router(elo_router)

    return app


@pytest.fixture(scope="function")
def db_session():
    """Create tables, give a clean session, tear down after test.

    scope="function" means every test gets a fresh DB — no cross-test pollution.
    """
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient wired to the test DB.

    The override means every route that calls Depends(get_db) gets our test session.
    """
    app = _build_test_app()

    # Swap the real get_db with one that yields our test session
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# ── Factory helpers ──────────────────────────────────────────────────
# These let tests write "game = sample_game(db_session)" instead of
# hand-inserting rows every time.


def sample_game(session, **overrides) -> Game:
    """Insert a Game row with sensible defaults. Override any field."""
    from datetime import date
    defaults = dict(
        game_id="TEST001",
        game_date=date(2026, 5, 22),
        season="2025-26",
        home_team="BOS",
        away_team="NYK",
        home_score=None,
        away_score=None,
        home_team_wins=None,
    )
    defaults.update(overrides)
    obj = Game(**defaults)
    session.add(obj)
    session.commit()
    return obj


def sample_odds(session, **overrides) -> Odds:
    """Insert an Odds row. Requires the game to already exist in DB."""
    defaults = dict(
        game_id="TEST001",
        bookmaker="Superbet",
        home_win_odds=1.50,
        away_win_odds=2.75,
    )
    defaults.update(overrides)
    obj = Odds(**defaults)
    session.add(obj)
    session.commit()
    return obj


def sample_prediction(session, **overrides) -> Prediction:
    """Insert a Prediction row. Requires the game to already exist."""
    defaults = dict(
        game_id="TEST001",
        model_name="logistic_regression",
        home_win_prob=0.55,
        away_win_prob=0.45,
        confidence=0.55,
    )
    defaults.update(overrides)
    obj = Prediction(**defaults)
    session.add(obj)
    session.commit()
    return obj


def sample_user(session, **overrides) -> User:
    """Insert a User row."""
    defaults = dict(
        supabase_id="test-user-123",
        email="test@example.com",
        name="Test User",
    )
    defaults.update(overrides)
    obj = User(**defaults)
    session.add(obj)
    session.commit()
    return obj
