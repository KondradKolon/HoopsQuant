"""
odds_profit_check.py — Max-efficiency odds fetch + model EV analysis

Strategy (100 req/hr):
  1. Fetch current events w/ bookmaker filter: 2 req (STS PL + Superbet)
  2. Fetch detailed odds via /odds/multi (10/call): ceil(N/10) req
  3. Fetch historical events: 1 req
  4. Fetch historical odds for events with our bookmakers: ~N/10 req
  5. Run model predictions + EV on everything found

Usage:
  python odds_profit_check.py              # full run
  python odds_profit_check.py --current     # current odds only (no historical)
  python odds_profit_check.py --no-predict  # odds fetch only, no model
"""

import argparse
import hashlib
import joblib
import logging
import numpy as np
import os
import pandas as pd
import requests
import sys
import time
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
logger = logging.getLogger("profit_check")

load_dotenv(Path(__file__).parent.parent / ".env")
KEY = os.getenv("ODDS_API_KEY")
BASE = "https://api.odds-api.io/v3"

BOOKMAKERS = os.getenv("BOOKMAKERS", "Superbet,Stake").split(",")

TEAM_MAP = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "LA Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP", "New York Knicks": "NYK", "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC", "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR", "Utah Jazz": "UTA", "Washington Wizards": "WAS",
    "Oklahoma C": "OKC", "San Antoni": "SAS", "New York K": "NYK", "Cleveland ": "CLE",
}


def api_get(endpoint, params, retries=10):
    for attempt in range(retries):
        try:
            r = requests.get(f"{BASE}/{endpoint}", params={"apiKey": KEY, **params}, timeout=15)
            if r.status_code == 429:
                err = r.json().get("error", "")
                logger.warning(f"Rate limited, retrying in 120s: {err}")
                time.sleep(120)
                continue
            if r.status_code == 200:
                return r.json()
            logger.warning(f"{endpoint} returned {r.status_code}")
            return None
        except Exception as e:
            logger.warning(f"Request error ({endpoint}): {e}")
            if attempt < retries - 1:
                time.sleep(5)
    return None


def extract_moneyline(market_list, bookmaker):
    for market in market_list or []:
        name = (market.get("name") or "").strip().lower()
        if any(k in name for k in ("1q", "2q", "3q", "4q", "quarter", "ht", "2h")):
            continue
        odds_list = market.get("odds") or []
        if not odds_list:
            continue
        odd = odds_list[0]
        if name in ("ml", "moneyline"):
            return float(odd.get("home", 0)) or None, float(odd.get("away", 0)) or None
        if name == "3-way result":
            return float(odd.get("home", 0)) or None, float(odd.get("away", 0)) or None
    return None, None


def american_to_decimal(american):
    if american is None or american == 0:
        return None
    if american > 0:
        return 1 + american / 100
    return 1 + 100 / abs(american)


def compute_ev(model_prob, decimal_odds):
    if decimal_odds is None or decimal_odds <= 0:
        return None
    return model_prob * decimal_odds - 1


def load_model_and_data():
    model_dir = Path(__file__).parent.parent / "models"
    model = joblib.load(model_dir / "model.pkl")
    scaler = joblib.load(model_dir / "scaler.pkl")
    feature_cols = joblib.load(model_dir / "feature_cols.pkl")

    features_path = Path(__file__).parent.parent / "features.csv"
    df = pd.read_csv(features_path, parse_dates=["game_date"]) if features_path.exists() else None
    if df is not None:
        logger.info(f"Model: {type(model).__name__}, features: {len(feature_cols)}, history: {len(df)} games")

    return model, scaler, feature_cols, df


def predict_game(home_full, away_full, model, scaler, feature_cols, df):
    home = TEAM_MAP.get(home_full, home_full)
    away = TEAM_MAP.get(away_full, away_full)

    completed = df[df["home_score"].notna()].copy()
    if completed.empty:
        return None

    features = {}
    for prefix, team in [("home_", home), ("away_", away)]:
        team_data = completed[
            (completed["home_team"] == team) | (completed["away_team"] == team)
        ].tail(10)
        if team_data.empty:
            logger.warning(f"No history for {team}")
            return None
        for col in feature_cols:
            if col.startswith(prefix) and col.endswith("_last10"):
                base = col[len(prefix):-7]
                if base in team_data.columns:
                    features[col] = team_data[base].mean()
                else:
                    candidates = [c for c in team_data.columns if c.endswith(base)]
                    if candidates:
                        features[col] = team_data[candidates[0]].mean()
                    else:
                        logger.warning(f"Missing feature base '{base}' for {team}")
                        return None

    features["home_elo"] = 1500.0
    features["away_elo"] = 1500.0
    features["elo_diff"] = 0.0

    missing = [c for c in feature_cols if c not in features or pd.isna(features.get(c))]
    if missing:
        logger.warning(f"Missing features: {missing}")
        return None

    X = pd.DataFrame(np.array([[features[c] for c in feature_cols]]), columns=feature_cols)
    X_scaled = pd.DataFrame(scaler.transform(X), columns=feature_cols)
    proba = model.predict_proba(X_scaled)[0]
    return {
        "home_win_prob": float(proba[1]),
        "away_win_prob": float(proba[0]),
        "confidence": max(proba[1], proba[0]),
    }


