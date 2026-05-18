"""
train.py — Trenowanie Modeli Probabilistycznych (Walk-Forward Validation)

Co robimy:
  1. Wczytujemy features.csv
  2. Walk-forward validation: trenujemy na roku N, testujemy na roku N+1
  3. Skalowanie cech (StandardScaler)
  4. Testujemy modele: LogisticRegression (różne C), XGBoost
  5. Kalibracja prawdopodobieństw (CalibratedClassifierCV)
  6. Ocena: Brier Score, ROC-AUC, Accuracy, Log Loss
  7. Wybieramy najlepszy model na podstawie średniej z foldów
  8. Trenujemy finalny model na wszystkich danych
  9. Zapis: model.pkl, scaler.pkl, feature_cols.pkl

Uruchomienie:
  python train.py [--train-end YYYY-MM-DD]
"""

import argparse
import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score, log_loss
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier


def main():
    parser = argparse.ArgumentParser(description="Trenowanie modelu z opcjonalnym odcięciem daty.")
    parser.add_argument("--train-end", default="2025-12-31", help="Ostatni dzień danych do finalnego treningu (YYYY-MM-DD)")
    args = parser.parse_args()

    print("[TRAIN] Wczytywanie features.csv...")
    df = pd.read_csv("features.csv", parse_dates=["game_date"])
    df = df.sort_values("game_date").reset_index(drop=True)

    print(f"[TRAIN] Wczytano {len(df)} meczów × {df.shape[1]} kolumn")

    # ─────────────────────────────────────────────────────────────────────────────
    # KROK 1: PRZYGOTOWANIE CECH
    # ─────────────────────────────────────────────────────────────────────────────
    # Używamy TYLKO: forma z ostatnich 10 meczów + Elo + Elo diff
    # (bez stats z ostatnich 5 meczów aby uniknąć multicollinearity)
    
    FEATURE_COLS = (
        [col for col in df.columns if col.endswith("_last10")]
        + ["home_elo", "away_elo", "elo_diff"]
    )

    TARGET_COL = "label"

    # Odrzucamy puste wartości przed podziałem
    df = df.dropna(subset=FEATURE_COLS + [TARGET_COL])

    print(f"[TRAIN] Liczba cech wejściowych: {len(FEATURE_COLS)}")
    print(f"[TRAIN] Przykłady cech: {FEATURE_COLS[:4]} ... {FEATURE_COLS[-3:]}")

    # ─────────────────────────────────────────────────────────────────────────────
    # KROK 2: WALK-FORWARD VALIDATION (TIME SERIES SPLIT)
    # ─────────────────────────────────────────────────────────────────────────────
    # Trenujemy na 1 roku wstecz -> Testujemy na bieżącym roku
    # NIE używamy shuffle=True — to dałoby look-ahead bias!

    SPLITS = [
        # Fold 1: Trenujemy na 22/23, Testujemy na 23/24
        {"train_start": "2022-09-01", "train_end": "2023-09-01", "test_end": "2024-09-01"},
        # Fold 2: Trenujemy na 23/24, Testujemy na 24/25
        {"train_start": "2023-09-01", "train_end": "2024-09-01", "test_end": "2025-06-01"},
    ]

    # ─────────────────────────────────────────────────────────────────────────────
    # KROK 3: KONFIGURACJA MODELI
    # ─────────────────────────────────────────────────────────────────────────────
    models_to_test = {
        "LogReg_C_10": LogisticRegression(C=10.0, max_iter=2000, random_state=42),
        "LogReg_C_1.0": LogisticRegression(C=1.0, max_iter=2000, random_state=42),
        "LogReg_C_0.1": LogisticRegression(C=0.1, max_iter=2000, random_state=42),
        "LogReg_C_0.01": LogisticRegression(C=0.01, max_iter=2000, random_state=42),
        "XGBoost_Sports_Tuned": XGBClassifier(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=2,              # SUPER SHALLOW - max 2 splits per tree
            subsample=0.8,            # Random 20% game dropout per tree
            colsample_bytree=0.8,     # Random 20% feature dropout per tree
            reg_lambda=10,            # L2 regularization
            reg_alpha=10,             # L1 regularization
            random_state=42,
            verbosity=0,
        )
    }

    aggregate_results = {name: {"brier": [], "auc": [], "acc": [], "log_loss": []} for name in models_to_test.keys()}

    print("\n" + "=" * 70)
    print("WALK-FORWARD VALIDATION")
    print("=" * 70)

    for idx, split in enumerate(SPLITS, 1):
        print(f"\n[FOLD {idx}] Train: {split['train_start']} → {split['train_end']} | Test: {split['train_end']} → {split['test_end']}")
        
        # Podział danych
        train_df = df[(df["game_date"] >= split["train_start"]) & (df["game_date"] < split["train_end"])].copy()
        test_df = df[(df["game_date"] >= split["train_end"]) & (df["game_date"] < split["test_end"])].copy()

        print(f"         Train size: {len(train_df)} | Test size: {len(test_df)}")

        X_train = train_df[FEATURE_COLS]
        y_train = train_df[TARGET_COL].values
        X_test = test_df[FEATURE_COLS]
        y_test = test_df[TARGET_COL].values

        # Skalowanie wewnątrz foldu (chroni przed data leakage)
        scaler = StandardScaler()
        X_train_scaled = pd.DataFrame(scaler.fit_transform(X_train), columns=FEATURE_COLS)
        X_test_scaled = pd.DataFrame(scaler.transform(X_test), columns=FEATURE_COLS)

        for name, base_model in models_to_test.items():
            # Kalibracja: sigmoid method jest szybsza niż isotonic
            model = CalibratedClassifierCV(base_model, method="sigmoid", cv=5)
            model.fit(X_train_scaled, y_train)

            proba = model.predict_proba(X_test_scaled)[:, 1]  # P(home team wins)
            pred = (proba >= 0.5).astype(int)

            brier = brier_score_loss(y_test, proba)
            auc = roc_auc_score(y_test, proba)
            acc = (pred == y_test).mean()
            lloss = log_loss(y_test, proba)

            aggregate_results[name]["brier"].append(brier)
            aggregate_results[name]["auc"].append(auc)
            aggregate_results[name]["acc"].append(acc)
            aggregate_results[name]["log_loss"].append(lloss)

            print(f"  > {name:25s} | Brier: {brier:.4f} | AUC: {auc:.4f} | Acc: {acc:.2%} | LogLoss: {lloss:.4f}")

    # ─────────────────────────────────────────────────────────────────────────────
    # KROK 4: PODSUMOWANIE (ŚREDNIE Z WSZYSTKICH FOLDÓW)
    # ─────────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("PODSUMOWANIE (ŚREDNIA Z WSZYSTKICH FOLDÓW)")
    print("=" * 70)

    summary_rows = []
    for name, metrics in aggregate_results.items():
        avg_brier = np.mean(metrics["brier"])
        avg_auc = np.mean(metrics["auc"])
        avg_acc = np.mean(metrics["acc"])
        avg_lloss = np.mean(metrics["log_loss"])
        summary_rows.append({
            "Model": name, 
            "Brier ↓": avg_brier, 
            "AUC ↑": avg_auc, 
            "Accuracy ↑": avg_acc,
            "LogLoss ↓": avg_lloss
        })

    summary_df = pd.DataFrame(summary_rows).set_index("Model")
    print(summary_df.to_string(
        float_format=lambda x: f"{x:.4f}" if x < 1 else f"{x:.2%}"
    ))

    # Wybieramy najlepszy model na podstawie Brier Score (najniższy)
    best_name = summary_df["Brier ↓"].idxmin()
    best_base_model = models_to_test[best_name]
    
    print(f"\n✅ Najlepszy model: {best_name} (Brier: {summary_df.loc[best_name, 'Brier ↓']:.4f})")

    # ─────────────────────────────────────────────────────────────────────────────
    # KROK 5: TRENOWANIE FINALNEGO MODELU PRODUKCYJNEGO
    # ─────────────────────────────────────────────────────────────────────────────
    print(f"\n[TRAIN] Ograniczanie danych do daty: {args.train_end}")
    
    # Filtrujemy dane - odrzucamy wszystko po `--train-end`
    train_mask = df["game_date"] <= args.train_end
    df_final_train = df[train_mask]
    
    print(f"[TRAIN] Do finalnego treningu użyto {len(df_final_train)} meczów")
    print(f"[TRAIN] Trenowanie ostatecznego modelu ({best_name})...")

    X_final = df_final_train[FEATURE_COLS]
    y_final = df_final_train[TARGET_COL].values

    final_scaler = StandardScaler()
    X_final_scaled = pd.DataFrame(final_scaler.fit_transform(X_final), columns=FEATURE_COLS)

    final_model = CalibratedClassifierCV(best_base_model, method="sigmoid", cv=10)
    final_model.fit(X_final_scaled, y_final)

    # ─────────────────────────────────────────────────────────────────────────────
    # KROK 6: FEATURE IMPORTANCE (TYLKO DLA LOGISTIC REGRESSION)
    # ─────────────────────────────────────────────────────────────────────────────
    if "LogReg" in best_name:
        print("\n" + "=" * 70)
        print("WAGI CECH OSTATECZNEGO MODELU (FEATURE IMPORTANCE)")
        print("=" * 70)
        try:
            all_coefs = [clf.estimator.coef_[0] for clf in final_model.calibrated_classifiers_]
            avg_coefs = np.mean(all_coefs, axis=0)

            importance_df = pd.DataFrame({
                "Feature": FEATURE_COLS,
                "Weight": avg_coefs,
                "Impact": np.abs(avg_coefs)
            }).sort_values(by="Impact", ascending=False).reset_index(drop=True)
            
            print(importance_df[["Feature", "Weight"]].head(15).to_string())
        except (AttributeError, IndexError) as e:
            print(f"Nie można wyciągnąć wag: {e}")

    # ─────────────────────────────────────────────────────────────────────────────
    # KROK 7: ZAPIS MODELU
    # ─────────────────────────────────────────────────────────────────────────────
    joblib.dump(final_model, "model.pkl")
    joblib.dump(final_scaler, "scaler.pkl")
    joblib.dump(FEATURE_COLS, "feature_cols.pkl")

    print(f"\n✅ [TRAIN] Zapisano pliki modelu:")
    print(f"   model.pkl       — {best_name} (skalibrowany)")
    print(f"   scaler.pkl      — StandardScaler")
    print(f"   feature_cols.pkl — {len(FEATURE_COLS)} cech")
    print(f"\n💡 Model NIE WIDZIAŁ meczów po: {args.train_end}")


if __name__ == "__main__":
    main()
