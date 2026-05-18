"""
train_2026.py — Trenowanie Modelu na Danych Sezonu 2025-26

Co robimy:
  1. Wczytujemy features_2026.csv
  2. Temporal split: trenujemy na CAŁYM sezonie, testujemy na jego końcu
  3. Skalowanie cech (StandardScaler)
  4. Testujemy modele: LogisticRegression + XGBoost
  5. Kalibracja prawdopodobieństw
  6. Ocena: Brier Score, ROC-AUC, Accuracy, Log Loss
  7. Zapis: model_2026.pkl, scaler_2026.pkl, feature_cols_2026.pkl

Uruchomienie:
  python train_2026.py
  
💡 Notatka: Ponieważ mamy tylko 1 sezon (2025-26), nie możemy zrobić
   Walk-Forward Validation. Zamiast tego trenujemy na całym sezonie.
   Dla playoffów używamy tego modelu.
"""

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score, log_loss
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier


print("[TRAIN-2026] Wczytywanie features_2026.csv...")
df = pd.read_csv("features_2026.csv", parse_dates=["game_date"])
df = df.sort_values("game_date").reset_index(drop=True)

print(f"[TRAIN-2026] Wczytano {len(df)} meczów × {df.shape[1]} kolumn")

# ─────────────────────────────────────────────────────────────────────────────
# KROK 1: PRZYGOTOWANIE CECH
# ─────────────────────────────────────────────────────────────────────────────

FEATURE_COLS = (
    [col for col in df.columns if col.endswith("_last10")]
    + ["home_elo", "away_elo", "elo_diff"]
)

TARGET_COL = "label"

# Odrzucamy puste wartości
df = df.dropna(subset=FEATURE_COLS + [TARGET_COL])

print(f"[TRAIN-2026] Liczba cech wejściowych: {len(FEATURE_COLS)}")
print(f"[TRAIN-2026] Przykłady cech: {FEATURE_COLS[:4]} ... {FEATURE_COLS[-3:]}")

# ─────────────────────────────────────────────────────────────────────────────
# KROK 2: TEMPORAL SPLIT (80% train, 20% test)
# ─────────────────────────────────────────────────────────────────────────────
# Dzielimy po dacie (nie shufflujemy!), aby uniknąć look-ahead bias

split_idx = int(len(df) * 0.8)
train_df = df.iloc[:split_idx].copy()
test_df = df.iloc[split_idx:].copy()

X_train = train_df[FEATURE_COLS]
y_train = train_df[TARGET_COL].values
X_test = test_df[FEATURE_COLS]
y_test = test_df[TARGET_COL].values

print(f"\n[TRAIN-2026] Podział temporal:")
print(f"  Train: {len(train_df)} meczów ({train_df['game_date'].min()} do {train_df['game_date'].max()})")
print(f"  Test:  {len(test_df)} meczów ({test_df['game_date'].min()} do {test_df['game_date'].max()})")
print(f"  Gospodarz wygrał w train: {train_df[TARGET_COL].mean():.1%}")
print(f"  Gospodarz wygrał w test:  {test_df[TARGET_COL].mean():.1%}")

# ─────────────────────────────────────────────────────────────────────────────
# KROK 3: SKALOWANIE
# ─────────────────────────────────────────────────────────────────────────────

scaler = StandardScaler()
X_train_scaled = pd.DataFrame(
    scaler.fit_transform(X_train), columns=FEATURE_COLS
)
X_test_scaled = pd.DataFrame(
    scaler.transform(X_test), columns=FEATURE_COLS
)

# ─────────────────────────────────────────────────────────────────────────────
# KROK 4: KONFIGURACJA MODELI
# ─────────────────────────────────────────────────────────────────────────────