def print_game(home_code, away_code, date_str, bm_odds, pred=None):
    print(f"\n  {home_code} vs {away_code} ({date_str})")
    if pred:
        print(f"  ┌ Model:  H {pred['home_win_prob']:.1%} | A {pred['away_win_prob']:.1%} | conf {pred['confidence']:.1%}")

    for bm, (ho, ao) in sorted(bm_odds.items()):
        home_dec = american_to_decimal(ho)
        away_dec = american_to_decimal(ao)
        home_impl = 1 / home_dec if home_dec else 0
        away_impl = 1 / away_dec if away_dec else 0
        margin = home_impl + away_impl - 1

        line = f"  ├ {bm:>10}: H {ho:+.0f} ({home_dec:.2f}x, {home_impl:.1%}) | A {ao:+.0f} ({away_dec:.2f}x, {away_impl:.1%}) | vig={margin:.1%}"

        if pred:
            home_ev = compute_ev(pred["home_win_prob"], home_dec)
            away_ev = compute_ev(pred["away_win_prob"], away_dec)
            hev = f"EV={home_ev:+.1%}" if home_ev is not None else "EV=---"
            aev = f"EV={away_ev:+.1%}" if away_ev is not None else "EV=---"
            line += f" | {hev:>12} | {aev:>12}"
            if home_ev is not None and home_ev > 0:
                line += " ⬆️"
            elif away_ev is not None and away_ev > 0:
                line += " ⬆️"

        print(line)

    return True


def fetch_events_with_bookmaker(bm, sport=None):
    """Get events that have odds for a specific bookmaker"""
    params = {"bookmaker": bm, "limit": 100}
    if sport:
        params["sport"] = sport
    data = api_get("events", params)
    if data is None:
        return []
    return data if isinstance(data, list) else data.get("events", data.get("data", [data] if isinstance(data, dict) and "id" in data else []))


def fetch_historical_events(bm, days_back=30):
    """Get historical events for a bookmaker"""
    params = {"bookmaker": bm, "limit": 100}
    data = api_get("historical/events", params)
    if data is None:
        return []
    return data if isinstance(data, list) else data.get("events", data.get("data", []))


