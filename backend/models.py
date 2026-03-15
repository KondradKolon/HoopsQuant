from sqlalchemy import Column, Integer, String, Float, Date, Boolean, UniqueConstraint
from database import Base


class Game(Base):
    """
    Jeden wiersz = jeden mecz NBA z pełnymi statystykami OBU drużyn.

    Skąd mamy te dane?
    ─────────────────────────────────────────────────────────────────
    leaguegamelog zwraca ~2460 wierszy na sezon (2 wiersze na mecz).
    W seed.py łączymy oba wiersze (home + away) po GAME_ID
    → jeden wiersz z prefiksem home_ i away_.

    Dlaczego game_id obok id?
    ─────────────────────────────────────────────────────────────────
    `id`      = nasz wewnętrzny klucz (auto-increment, szybki JOIN)
    `game_id` = oficjalny ID meczu z NBA (np. "0022300001")
              = pozwala uniknąć duplikatów przy re-seedowaniu
    """

    __tablename__ = "games"

    # ── KLUCZ GŁÓWNY ─────────────────────────────────────────────────
    id = Column(Integer, primary_key=True, index=True)

    # NBA's własne ID meczu — unikalne per sezon, używamy do dedupu
    game_id = Column(String(20), nullable=False, index=True)

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
    # Baza odrzuci INSERT jeśli ten game_id już istnieje → zero duplikatów
    __table_args__ = (UniqueConstraint("game_id", name="uq_game_id"),)


class Player(Base):
    """
    Zawodnik NBA. Będzie używany w późniejszych sprintach
    do analizy składów i kontuzji.
    """

    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    team_name = Column(String(50), nullable=True)
    position = Column(String(10), nullable=True)
    is_active = Column(Boolean, nullable=False)
