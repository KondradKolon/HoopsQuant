"""Unit tests for prediction service functions."""

import numpy as np
import pandas as pd

from app.services.predictions import (
    _matchup_home_net_ortg,
    _sanitize_features,
    calculate_elo,
    calculate_team_form,
    prob_to_min_american,
    prob_to_min_decimal,
)


class TestMatchupNetOrtg:
    def test_home_team_was_home_in_past_game(self):
        row = pd.Series({
            "home_team": "OKC",
            "home_ortg": 120.0,
            "home_drtg": 110.0,
        })
        assert _matchup_home_net_ortg(row, "OKC") == 10.0

    def test_home_team_was_away_in_past_game(self):
        row = pd.Series({
            "home_team": "SAS",
            "home_ortg": 115.0,
            "home_drtg": 105.0,
        })
        # Today's home OKC was away → batch uses -home_net_ortg
        assert _matchup_home_net_ortg(row, "OKC") == -10.0

    def test_missing_ortg_returns_none(self):
        row = pd.Series({"home_team": "OKC", "home_ortg": np.nan, "home_drtg": 110.0})
        assert _matchup_home_net_ortg(row, "OKC") is None


class TestSanitizeFeatures:
    def test_fills_matchup_nan(self):
        out = _sanitize_features({
            "matchup_net_ortg_last5": np.nan,
            "matchup_home_wins_last5": np.nan,
            "home_elo": 1500.0,
        })
        assert out["matchup_net_ortg_last5"] == 0.0
        assert out["matchup_home_wins_last5"] == 0.5
        assert out["home_elo"] == 1500.0


class TestProbToMinDecimal:
    def test_even_money(self):
        assert prob_to_min_decimal(0.5) == 2.0

    def test_favorite(self):
        assert prob_to_min_decimal(0.75) == 1.33

    def test_underdog(self):
        assert prob_to_min_decimal(0.25) == 4.0

    def test_extreme_favorite(self):
        assert prob_to_min_decimal(0.95) == 1.05

    def test_boundary_zero(self):
        assert prob_to_min_decimal(0.0) == 0.0

    def test_boundary_one(self):
        assert prob_to_min_decimal(1.0) == 0.0


class TestProbToMinAmerican:
    def test_even_money(self):
        assert prob_to_min_american(0.5) == 100

    def test_favorite(self):
        result = prob_to_min_american(0.75)
        # 0.75 → decimal 1.33 → -100 / 0.33 = -303
        assert result == -303

    def test_underdog(self):
        result = prob_to_min_american(0.25)
        assert result == 300

    def test_boundary_zero(self):
        assert prob_to_min_american(0.0) == 0

    def test_boundary_one(self):
        assert prob_to_min_american(1.0) == 0


class TestCalculateElo:
    def test_no_games_returns_default(self):
        df = pd.DataFrame(columns=[
            "game_date", "season", "home_team", "away_team",
            "home_score", "away_score", "home_team_wins"
        ])
        elo = calculate_elo(df, "BOS", pd.Timestamp("2026-05-22"))
        assert elo == 1500.0

    def test_single_game_home_win(self):
        df = pd.DataFrame([{
            "game_date": pd.Timestamp("2026-05-20"),
            "season": "2025-26",
            "home_team": "BOS",
            "away_team": "NYK",
            "home_score": 110,
            "away_score": 90,
            "home_team_wins": 1.0,
        }])
        elo = calculate_elo(df, "BOS", pd.Timestamp("2026-05-22"))
        assert elo > 1500.0  # BOS won, Elo should increase

    def test_single_game_home_loss(self):
        df = pd.DataFrame([{
            "game_date": pd.Timestamp("2026-05-20"),
            "season": "2025-26",
            "home_team": "BOS",
            "away_team": "NYK",
            "home_score": 90,
            "away_score": 110,
            "home_team_wins": 0.0,
        }])
        elo = calculate_elo(df, "BOS", pd.Timestamp("2026-05-22"))
        assert elo < 1500.0  # BOS lost, Elo should decrease

    def test_away_team_elo_updated(self):
        df = pd.DataFrame([{
            "game_date": pd.Timestamp("2026-05-20"),
            "season": "2025-26",
            "home_team": "BOS",
            "away_team": "NYK",
            "home_score": 90,
            "away_score": 110,
            "home_team_wins": 0.0,
        }])
        nyk_elo = calculate_elo(df, "NYK", pd.Timestamp("2026-05-22"))
        assert nyk_elo > 1500.0  # NYK won on road, big Elo gain


class TestCalculateTeamForm:
    def test_no_history_returns_nan(self):
        df = pd.DataFrame(columns=[
            "game_date", "home_team", "away_team", "home_score", "away_score",
            "home_reb", "away_reb", "home_ast", "away_ast",
            "home_stl", "away_stl", "home_blk", "away_blk",
            "home_tov", "away_tov", "home_ortg", "away_ortg",
            "home_drtg", "away_drtg", "home_efg", "away_efg",
            "home_ts", "away_ts", "home_pace", "away_pace",
        ])
        result = calculate_team_form(df, "BOS", pd.Timestamp("2026-05-22"), num_recent_games=10)
        for v in result.values():
            assert np.isnan(v)

    def test_single_game_returns_form(self):
        df = pd.DataFrame([
            {
                "game_date": pd.Timestamp("2026-05-18"),
                "home_team": "BOS",
                "away_team": "CHI",
                "home_score": 105,
                "away_score": 95,
                "home_reb": 42, "away_reb": 38,
                "home_ast": 25, "away_ast": 20,
                "home_stl": 7, "away_stl": 5,
                "home_blk": 4, "away_blk": 2,
                "home_tov_rate": 0.11, "away_tov_rate": 0.13,
                "home_ortg": 112.0, "away_ortg": 102.0,
                "home_drtg": 102.0, "away_drtg": 112.0,
                "home_efg": 0.53, "away_efg": 0.47,
                "home_ts": 0.58, "away_ts": 0.50,
                "home_pace": 99.0, "away_pace": 97.0,
            },
            {
                "game_date": pd.Timestamp("2026-05-20"),
                "home_team": "BOS",
                "away_team": "NYK",
                "home_score": 110,
                "away_score": 90,
                "home_reb": 45, "away_reb": 40,
                "home_ast": 28, "away_ast": 22,
                "home_stl": 8, "away_stl": 6,
                "home_blk": 5, "away_blk": 3,
                "home_tov_rate": 0.10, "away_tov_rate": 0.12,
                "home_ortg": 115.0, "away_ortg": 105.0,
                "home_drtg": 105.0, "away_drtg": 115.0,
                "home_efg": 0.55, "away_efg": 0.48,
                "home_ts": 0.60, "away_ts": 0.52,
                "home_pace": 100.0, "away_pace": 98.0,
            },
        ])
        result = calculate_team_form(df, "BOS", pd.Timestamp("2026-05-22"), num_recent_games=10)
        assert "reb_last10" in str(list(result.keys()))
        # shift(1) makes first row NaN; second row has first game's stats
        assert not any(np.isnan(v) for v in result.values())