def fetch_odds_multi(event_ids):
    """Fetch odds for up to 10 events at once"""
    odds_map = {}
    batches = [event_ids[i:i+10] for i in range(0, len(event_ids), 10)]
    for batch in batches:
        data = api_get("odds/multi", {"eventIds": ",".join(batch)})
        if data is None:
            continue
        items = data if isinstance(data, list) else data.get("odds", data.get("data", [data] if isinstance(data, dict) and "id" in data else []))
        for item in items:
            eid = str(item.get("id", ""))
            if eid:
                odds_map[eid] = item.get("bookmakers", {})
    return odds_map


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--current", action="store_true", help="Current odds only (skip historical)")
    parser.add_argument("--no-predict", action="store_true", help="Skip model predictions")
    parser.add_argument("--historical-days", type=int, default=7, help="Days back for historical events")
    args = parser.parse_args()

    if not KEY:
        logger.error("ODDS_API_KEY not set in .env")
        return

    # Load model + data
    if not args.no_predict:
        model, scaler, feature_cols, df = load_model_and_data()
    else:
        model = scaler = feature_cols = df = None

    req_count = 0

    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 1: Fetch CURRENT events with bookmaker filter
    # ─────────────────────────────────────────────────────────────────────────
    all_events = {}
    for bm in BOOKMAKERS:
        events = fetch_events_with_bookmaker(bm, sport="basketball")
        req_count += 1
        for ev in events:
            eid = str(ev.get("id", ""))
            if eid:
                if eid not in all_events:
                    all_events[eid] = ev
                    all_events[eid]["_bm"] = bm
                else:
                    bms = all_events[eid].get("bookmakers", {})
                    if isinstance(bms, dict) and bm not in bms:
                        bms[bm] = ev.get("bookmakers", {}).get(bm, [])

        logger.info(f"  {bm}: {len(events)} current events")

    # Also try football and tennis to maximize coverage
    for sport in ["football", "tennis"]:
        for bm in BOOKMAKERS:
            events = fetch_events_with_bookmaker(bm, sport=sport)
            req_count += 1
            for ev in events:
                eid = str(ev.get("id", ""))
                if eid and eid not in all_events:
                    all_events[eid] = ev
                    all_events[eid]["_bm"] = bm
            if events:
                logger.info(f"  {bm} ({sport}): {len(events)} events")

    logger.info(f"Total current events found: {len(all_events)} (used {req_count} req)")

    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 2: Fetch HISTORICAL events (7 days back)
    # ─────────────────────────────────────────────────────────────────────────
    hist_events = {}
    if not args.current:
        for bm in BOOKMAKERS:
            events = fetch_historical_events(bm)
            req_count += 1
            for ev in events:
                eid = str(ev.get("id", ""))
                if eid and eid not in hist_events:
                    hist_events[eid] = ev
                    hist_events[eid]["_bm"] = bm
            logger.info(f"  {bm}: {len(events)} historical events (total req: {req_count})")

        # Get scores for historical events
        if hist_events:
            logger.info(f"Fetching historical odds for {len(hist_events)} events...")
            hist_ids = list(hist_events.keys())
            odds_map = fetch_odds_multi(hist_ids)
            req_count += (len(hist_ids) + 9) // 10

            for eid, ev in hist_events.items():
                bms = odds_map.get(eid, ev.get("bookmakers", {}))
                if bms:
                    all_events[eid] = ev
                    all_events[eid]["bookmakers"] = bms

            logger.info(f"Historical with odds: {len([e for e in all_events.values() if e.get('bookmakers')])}")

    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 3: Fetch detailed odds for all events found
    # ─────────────────────────────────────────────────────────────────────────
    all_ids = [eid for eid, ev in all_events.items() if "bookmakers" not in ev or not ev.get("bookmakers")]
    if all_ids:
        logger.info(f"Fetching odds for {len(all_ids)} events without embedded odds...")
        odds_map = fetch_odds_multi(all_ids)
        req_count += (len(all_ids) + 9) // 10
        for eid, bms in odds_map.items():
            if eid in all_events:
                all_events[eid]["bookmakers"] = bms

    logger.info(f"\nTotal API requests: {req_count} / ~90 budget")

    # ─────────────────────────────────────────────────────────────────────────
    # PHASE 4: Analyze — find events with odds from our bookmakers
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 110)
    print("PROFITABILITY ANALYSIS")
    print("=" * 110)

    total_positive_ev = 0
    total_bets = 0
    total_ev_sum = 0.0

    for eid, ev in sorted(all_events.items(), key=lambda x: x[1].get("date", "")):
        bms = ev.get("bookmakers", {})
        if not isinstance(bms, dict):
            continue

        home_full = ev.get("home", "?")
        away_full = ev.get("away", "?")
        home_code = TEAM_MAP.get(home_full, home_full)
        away_code = TEAM_MAP.get(away_full, away_full)
        date_str = str(ev.get("date", ""))[:10]

        # Extract odds for each bookmaker
        our_odds = {}
        for bm in BOOKMAKERS:
            markets = bms.get(bm, [])
            ho, ao = extract_moneyline(markets, bm)
            if ho and ao:
                our_odds[bm] = (ho, ao)

        if not our_odds:
            continue

        # Get prediction
        pred = None
        if df is not None:
            pred = predict_game(home_full, away_full, model, scaler, feature_cols, df)

        print_game(home_code, away_code, date_str, our_odds, pred)

        if pred:
            for ho, ao in our_odds.values():
                home_dec = american_to_decimal(ho)
                away_dec = american_to_decimal(ao)
                total_bets += 2
                home_ev = compute_ev(pred["home_win_prob"], home_dec)
                away_ev = compute_ev(pred["away_win_prob"], away_dec)
                if home_ev is not None:
                    total_ev_sum += home_ev
                    if home_ev > 0:
                        total_positive_ev += 1
                if away_ev is not None:
                    total_ev_sum += away_ev
                    if away_ev > 0:
                        total_positive_ev += 1

    # Summary
    print("\n" + "=" * 110)
    print("SUMMARY")
    print("=" * 110)
    games_with_odds = sum(1 for ev in all_events.values()
                          if any(bm in (ev.get("bookmakers", {}) or {}) for bm in BOOKMAKERS))
    print(f"  Events fetched:              {len(all_events)}")
    print(f"  Games with STS PL/Superbet:  {games_with_odds}")
    print(f"  API requests used:           {req_count}")
    print(f"  Total bet sides evaluated:   {total_bets}")
    print(f"  Positive EV opportunities:   {total_positive_ev}")
    if total_bets > 0:
        print(f"  Avg EV per bet:              {total_ev_sum/total_bets:+.2%}")
    print("=" * 110)


if __name__ == "__main__":
    main()
