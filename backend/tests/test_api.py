"""Integration tests for API routes using TestClient + in-memory SQLite."""

from datetime import date, timedelta

from app.db.models import Odds


class TestHealthEndpoint:
    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "HoopsQuant API"
        assert data["status"] == "online"

    def test_health(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestGamesEndpoint:
    def test_get_upcoming_games_empty(self, client):
        resp = client.get("/api/v1/games/upcoming")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_upcoming_games_with_data(self, client, db_session):
        from tests.conftest import sample_game, sample_prediction
        game = sample_game(db_session)
        sample_prediction(db_session, game_id=game.game_id)

        resp = client.get("/api/v1/games/upcoming")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["game_id"] == game.game_id
        assert data[0]["prediction"]["home_win_prob"] == 0.55

    def test_get_games_all(self, client, db_session):
        from tests.conftest import sample_game
        sample_game(db_session)
        sample_game(db_session, game_id="TEST002", home_team="LAL", away_team="GSW")

        resp = client.get("/api/v1/games")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_get_games_with_season_filter(self, client, db_session):
        from tests.conftest import sample_game
        sample_game(db_session)
        sample_game(db_session, game_id="TEST002", season="2024-25")

        resp = client.get("/api/v1/games?season=2024-25")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["game_id"] == "TEST002"

    def test_get_game_count(self, client, db_session):
        from tests.conftest import sample_game
        sample_game(db_session)
        sample_game(db_session, game_id="TEST002")

        resp = client.get("/api/v1/games/count")
        assert resp.status_code == 200
        assert resp.json()["total_games"] == 2

    def test_get_game_prediction_found(self, client, db_session):
        from tests.conftest import sample_game, sample_prediction
        game = sample_game(db_session)
        sample_prediction(db_session, game_id=game.game_id)

        resp = client.get(f"/api/v1/games/{game.game_id}/prediction")
        assert resp.status_code == 200
        data = resp.json()
        assert data["game"]["game_id"] == game.game_id
        assert data["prediction"]["home_win_prob"] == 0.55

    def test_get_game_prediction_not_found(self, client):
        resp = client.get("/api/v1/games/NONEXISTENT/prediction")
        assert resp.status_code == 404

    def test_get_game_prediction_without_prediction(self, client, db_session):
        from tests.conftest import sample_game
        game = sample_game(db_session)

        resp = client.get(f"/api/v1/games/{game.game_id}/prediction")
        assert resp.status_code == 200
        assert resp.json()["prediction"] is None


class TestDashboardEndpoint:
    def test_upcoming_games_empty(self, client):
        resp = client.get("/api/v1/dashboard/games/upcoming")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_upcoming_games_with_odds(self, client, db_session):
        from datetime import date, timedelta

        from tests.conftest import sample_game, sample_odds, sample_prediction
        future = date.today() + timedelta(days=2)
        game = sample_game(db_session, game_date=future)
        sample_odds(db_session, game_id=game.game_id)
        sample_prediction(db_session, game_id=game.game_id)

        resp = client.get("/api/v1/dashboard/games/upcoming")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["best_odds"]["home"] == 1.5
        assert data[0]["prediction"]["confidence"] == 0.55


class TestArbitrageEndpoint:
    def test_no_opportunities_with_single_odds(self, client, db_session):
        from tests.conftest import sample_game, sample_odds
        sample_game(db_session)
        sample_odds(db_session)

        resp = client.get("/api/v1/arbitrage/opportunities")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_arb_opportunity_detected(self, client, db_session):
        from tests.conftest import sample_game
        game = sample_game(db_session)

        o1 = Odds(game_id=game.game_id, bookmaker="Superbet", home_win_odds=2.0, away_win_odds=1.8)
        o2 = Odds(game_id=game.game_id, bookmaker="Stake", home_win_odds=1.5, away_win_odds=2.5)
        db_session.add_all([o1, o2])
        db_session.commit()

        resp = client.get("/api/v1/arbitrage/opportunities")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        # With Superbet home=2.0 (50%) + Stake away=2.5 (40%) = 90% -> 10% arb
        assert any(o["ev_percent"] >= 10.0 for o in data)

    def test_dashboard_arbitrage(self, client, db_session):
        from tests.conftest import sample_game
        game = sample_game(db_session)

        o1 = Odds(game_id=game.game_id, bookmaker="Superbet", home_win_odds=2.0, away_win_odds=1.8)
        o2 = Odds(game_id=game.game_id, bookmaker="Stake", home_win_odds=1.5, away_win_odds=2.5)
        db_session.add_all([o1, o2])
        db_session.commit()

        resp = client.get("/api/v1/dashboard/arbitrage")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] > 0


