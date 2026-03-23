"""
train.py — Trenowanie Modeli Probabilistycznych (Walk-Forward Validation)
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
    # --- DODANO ARGPARSE ABY KONTROLOWAĆ DATĘ KOŃCOWĄ ---
    parser = argparse.ArgumentParser(description="Trenowanie modelu z odcięciem daty.")
    parser.add_argument("--train-end", default="2025-12-31", help="Ostatni dzień danych do treningu (YYYY-MM-DD)")
    args = parser.parse_args()

    print("[TRAIN] Wczytywanie features.csv...")
    df = pd.read_csv("features.csv", parse_dates=["game_date"])
    df = df.sort_values("game_date").reset_index(drop=True)

    print(f"[TRAIN] Wczytano ogółem {len(df)} meczów × {df.shape[1]} kolumn")

    FEATURE_COLS = (
        [col for col in df.columns if col.endswith("_last10")]
        + ["home_elo", "away_elo", "elo_diff"]
    )

    TARGET_COL = "label"

    # Odrzucamy puste wartości przed podziałem
    df = df.dropna(subset=FEATURE_COLS + [TARGET_COL])

    print(f"[TRAIN] Liczba cech wejściowych po czyszczeniu: {len(FEATURE_COLS)}")

    # ─────────────────────────────────────────────────────────────────────────────
    # KROK 3: WALK-FORWARD VALIDATION (TIME SERIES SPLIT)
    # ─────────────────────────────────────────────────────────────────────────────
    SPLITS = [
        {"train_start": "2022-09-01", "train_end": "2023-09-01", "test_end": "2024-09-01"},
        {"train_start": "2023-09-01", "train_end": "2024-09-01", "test_end": "2025-06-01"},
    ]

    models_to_test = {
        "LogReg_C_10": LogisticRegression(C=10.0, max_iter=2000, random_state=42),
        "LogReg_C_1.0": LogisticRegression(C=1.0, max_iter=2000, random_state=42),
        "LogReg_C_0.1": LogisticRegression(C=0.1, max_iter=2000, random_state=42),
        "LogReg_C_0.01": LogisticRegression(C=0.01, max_iter=2000, random_state=42),
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
        )
    }

    aggregate_results = {name: {"brier": [], "auc": [], "acc": [], "log loss": []} for name in models_to_test.keys()}

    print("\n" + "=" * 60)
    print("ROZPOCZĘCIE WALK-FORWARD VALIDATION")
    print("=" * 60)

    for idx, split in enumerate(SPLITS, 1):
        print(f"\n[FOLD {idx}] Train: {split['train_start']} -> {split['train_end']} | Test: {split['train_end']} -> {split['test_end']}")
        
        train_df = df[(df["game_date"] >= split["train_start"]) & (df["game_date"] < split["train_end"])].copy()
        test_df = df[(df["game_date"] >= split["train_end"]) & (df["game_date"] < split["test_end"])].copy()

        X_train = train_df[FEATURE_COLS]
        y_train = train_df[TARGET_COL].values
        X_test = test_df[FEATURE_COLS]
        y_test = test_df[TARGET_COL].values

        scaler = StandardScaler()
        X_train_scaled = pd.DataFrame(scaler.fit_transform(X_train), columns=FEATURE_COLS)
        X_test_scaled = pd.DataFrame(scaler.transform(X_test), columns=FEATURE_COLS)

        for name, base_model in models_to_test.items():
            model = CalibratedClassifierCV(base_model, method="sigmoid", cv=5)
            model.fit(X_train_scaled, y_train)

            proba = model.predict_proba(X_test_scaled)[:, 1]
            pred = (proba >= 0.5).astype(int)

            brier = brier_score_loss(y_test, proba)
            auc = roc_auc_score(y_test, proba)
            acc = (pred == y_test).mean()
            lloss = log_loss(y_test, proba)
            
            aggregate_results[name]["brier"].append(brier)
            aggregate_results[name]["auc"].append(auc)
            aggregate_results[name]["acc"].append(acc)
            aggregate_results[name]["log loss"].append(lloss)

            print(f"  > {name}: Brier: {brier:.4f} | AUC: {auc:.4f} | Acc: {acc:.2%} | Log Loss: {lloss:.4f} ")

    # ─────────────────────────────────────────────────────────────────────────────
    # KROK 4: PODSUMOWANIE (ŚREDNIE Z FOLDÓW)
    # ─────────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("PODSUMOWANIE (ŚREDNIA Z WSZYSTKICH FOLDÓW)")
    print("=" * 60)

    summary_rows = []
    for name, metrics in aggregate_results.items():
        summary_rows.append({
            "Model": name, 
            "Brier ↓": np.mean(metrics["brier"]), 
            "AUC ↑": np.mean(metrics["auc"]), 
            "Accuracy ↑": np.mean(metrics["acc"]),
            "Log Loss": np.mean(metrics["log loss"])
        })

    summary_df = pd.DataFrame(summary_rows).set_index("Model")
    print(summary_df.applymap(lambda x: f"{x:.4f}" if x < 1 else f"{x:.2%}").to_string())

    # Wybieramy najlepszy model na podstawie Brier Score
    best_name = summary_df["Brier ↓"].idxmin()
    best_base_model = models_to_test[best_name] # <-- POPRAWIONY BŁĄD! Teraz działa też z XGBoost
    
    print(f"\n✅ Prawdziwie najlepszy model: {best_name}")

    # ─────────────────────────────────────────────────────────────────────────────
    # KROK 5: TRENOWANIE FINALNEGO MODELU PRODUKCYJNEGO Z ODCIĘCIEM DATY
    # ─────────────────────────────────────────────────────────────────────────────
    print(f"\n[TRAIN] Ograniczanie danych do daty: {args.train_end}")
    
    # Filtrujemy dane - odrzucamy wszystko po `--train-end` (np. odrzucamy styczeń 2026)
    train_mask = df["game_date"] <= args.train_end
    df_final_train = df[train_mask]
    
    print(f"[TRAIN] Do finalnego treningu użyto {len(df_final_train)} meczów.")
    print(f"[TRAIN] Trenowanie ostatecznego modelu ({best_name})...")

    X_final = df_final_train[FEATURE_COLS]
    y_final = df_final_train[TARGET_COL].values

    final_scaler = StandardScaler()
    X_final_scaled = pd.DataFrame(final_scaler.fit_transform(X_final), columns=FEATURE_COLS)

    final_model = CalibratedClassifierCV(best_base_model, method="sigmoid", cv=10)
    final_model.fit(X_final_scaled, y_final)

    # Wyciąganie wag (Tylko dla Logistic Regression, XGBoost tego nie obsługuje w ten sam sposób)
    if "LogReg" in best_name:
        print("\n" + "=" * 60)
        print("WAGI CECH OSTATECZNEGO MODELU PRODUKCYJNEGO")
        print("=" * 60)
        try:
            all_coefs = [clf.estimator.coef_[0] for clf in final_model.calibrated_classifiers_]
            avg_coefs = np.mean(all_coefs, axis=0)

            importance_df = pd.DataFrame({
                "Feature": FEATURE_COLS,
                "Weight": avg_coefs,
                "Impact": np.abs(avg_coefs)
            }).sort_values(by="Impact", ascending=False).reset_index(drop=True)
            print(importance_df[["Feature", "Weight"]].head(15).to_string())
        except AttributeError:
            pass

    # Zapis
    joblib.dump(final_model, "model.pkl")
    joblib.dump(final_scaler, "scaler.pkl")
    joblib.dump(FEATURE_COLS, "feature_cols.pkl")

    print(f"\n[TRAIN] Zapisano pliki modelu! Model nie widział meczów po {args.train_end}.")

if __name__ == "__main__":
    main()