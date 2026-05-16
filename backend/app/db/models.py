from sqlalchemy import Column, Integer, String, Float, Date, Boolean, UniqueConstraint, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base


class Game(Base):
    
    __tablename__ = "games"

    # ── KLUCZ GŁÓWNY ─────────────────────────────────────────────────
    id = Column(Integer, primary_key=True, index=True)

    # NBA's własne ID meczu — unikalne per sezon, używamy do dedupu
    game_id = Column(String(20), nullable=False, index=True)

    # Relationship to Odds
    odds = relationship("Odds", back_populates="game")

    # ── META ──────────────────────────────────────────────────────────
    game_date = Column(Date, nullable=False)
    season = Column(String(10), nullable=False)  # np. "2023-24"

    # ── DRUŻYNY ───────────────────────────────────────────────────────
    home_team = Column(String(50), nullable=False)  # np. "DEN"
    away_team = Column(String(50), nullable=False)  # np. "LAL"

    # ── WYNIK KOŃCOWY ─────────────────────────────────────────────────
    home_score = Column(Float, nullable=True)
    away_score = Column(Float, nullable=True)
    home_team_wins = Column(Boolean, nullable=True)  # True = gospodarz wygrał

    # ── STATYSTYKI GOSPODARZA (home_*) ────────────────────────────────
    # Rzuty z gry (Field Goals)
    home_fgm = Column(Float, nullable=True)  # trafione
    home_fga = Column(Float, nullable=True)  # próby
    home_fg_pct = Column(Float, nullable=True)  # skuteczność: fgm/fga

    # Trójki (3-Pointers)
    home_fg3m = Column(Float, nullable=True)
    home_fg3a = Column(Float, nullable=True)
    home_fg3_pct = Column(Float, nullable=True)

    # Wolne rzuty (Free Throws)
    home_ftm = Column(Float, nullable=True)
    home_fta = Column(Float, nullable=True)
    home_ft_pct = Column(Float, nullable=True)

    # Zbiorki, asysty, przechwyty, bloki, straty, faule
    home_oreb = Column(Float, nullable=True)  # zbiorki ofensywne
    home_dreb = Column(Float, nullable=True)  # zbiorki defensywne
    home_reb = Column(Float, nullable=True)  # zbiorki łącznie
    home_ast = Column(Float, nullable=True)  # asysty
    home_stl = Column(Float, nullable=True)  # przechwyty
    home_blk = Column(Float, nullable=True)  # bloki
    home_tov = Column(Float, nullable=True)  # straty (turnovers)
    home_pf = Column(Float, nullable=True)  # faule osobiste
    home_plus_minus = Column(Float, nullable=True)  # różnica pk gdy ta drużyna grała

    # ── STATYSTYKI GOŚCI (away_*) ──────────────────────────────────────
    # Identyczna struktura co home_*, tylko inny prefix
    away_fgm = Column(Float, nullable=True)
    away_fga = Column(Float, nullable=True)
    away_fg_pct = Column(Float, nullable=True)

    away_fg3m = Column(Float, nullable=True)
    away_fg3a = Column(Float, nullable=True)
    away_fg3_pct = Column(Float, nullable=True)

    away_ftm = Column(Float, nullable=True)
    away_fta = Column(Float, nullable=True)
    away_ft_pct = Column(Float, nullable=True)

    away_oreb = Column(Float, nullable=True)
    away_dreb = Column(Float, nullable=True)
    away_reb = Column(Float, nullable=True)
    away_ast = Column(Float, nullable=True)
    away_stl = Column(Float, nullable=True)
    away_blk = Column(Float, nullable=True)
    away_tov = Column(Float, nullable=True)
    away_pf = Column(Float, nullable=True)
    away_plus_minus = Column(Float, nullable=True)

    # ── CONSTRAINT: jeden game_id per sezon ───────────────────────────
    __table_args__ = (UniqueConstraint("game_id", name="uq_game_id"),)


