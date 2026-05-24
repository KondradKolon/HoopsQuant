"""Unit tests for Elo route helper functions."""

import pandas as pd
import pytest

from app.api.routes.elo import compute_team_record, elo_prob


class TestEloProb:
    def test_equal_elo(self):
        prob = elo_prob(1500, 1500)
        # HOME_ADVANTAGE=50 gives home team ~57% vs equal Elo
        assert prob == pytest.approx(0.571, rel=0.01)

    def test_home_favorite(self):
        prob = elo_prob(1600, 1400)
        assert prob > 0.5
        assert prob < 0.99

    def test_home_underdog(self):
        prob = elo_prob(1400, 1600)
        assert prob < 0.5
        assert prob > 0.01

    def test_large_difference(self):
        prob = elo_prob(1800, 1200)
        assert prob > 0.9

    def test_home_advantage(self):
        prob_home = elo_prob(1500, 1500)
        assert prob_home > 0.5  # home court advantage makes >50%


class TestComputeTeamRecord:
    def test_empty_df(self):
        df = pd.DataFrame(columns=["home_team", "away_team", "home_team_wins"])
        wins, losses = compute_team_record(df, "BOS")
        assert wins == 0
        assert losses == 0

    def test_home_wins_only(self):
        df = pd.DataFrame([
            {"home_team": "BOS", "away_team": "NYK", "home_team_wins": 1.0},
            {"home_team": "BOS", "away_team": "MIA", "home_team_wins": 1.0},
        ])
        wins, losses = compute_team_record(df, "BOS")
        assert wins == 2
        assert losses == 0

    def test_home_losses_only(self):
        df = pd.DataFrame([
            {"home_team": "BOS", "away_team": "NYK", "home_team_wins": 0.0},
            {"home_team": "BOS", "away_team": "MIA", "home_team_wins": 0.0},
        ])
        wins, losses = compute_team_record(df, "BOS")
        assert wins == 0
        assert losses == 2

    def test_away_wins(self):
        df = pd.DataFrame([
            {"home_team": "NYK", "away_team": "BOS", "home_team_wins": 0.0},
        ])
        wins, losses = compute_team_record(df, "BOS")
        assert wins == 1
        assert losses == 0

    def test_away_losses(self):
        df = pd.DataFrame([
            {"home_team": "NYK", "away_team": "BOS", "home_team_wins": 1.0},
        ])
        wins, losses = compute_team_record(df, "BOS")
        assert wins == 0
        assert losses == 1

    def test_mixed_record(self):
        df = pd.DataFrame([
            {"home_team": "BOS", "away_team": "NYK", "home_team_wins": 1.0},
            {"home_team": "BOS", "away_team": "MIA", "home_team_wins": 0.0},
            {"home_team": "CHI", "away_team": "BOS", "home_team_wins": 0.0},
            {"home_team": "CHI", "away_team": "BOS", "home_team_wins": 1.0},
        ])
        wins, losses = compute_team_record(df, "BOS")
        assert wins == 2  # home win vs NYK + away win at CHI
        assert losses == 2  # home loss vs MIA + away loss at CHI
