"""
train_2026.py — Train on 2025-26 season only (for current / playoff predictions)

Uses features.csv filtered to season 2025-26 (same 27 features as production playoff model).
Temporal split for evaluation (default 70/30), then fits LogReg_C_0.01 on all
completed games in the season for playoff inference.

Saves to backend/models/playoff_model.pkl (and scaler / feature_cols).

Usage (from backend/):
  python scripts/train_2026.py
  python scripts/train_2026.py --train-frac 0.7
"""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

SEASON = "2025-26"
DEPLOY_MODEL = "LogReg_C_0.01"
MODELS_DIR = Path(__file__).parent.parent / "models"


def build_feature_cols(df: pd.DataFrame) -> list[str]:
    return (
        [col for col in df.columns if col.endswith("_last10")]
        + ["home_elo", "away_elo", "elo_diff"]
        + ["matchup_home_wins_last5", "matchup_pts_diff_last5", "matchup_net_ortg_last5"]
        + ["is_playoff"]
    )


def load_season_df() -> pd.DataFrame:
    path = Path(__file__).parent.parent / "features.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run: python scripts/features.py"
        )
    df = pd.read_csv(path, parse_dates=["game_date"])
    df = df[df["season"] == SEASON].copy()
    df = df[df["home_score"].notna()].copy()
    df = df.drop_duplicates(subset=["game_date", "home_team", "away_team"], keep="last")
    df = df.sort_values("game_date").reset_index(drop=True)
    return df


def get_models() -> dict:
    return {
        "LogReg_C_0.01": LogisticRegression(C=0.01, max_iter=2000, random_state=42),
        "LogReg_C_0.1": LogisticRegression(C=0.1, max_iter=2000, random_state=42),
        "LogReg_C_1.0": LogisticRegression(C=1.0, max_iter=2000, random_state=42),
        "XGBoost_Sports_Tuned": XGBClassifier(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=2,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_lambda=10,
            reg_alpha=10,
            random_state=42,
            verbosity=0,
        ),
    }


def evaluate_models(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_test: pd.DataFrame,
    y_test: np.ndarray,
    models: dict,
    force_logreg: bool,
) -> tuple[str, dict]:
    scaler = StandardScaler()
    X_train_s = pd.DataFrame(scaler.fit_transform(X_train), columns=X_train.columns)
    X_test_s = pd.DataFrame(scaler.transform(X_test), columns=X_test.columns)

    results: dict = {}
    print("\n" + "=" * 70)
    print(f"TRENOWANIE I EWALUACJA (sezon {SEASON}, split chronologiczny)")
    print("=" * 70)

    for name, base_model in models.items():
        clf = CalibratedClassifierCV(base_model, method="sigmoid", cv=5)
        clf.fit(X_train_s, y_train)
        proba = clf.predict_proba(X_test_s)[:, 1]
        pred = (proba >= 0.5).astype(int)
        results[name] = {
            "brier": brier_score_loss(y_test, proba),
            "auc": roc_auc_score(y_test, proba),
            "acc": (pred == y_test).mean(),
            "log_loss": log_loss(y_test, proba),
        }
        r = results[name]
        print(
            f"  {name:25s} | Brier: {r['brier']:.4f} | AUC: {r['auc']:.4f} "
            f"| Acc: {r['acc']:.2%} | LogLoss: {r['log_loss']:.4f}"
        )

    # Playoff-only holdout (last portion of test set if labeled)
    print("\n--- Tylko mecze playoff w zbiorze test (jeśli są) ---")

    best_name = min(results, key=lambda n: results[n]["brier"])
    if force_logreg:
        for candidate in ("LogReg_C_0.01", "LogReg_C_0.1", "LogReg_C_1.0"):
            if candidate in models:
                best_name = candidate
                break
        print(f"\nWymuszono LogReg: {best_name}")
    else:
        print(f"\nNajlepszy model (Brier): {best_name}")

    return best_name, results


def main() -> None:
    parser = argparse.ArgumentParser(description="Train 2025-26 season model for playoffs")
    parser.add_argument(
        "--train-frac",
        type=float,
        default=0.7,
        help="Chronological train fraction for evaluation (default 0.7 = 70/30)",
    )
    args = parser.parse_args()

    print(f"[TRAIN-2026] Wczytywanie features.csv (sezon {SEASON})...")
    df = load_season_df()
    feature_cols = build_feature_cols(df)
    df = df.dropna(subset=feature_cols + ["label"])

    print(f"[TRAIN-2026] {len(df)} meczów (regular: {(df['is_playoff']==0).sum()}, playoff: {(df['is_playoff']==1).sum()})")
    print(f"[TRAIN-2026] {len(feature_cols)} cech (z is_playoff)")

    split_idx = int(len(df) * args.train_frac)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]

    X_train = train_df[feature_cols]
    y_train = train_df["label"].values
    X_test = test_df[feature_cols]
    y_test = test_df["label"].values

    print(
        f"\nTrain: {len(train_df)} ({train_df['game_date'].min().date()} → {train_df['game_date'].max().date()})"
    )
    print(
        f"Test:  {len(test_df)} ({test_df['game_date'].min().date()} → {test_df['game_date'].max().date()})"
    )

    models = get_models()
    best_name, results = evaluate_models(
        X_train, y_train, X_test, y_test, models, force_logreg=False
    )

    if len(test_df[test_df["is_playoff"] == 1]) > 0:
        test_playoff = test_df[test_df["is_playoff"] == 1]
        scaler_p = StandardScaler()
        X_tr_s = scaler_p.fit_transform(train_df[feature_cols])
        X_tp_s = scaler_p.transform(test_playoff[feature_cols])
        clf = CalibratedClassifierCV(models[DEPLOY_MODEL], method="sigmoid", cv=5)
        clf.fit(X_tr_s, y_train)
        proba = clf.predict_proba(X_tp_s)[:, 1]
        acc_p = ((proba >= 0.5) == test_playoff["label"].values).mean()
        print(f"  Playoff test accuracy ({DEPLOY_MODEL}, {len(test_playoff)} gier): {acc_p:.2%}")

    deploy_name = DEPLOY_MODEL
    print(
        f"\n[TRAIN-2026] Finalny model produkcyjny: {deploy_name} "
        f"(eval winner by Brier: {best_name}) na całym sezonie {SEASON}..."
    )
    X_final = df[feature_cols]
    y_final = df["label"].values

    final_scaler = StandardScaler()
    X_final_s = pd.DataFrame(
        final_scaler.fit_transform(X_final), columns=feature_cols
    )

    final_model = CalibratedClassifierCV(models[deploy_name], method="sigmoid", cv=10)
    final_model.fit(X_final_s, y_final)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_model, MODELS_DIR / "playoff_model.pkl")
    joblib.dump(final_scaler, MODELS_DIR / "playoff_scaler.pkl")
    joblib.dump(feature_cols, MODELS_DIR / "playoff_feature_cols.pkl")

    size_kb = (MODELS_DIR / "playoff_model.pkl").stat().st_size // 1024
    print(f"\n[TRAIN-2026] Zapisano do {MODELS_DIR}/")
    print(f"   playoff_model.pkl       — {deploy_name} (~{size_kb} KB)")
    print(f"   playoff_scaler.pkl")
    print(f"   playoff_feature_cols.pkl — {len(feature_cols)} cech")
    print("\nUżycie: predict_game() ładuje te pliki gdy game_date >= playoff cutoff.")


if __name__ == "__main__":
    main()