class Player(Base):
    """
    Zawodnik NBA. Będzie używany w późniejszych fazach
    do analizy składów i kontuzji.
    """

    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    team_name = Column(String(50), nullable=True)
    position = Column(String(10), nullable=True)
    is_active = Column(Boolean, nullable=False)


class Odds(Base):
    __tablename__ = "odds"
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(String(20), ForeignKey("games.game_id"), nullable=False, index=True)
    bookmaker = Column(String(50), nullable=False, index=True)
    home_win_odds = Column(Float, nullable=True)
    away_win_odds = Column(Float, nullable=True)

    game = relationship("Game", back_populates="odds")

    __table_args__ = (
        UniqueConstraint('game_id', 'bookmaker', name='uix_game_bookmaker'),
)


class User(Base):
    """User accounts for authentication"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    supabase_id = Column(String(100), unique=True, index=True, nullable=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=True)
    provider = Column(String(50), nullable=True)  # google, github, email
    created_at = Column(DateTime, default=datetime.utcnow)
    
    watchlist = relationship("Watchlist", back_populates="user")


class Watchlist(Base):
    """User's saved games"""
    __tablename__ = "watchlist"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    game_id = Column(String(20), ForeignKey("games.game_id"), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="watchlist")
    game = relationship("Game")


class Prediction(Base):
    """ML model predictions for games"""
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(String(20), ForeignKey("games.game_id"), nullable=False, index=True)
    model_name = Column(String(50), nullable=False)
    home_win_prob = Column(Float, nullable=False)
    away_win_prob = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    game = relationship("Game")
    
    __table_args__ = (
        UniqueConstraint('game_id', 'model_name', name='uix_game_model'),
)


class UserPick(Base):
    """Track user's placed bets/picks"""
    __tablename__ = "user_picks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    game_id = Column(String(20), ForeignKey("games.game_id"), nullable=False)
    
    # Pick details
    pick_team = Column(String(10), nullable=False)  # "LAL" or "BOS"
    pick_type = Column(String(20), nullable=False)  # "moneyline", "spread", "total"
    odds = Column(Float, nullable=False)            # -110, +150
    stake = Column(Float, nullable=False)           # $100
    
    # Status
    placed_at = Column(DateTime, default=datetime.utcnow)
    result = Column(String(10), nullable=True)      # "WIN", "LOSS", "PENDING"
    profit = Column(Float, nullable=True)           # +$90 or -$100
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User")
    game = relationship("Game")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'game_id', 'pick_type', name='uq_user_game_pick'),
        Index('idx_user_picks', 'user_id', 'result'),
    )


class OddsHistory(Base):
    """Track historical odds for line movement tracking"""
    __tablename__ = "odds_history"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(String(20), ForeignKey("games.game_id"), nullable=False, index=True)
    bookmaker = Column(String(50), nullable=False)
    
    # Odds at this point in time
    home_odds = Column(Float, nullable=True)        # -110
    away_odds = Column(Float, nullable=True)        # +110
    spread = Column(Float, nullable=True)           # -2.5
    total = Column(Float, nullable=True)            # 218.5
    
    # When this was recorded
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    game = relationship("Game")
    
    __table_args__ = (
        Index('idx_game_bookmaker_timestamp', 'game_id', 'bookmaker', 'timestamp'),
    )


class UserAlert(Base):
    """User's notification preferences"""
    __tablename__ = "user_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Alert types
    alerts_arbitrage = Column(Boolean, default=True)      # Arb opportunities
    alerts_sharp = Column(Boolean, default=True)          # Sharp money detected
    alerts_picks = Column(Boolean, default=True)          # New picks
    alerts_lineup = Column(Boolean, default=False)        # Player injuries/lineup
    
    # Filters
    min_roi = Column(Float, default=0.5)                  # Alert if ROI > 0.5%
    min_confidence = Column(Float, default=0.55)          # Alert if confidence > 55%
    
    # Notification channels
    email = Column(Boolean, default=True)
    sms = Column(Boolean, default=False)
    push = Column(Boolean, default=False)
    
    # Contact info
    phone_number = Column(String(20), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User")