models = {
    "LogReg_C_0.01": LogisticRegression(C=0.01, max_iter=2000, random_state=42),
    "LogReg_C_0.1": LogisticRegression(C=0.1, max_iter=2000, random_state=42),
    "LogReg_C_1.0": LogisticRegression(C=1.0, max_iter=2000, random_state=42),
    "XGBoost_Sports": XGBClassifier(
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

results = {}

print("\n" + "=" * 70)
print("TRENOWANIE I EWALUACJA")
print("=" * 70)

for name, base_model in models.items():
    print(f"\n▶ {name}")

    # Kalibracja za pomocą sigmoid
    model = CalibratedClassifierCV(base_model, method="sigmoid", cv=5)
    model.fit(X_train_scaled, y_train)

    proba = model.predict_proba(X_test_scaled)[:, 1]
    pred = (proba >= 0.5).astype(int)

    brier = brier_score_loss(y_test, proba)
    auc = roc_auc_score(y_test, proba)
    acc = (pred == y_test).mean()
    lloss = log_loss(y_test, proba)

    results[name] = {
        "model": model,
        "brier": brier,
        "auc": auc,
        "acc": acc,
        "log_loss": lloss,
        "proba": proba,
    }

    print(f"  Brier Score: {brier:.4f}")
    print(f"  ROC-AUC:     {auc:.4f}")
    print(f"  Accuracy:    {acc:.2%}")
    print(f"  Log Loss:    {lloss:.4f}")

print("\n" + "=" * 70)
print("PODSUMOWANIE")
print("=" * 70)

summary_rows = []
for name, r in results.items():
    summary_rows.append({
        "Model": name,
        "Brier ↓": f"{r['brier']:.4f}",
        "AUC ↑": f"{r['auc']:.4f}",
        "Accuracy ↑": f"{r['acc']:.2%}",
        "LogLoss ↓": f"{r['log_loss']:.4f}",
    })

summary_df = pd.DataFrame(summary_rows).set_index("Model")
print(summary_df.to_string())

# Najlepszy = najniższy Brier Score
best_name = min(results, key=lambda n: results[n]["brier"])
print(f"\n✅ Najlepszy model: {best_name}")
print(f"   Brier: {results[best_name]['brier']:.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# KROK 5: TRENOWANIE NA CAŁYM ZBIORZE (DLA PLAYOFFÓW)
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n[TRAIN-2026] Trenowanie finalnego modelu ({best_name}) na całym zbiorze sezonu...")

X_final = df[FEATURE_COLS]
y_final = df[TARGET_COL].values

final_scaler = StandardScaler()
X_final_scaled = pd.DataFrame(
    final_scaler.fit_transform(X_final), columns=FEATURE_COLS
)

best_base_model = models[best_name]
final_model = CalibratedClassifierCV(best_base_model, method="sigmoid", cv=10)
final_model.fit(X_final_scaled, y_final)

# ─────────────────────────────────────────────────────────────────────────────
# KROK 6: FEATURE IMPORTANCE (TYLKO LOGISTIC REGRESSION)
# ─────────────────────────────────────────────────────────────────────────────

if "LogReg" in best_name:
    print("\n" + "=" * 70)
    print("WAGI CECH - TOP 15")
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
    except (AttributeError, IndexError):
        pass

# ─────────────────────────────────────────────────────────────────────────────
# KROK 7: ZAPIS MODELU
# ─────────────────────────────────────────────────────────────────────────────

joblib.dump(final_model, "model_2026.pkl")
joblib.dump(final_scaler, "scaler_2026.pkl")
joblib.dump(FEATURE_COLS, "feature_cols_2026.pkl")

print(f"\n✅ [TRAIN-2026] Zapisano pliki modelu:")
print(f"   model_2026.pkl       — {best_name} (skalibrowany)")
print(f"   scaler_2026.pkl      — StandardScaler")
print(f"   feature_cols_2026.pkl — {len(FEATURE_COLS)} cech")
print(f"\n💡 Model gotowy do predykcji playoffów 2025-26!")
