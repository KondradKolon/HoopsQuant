"""
Shared constants for HoopsQuant backend.
Single source of truth for team name mappings, NBA metadata, and config defaults.
"""

TEAM_ABBREVIATIONS = {
    "Atlanta Hawks": "ATL",
    "Boston Celtics": "BOS",
    "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA",
    "Chicago Bulls": "CHI",
    "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL",
    "Denver Nuggets": "DEN",
    "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW",
    "Houston Rockets": "HOU",
    "Indiana Pacers": "IND",
    "LA Clippers": "LAC",
    "Los Angeles Lakers": "LAL",
    "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA",
    "Milwaukee Bucks": "MIL",
    "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP",
    "New York Knicks": "NYK",
    "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL",
    "Philadelphia 76ers": "PHI",
    "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR",
    "Sacramento Kings": "SAC",
    "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR",
    "Utah Jazz": "UTA",
    "Washington Wizards": "WAS",
}

NBA_ABBREVIATION_TO_FULL = {v: k for k, v in TEAM_ABBREVIATIONS.items()}

NBA_CONFERENCES = {
    "east": {"BOS", "NYK", "BKN", "PHI", "TOR", "CLE", "MIL", "IND", "CHI", "DET", "MIA", "ATL", "CHA", "ORL", "WAS"},
    "west": {"DEN", "MIN", "OKC", "POR", "UTA", "LAL", "LAC", "GSW", "SAC", "PHX", "DAL", "HOU", "SAS", "MEM", "NOP"},
}
