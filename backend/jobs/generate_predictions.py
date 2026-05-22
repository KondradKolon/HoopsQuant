"""
generate_predictions.py — Job do Generowania Predykcji dla Nadchodzących Meczów

Co robi:
  1. Wczytuje wszystkie nadchodzące mecze z bazy (bez wyniku)
  2. Dla każdego meczu oblicza cechy z historii
  3. Uruchamia model ML aby otrzymać predykcje
  4. Zapisuje predykcje do tabeli predictions
  5. Loguje wyniki

Uruchomienie:
  python -m jobs.generate_predictions
  
Lub z głównego katalogu backend/:
  cd backend && python -m jobs.generate_predictions
"""

import logging
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s: %(message)s'
)
logger = logging.getLogger("generate_predictions")

from app.db.database import SessionLocal
from app.db.models import Game, Prediction
from app.services.predictions import generate_features_for_game, predict_game


def main():
    """Główna funkcja"""
    
    session = SessionLocal()
    
    try:
        logger.info("🔍 Wczytywanie nadchodzących meczów...")
        
        # Mecze bez wyniku (home_score is NULL)
        upcoming_games = session.query(Game).filter(
            Game.home_score.is_(None),
            Game.game_date >= datetime.now().date()
        ).order_by(Game.game_date).all()
        
        logger.info(f"   Znalezione {len(upcoming_games)} nadchodzące mecze")
        
        if len(upcoming_games) == 0:
            logger.info("   Brak meczów do predykcji")
            return
        
        predictions_created = 0
        predictions_updated = 0
        errors = 0
        
        for game in upcoming_games:
            try:
                logger.info(f"\n▶ {game.home_team} vs {game.away_team} ({game.game_date})")
                
                # 1. Obliczamy cechy
                features = generate_features_for_game(
                    game_id=game.game_id,
                    home_team=game.home_team,
                    away_team=game.away_team,
                    game_date=game.game_date,
                    session=session
                )
                
                if features is None:
                    logger.warning("   ⚠️ Nie udało się obliczyć cech")
                    errors += 1
                    continue
                
                # 2. Generujemy predykcję
                from app.services.predictions import load_model
                _, _, feature_cols = load_model()
                
                pred_result = predict_game(features, feature_cols)
                
                # 3. Sprawdzamy czy już istnieje predykcja
                existing_pred = session.query(Prediction).filter(
                    Prediction.game_id == game.game_id,
                    Prediction.model_name == "LogReg_C_0.01"
                ).first()
                
                if existing_pred:
                    # Update
                    existing_pred.home_win_prob = pred_result["home_win_prob"]
                    existing_pred.away_win_prob = pred_result["away_win_prob"]
                    existing_pred.confidence = pred_result["confidence"]
                    existing_pred.created_at = datetime.utcnow()
                    predictions_updated += 1
                    status = "✏️ UPDATED"
                else:
                    # Create
                    new_pred = Prediction(
                        game_id=game.game_id,
                        model_name="LogReg_C_0.01",
                        home_win_prob=pred_result["home_win_prob"],
                        away_win_prob=pred_result["away_win_prob"],
                        confidence=pred_result["confidence"]
                    )
                    session.add(new_pred)
                    predictions_created += 1
                    status = "✅ CREATED"
                
                logger.info(f"   {status} | Home: {pred_result['home_win_prob']:.1%} | Away: {pred_result['away_win_prob']:.1%} | Confidence: {pred_result['confidence']:.1%}")
                
            except Exception as e:
                logger.error(f"   ❌ Błąd: {e}")
                errors += 1
                continue
        
        # Commit do bazy
        session.commit()
        
        logger.info("\n" + "="*70)
        logger.info("PODSUMOWANIE")
        logger.info("="*70)
        logger.info(f"✅ Przedykcje utworzone: {predictions_created}")
        logger.info(f"✏️  Predykcje zaktualizowane: {predictions_updated}")
        logger.info(f"❌ Błędy: {errors}")
        logger.info(f"📊 Razem przetworzonych: {len(upcoming_games)}")
        
    finally:
        session.close()


if __name__ == "__main__":
    main()
