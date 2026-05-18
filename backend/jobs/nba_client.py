import time
import random
import pandas as pd
from curl_cffi import requests as cffi_requests
from curl_cffi.requests.exceptions import Timeout

URL = "https://stats.nba.com/stats/leaguegamelog"

HEADERS = {
    "Host": "stats.nba.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/110.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
}

# Kolumny które nas interesują z API — wszystko inne ignorujemy
STAT_COLS = [
    "GAME_ID",
    "GAME_DATE",
    "TEAM_ABBREVIATION",
    "MATCHUP",
    "WL",
    "PTS",
    "FGM",
    "FGA",
    "FG_PCT",
    "FG3M",
    "FG3A",
    "FG3_PCT",
    "FTM",
    "FTA",
    "FT_PCT",
    "OREB",
    "DREB",
    "REB",
    "AST",
    "STL",
    "BLK",
    "TOV",
    "PF",
    "PLUS_MINUS",
]


def fetch_season(season: str) -> pd.DataFrame:
    """
    Pobiera wszystkie wiersze dla danego sezonu regularnego.

    Args:
        season: Format "RRRR-RR", np. "2023-24"

    Returns:
        pd.DataFrame z ~2460 wierszami (2 wiersze na mecz — home + away).
        Każdy wiersz = statystyki jednej drużyny w jednym meczu.

    Raises:
        RuntimeError: gdy API zwróci błąd lub puste dane.
    """
    params = {
        "Counter": "1000",
        "DateFrom": "",
        "DateTo": "",
        "Direction": "ASC",
        "LeagueID": "00",
        "PlayerOrTeam": "T", 
        "Season": season,
        "SeasonType": "Regular Season",
        "Sorter": "DATE",
    }

    pause = random.uniform(2, 4)
    print(f"[CLIENT] GET stats.nba.com  season={season} ... (pauza {pause:.1f}s)")
    time.sleep(pause)

    from curl_cffi.requests.exceptions import HTTPError

    MAX_RETRIES = 4
    BASE_WAIT_SEC = 8

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = cffi_requests.get(
                URL,
                params=params,
                headers=HEADERS,
                impersonate="chrome110",
                timeout=60,
            )

            if response.status_code == 500:
                raise HTTPError(f"HTTP 500", 0, response)

            break  # sukces

        except (Timeout, HTTPError) as e:
            err_type = (
                "Timeout" if isinstance(e, Timeout) else f"HTTP {response.status_code}"
            )

            if attempt == MAX_RETRIES:
                raise RuntimeError(
                    f"NBA API nie odpowiada po {MAX_RETRIES} próbach dla sezonu {season} ({err_type})."
                ) from e

            wait = BASE_WAIT_SEC * (2 ** (attempt - 1)) + random.uniform(0, 5)
            print(
                f"[CLIENT] {err_type} (próba {attempt}/{MAX_RETRIES}). Czekam {wait:.1f}s..."
            )
            time.sleep(wait)

    response.raise_for_status()

    # Struktura odpowiedzi: {"resultSets": [{"headers": [...], "rowSet": [...]}]}
    result_set = response.json()["resultSets"][0]
    headers = result_set["headers"]
    rows = result_set["rowSet"]

    if not rows:
        raise RuntimeError(f"API zwróciło 0 wierszy dla sezonu {season}.")

    # Budujemy DataFrame z nagłówkami z API i wybierz tylko potrzebne kolumny
    df = pd.DataFrame(rows, columns=headers)[STAT_COLS]

    print(f"[CLIENT] Pobrano {len(df)} wierszy (2 per mecz).")
    return df
