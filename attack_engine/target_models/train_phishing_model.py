"""
train_phishing_model.py
------------------------
M4's job: train the "target model" that will later get attacked.

What this does:
1. Loads phishing_data.csv (30 website features + 1 label column "result")
2. Trains a Logistic Regression classifier: given the 30 features, predict
   phishing (1) or legitimate (0)
3. Measures accuracy and F1-score on a held-out test set (this is the
   "clean baseline" — how good the model is BEFORE any attack)
4. Saves the trained model + scaler to disk so the attack script can load
   them later

Why Logistic Regression (not RandomForest/XGBoost) for this first model:
FGSM/PGD attacks need to compute a *gradient* — basically "which direction
should I nudge this input to confuse the model the most". Logistic
Regression has a clean, well-defined gradient, and ART (our attack library)
supports it natively. Tree-based models (RandomForest, XGBoost) don't have
gradients in the same way — we'll attack those with a different technique
(HopSkipJump, a "black-box" attack that doesn't need gradients) in a later
milestone. This matches ARCHITECTURE.md's white-box vs black-box split.

Run this file with: python train_phishing_model.py
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, f1_score
import joblib
import json

# ---- 1. Load the data ----
df = pd.read_csv("phishing_data.csv")

FEATURE_COLUMNS = [c for c in df.columns if c != "result"]
X = df[FEATURE_COLUMNS].values
y_raw = df["result"].values          # values are -1 (legit) or 1 (phishing)
y = (y_raw == 1).astype(int)         # convert to 0 (legit) / 1 (phishing)

print(f"Loaded {len(df)} rows, {len(FEATURE_COLUMNS)} features.")
print(f"Phishing: {y.sum()}  Legitimate: {len(y) - y.sum()}")

# ---- 2. Split into train/test ----
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ---- 3. Scale features (helps Logistic Regression converge + attack quality) ----
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# ---- 4. Train the model ----
model = LogisticRegression(max_iter=1000)
model.fit(X_train_scaled, y_train)

# ---- 5. Evaluate: this is the "clean baseline" everyone else will compare against ----
y_pred = model.predict(X_test_scaled)
accuracy = accuracy_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)

print(f"\nClean baseline accuracy: {accuracy:.4f}")
print(f"Clean baseline F1-score: {f1:.4f}")

# ---- 6. Save everything the attack script will need ----
joblib.dump(model, "phishing_model.pkl")
joblib.dump(scaler, "phishing_scaler.pkl")

# Also save a small sample of the (scaled) test set for the attack script to use
np.save("X_test_sample.npy", X_test_scaled[:200])   # first 200 test rows
np.save("y_test_sample.npy", y_test[:200])

baseline_metrics = {
    "model_type": "sklearn_logistic_regression",
    "domain": "phishing_url",
    "n_features": len(FEATURE_COLUMNS),
    "n_train": len(X_train),
    "n_test": len(X_test),
    "clean_accuracy": round(float(accuracy), 4),
    "clean_f1": round(float(f1), 4),
}
with open("baseline_metrics.json", "w") as f:
    json.dump(baseline_metrics, f, indent=2)

print("\nSaved: phishing_model.pkl, phishing_scaler.pkl, baseline_metrics.json")
print("Saved: X_test_sample.npy, y_test_sample.npy (for the attack script)")