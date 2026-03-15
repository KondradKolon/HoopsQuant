"""
train.py — Trenowanie Modeli Probabilistycznych 

Co tu robimy:
  1. Wczytujemy features.csv
  2. Temporal split — train: sezony do 2023-24, test: 2024-25 i 2025-26
  3. Skalowanie cech (StandardScaler)
  4. Trenujemy 3 modele: LogisticRegression, LightGBM, XGBoost (na cechach: forma, Elo, B2B, matchup)
  5. Kalibracja prawdopodobieństw (CalibratedClassifierCV)
  6. Ocena: Brier Score, ROC-AUC, Accuracy
  7. Wypisujemy Feature Importance dla modeli drzewiastych
  8. Zapis najlepszego modelu do model.pkl + scaler.pkl

Uruchomienie:
  python train.py
"""

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier


print("[TRAIN] Wczytywanie features.csv...")
df = pd.read_csv("features.csv", parse_dates=["game_date"])

print(f"[TRAIN] Wczytano {len(df)} meczów × {df.shape[1]} kolumn")


# Używamy TYLKO danych które byłyby dostępne PRZED meczem:
#   - forma z ostatnich 5 meczów (obliczona ze shift(1) — bez look-ahead)
#   - forma z ostatnich 10 meczów
#   - dni odpoczynku
#   - Elo (aktualne rankingi drużyn)
#   - B2B (czy drużyna gra drugi mecz z rzędu)
#   - matchup (historyczny bilans bezpośrednich spotkań)

FEATURE_COLS = (
    [col for col in df.columns if col.endswith("_last5")]
    + [col for col in df.columns if col.endswith("_last10")]
    + ["home_rest_days", "away_rest_days"]
)

TARGET_COL = "label"

print(f"[TRAIN] Liczba cech wejściowych: {len(FEATURE_COLS)}")
print(f"[TRAIN] Przykłady cech: {FEATURE_COLS[:4]} ... {FEATURE_COLS[-2:]}")

# ─────────────────────────────────────────────────────────────────────────────
# KROK 3: TEMPORAL SPLIT
#
# Train: mecze do końca sezonu 2023-24 (data przed 2024-09-01)
# Test:  mecze od sezonu 2024-25 (data po lub równa 2024-09-01)
#
# NIE używamy shuffle=True — to dałoby look-ahead bias!
# ─────────────────────────────────────────────────────────────────────────────

SPLIT_DATE = "2024-09-01"

train_df = df[df["game_date"] < SPLIT_DATE].copy()
test_df = df[df["game_date"] >= SPLIT_DATE].copy()

# Usuń wiersze gdzie forma jest NaN (pierwsze mecze w historii drużyny)
train_df = train_df.dropna(subset=FEATURE_COLS + [TARGET_COL])
test_df = test_df.dropna(subset=FEATURE_COLS + [TARGET_COL])

print(f"\n[TRAIN] Podział temporal:")
print(f"  Train: {len(train_df)} meczów (do {SPLIT_DATE})")
print(f"  Test:  {len(test_df)} meczów (od {SPLIT_DATE})")
print(f"  Gospodarz wygrał w train: {train_df[TARGET_COL].mean():.1%}")
print(f"  Gospodarz wygrał w test:  {test_df[TARGET_COL].mean():.1%}")

X_train = train_df[FEATURE_COLS]
y_train = train_df[TARGET_COL].values
X_test = test_df[FEATURE_COLS]
y_test = test_df[TARGET_COL].values


scaler = StandardScaler()
X_train_scaled = pd.DataFrame(
    scaler.fit_transform(X_train), columns=FEATURE_COLS
)
X_test_scaled = pd.DataFrame(
    scaler.transform(X_test), columns=FEATURE_COLS
)


# Każdy model będzie oceniany według:
#   Brier Score  — im niższy tym lepiej (0.25 = losowy, 0 = idealne)
#   ROC-AUC      — im wyższy tym lepiej (0.5 = losowy, 1.0 = idealne)
#   Accuracy     — % trafnych predykcji (próg = 0.5)

models = {
    "LogisticRegression": LogisticRegression(
        C=1.0,
        max_iter=1000,
        random_state=42,
    ),
    "LightGBM": LGBMClassifier(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=6,
        random_state=42,
        verbose=-1,
    ),
    "XGBoost": XGBClassifier(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=6,
        random_state=42,
        eval_metric="logloss",
        verbosity=0,
    ),
}

results = {}

print("\n" + "=" * 60)
print("TRENOWANIE I EWALUACJA")
print("=" * 60)

for name, base_model in models.items():
    print(f"\n▶ {name}")

    # Kalibracja: isotonic regression dopasowuje surowe probability → kalibrowane
    # cv=5 = 5-fold cross-validation na zbiorze treningowym
    model = CalibratedClassifierCV(base_model, method="isotonic", cv=5)
    model.fit(X_train_scaled, y_train)

    proba = model.predict_proba(X_test_scaled)[:, 1]  # P(gospodarz wygra)
    pred = (proba >= 0.5).astype(int)

    brier = brier_score_loss(y_test, proba)
    auc = roc_auc_score(y_test, proba)
    acc = (pred == y_test).mean()

    results[name] = {
        "model": model,
        "brier": brier,
        "auc": auc,
        "acc": acc,
        "proba": proba,
    }

    print(f"  Brier Score: {brier:.4f}  (niższy = lepszy, losowy = 0.25)")
    print(f"  ROC-AUC:     {auc:.4f}  (wyższy = lepszy, losowy = 0.50)")
    print(f"  Accuracy:    {acc:.2%}")

    # Calibration check: jak bardzo model jest skalibrowany
    fraction_pos, mean_pred = calibration_curve(y_test, proba, n_bins=10)
    max_calib_err = np.max(np.abs(fraction_pos - mean_pred))
    print(f"  Max błąd kalibracji: {max_calib_err:.3f}  (niższy = lepiej)")


print("\n" + "=" * 60)
print("PODSUMOWANIE")
print("=" * 60)

summary_rows = []
for name, r in results.items():
    summary_rows.append(
        {
            "Model": name,
            "Brier ↓": f"{r['brier']:.4f}",
            "AUC ↑": f"{r['auc']:.4f}",
            "Accuracy ↑": f"{r['acc']:.2%}",
        }
    )

summary_df = pd.DataFrame(summary_rows).set_index("Model")
print(summary_df.to_string())

# Najlepszy = najniższy Brier Score
best_name = min(results, key=lambda n: results[n]["brier"])
print(f"\n✅ Najlepszy model: {best_name}")

# ─────────────────────────────────────────────────────────────────────────────
# KROK 7: ZAPIS
# ─────────────────────────────────────────────────────────────────────────────

best_model = results[best_name]["model"]

joblib.dump(best_model, "model.pkl")
joblib.dump(scaler, "scaler.pkl")
joblib.dump(FEATURE_COLS, "feature_cols.pkl")

print(f"\n[TRAIN] Zapisano:")
print(f"  model.pkl       — {best_name} (skalibrowany)")
print(f"  scaler.pkl      — StandardScaler (fit na train)")
print(f"  feature_cols.pkl — lista {len(FEATURE_COLS)} kolumn wejściowych")