class TestWatchlistEndpoint:
    def test_get_watchlist_empty(self, client, db_session):
        from tests.conftest import sample_user
        user = sample_user(db_session)

        from app.middleware import get_current_user_id
        def override_auth():
            return user.supabase_id
        client.app.dependency_overrides[get_current_user_id] = override_auth

        resp = client.get("/api/v1/me/watchlist")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_add_and_remove_watchlist(self, client, db_session):
        from tests.conftest import sample_game, sample_user
        user = sample_user(db_session)
        game = sample_game(db_session)

        from app.middleware import get_current_user_id
        def override_auth():
            return user.supabase_id
        client.app.dependency_overrides[get_current_user_id] = override_auth

        resp = client.post(f"/api/v1/me/watchlist/{game.game_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

        resp = client.get("/api/v1/me/watchlist")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["game_id"] == game.game_id

        resp = client.delete(f"/api/v1/me/watchlist/{game.game_id}")
        assert resp.status_code == 200

        resp = client.get("/api/v1/me/watchlist")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_add_duplicate_watchlist(self, client, db_session):
        from tests.conftest import sample_game, sample_user
        user = sample_user(db_session)
        game = sample_game(db_session)

        from app.middleware import get_current_user_id
        def override_auth():
            return user.supabase_id
        client.app.dependency_overrides[get_current_user_id] = override_auth

        client.post(f"/api/v1/me/watchlist/{game.game_id}")
        resp = client.post(f"/api/v1/me/watchlist/{game.game_id}")
        assert resp.json()["status"] == "already_exists"

    def test_remove_nonexistent_watchlist(self, client, db_session):
        from tests.conftest import sample_user
        user = sample_user(db_session)

        from app.middleware import get_current_user_id
        def override_auth():
            return user.supabase_id
        client.app.dependency_overrides[get_current_user_id] = override_auth

        resp = client.delete("/api/v1/me/watchlist/NONEXISTENT")
        assert resp.status_code == 404


class TestEloEndpoint:
    def test_rankings_empty(self, client):
        resp = client.get("/api/v1/elo/rankings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["teams"] == []

    def test_rankings_with_games(self, client, db_session):
        from tests.conftest import sample_game
        today = date.today()
        sample_game(db_session, game_id="G1", home_team="BOS", away_team="NYK",
                     game_date=today - timedelta(days=2), home_score=110, away_score=90,
                     home_team_wins=1.0)
        sample_game(db_session, game_id="G2", home_team="LAL", away_team="GSW",
                     game_date=today - timedelta(days=1), home_score=95, away_score=105,
                     home_team_wins=0.0)

        resp = client.get("/api/v1/elo/rankings")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["teams"]) == 4
        assert data["season"] == "2025-26"

    def test_elo_upcoming(self, client, db_session):
        from tests.conftest import sample_game
        today = date.today()
        sample_game(db_session, game_id="G1", home_team="BOS", away_team="NYK",
                     game_date=today - timedelta(days=2), home_score=110, away_score=90,
                     home_team_wins=1.0)
        sample_game(db_session, game_id="G2", home_team="LAL", away_team="GSW",
                     game_date=today + timedelta(days=1), home_score=None, away_score=None,
                     home_team_wins=None)

        resp = client.get("/api/v1/elo/upcoming")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["games"]) == 1
        assert data["games"][0]["prediction"] is not None

    def test_elo_trend(self, client, db_session):
        from tests.conftest import sample_game
        today = date.today()
        sample_game(db_session, game_id="G1", home_team="BOS", away_team="NYK",
                     game_date=today - timedelta(days=2), home_score=110, away_score=90,
                     home_team_wins=1.0)

        resp = client.get("/api/v1/elo/trend?team=BOS")
        assert resp.status_code == 200
        data = resp.json()
        assert data["team"] == "BOS"
        assert len(data["points"]) == 1
