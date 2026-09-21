"""
fgsm_attack.py
--------------
M4's job: attack the trained phishing model with FGSM (Fast Gradient Sign
Method) and produce raw_results.json — the exact contract file that M2
(scoring engine) and M3 (ATLAS mapping) will read in later milestones.

What FGSM actually does, in plain terms:
  For each website in the test set, FGSM looks at the model's gradient
  (which direction of change would confuse it most) and nudges every
  feature a tiny bit (controlled by "epsilon") in that direction. If the
  model's prediction flips after this tiny nudge, the attack "succeeded"
  on that sample.

What we measure:
  - Attack Success Rate (ASR): of the samples the model originally got
    RIGHT, what fraction did FGSM manage to flip to WRONG?
  - Average confidence drop: how much less confident the model became,
    on average, even on samples it didn't fully flip.

Run this file with: python fgsm_attack.py
(must be run AFTER train_phishing_model.py, in the same folder)
"""

import numpy as np
import joblib
import json
from art.estimators.classification import SklearnClassifier
from art.attacks.evasion import FastGradientMethod

# ---- 1. Load the trained model + test data ----
model = joblib.load("phishing_model.pkl")
X_test = np.load("X_test_sample.npy")
y_test = np.load("y_test_sample.npy")

print(f"Loaded model + {len(X_test)} test samples.")

# ---- 2. Wrap the sklearn model so ART can attack it ----
# clip_values: since we scaled features earlier, values roughly sit in this range.
# ART needs to know the valid input range so it doesn't create nonsense inputs.
clip_min, clip_max = X_test.min() - 1, X_test.max() + 1
classifier = SklearnClassifier(model=model, clip_values=(clip_min, clip_max))

# ---- 3. Record predictions BEFORE the attack ----
preds_before = classifier.predict(X_test)
labels_before = np.argmax(preds_before, axis=1)
confidence_before = np.max(preds_before, axis=1)

# ---- 4. Run FGSM ----
EPSILON = 0.3  # how big a nudge to make (in scaled-feature units)
attack = FastGradientMethod(estimator=classifier, eps=EPSILON)
X_adv = attack.generate(x=X_test)

# ---- 5. Record predictions AFTER the attack ----
preds_after = classifier.predict(X_adv)
labels_after = np.argmax(preds_after, axis=1)
confidence_after = np.max(preds_after, axis=1)

# ---- 6. Compute metrics ----
# Only count samples the model originally classified CORRECTLY —
# that's the standard, honest way to measure an evasion attack.
correctly_classified = labels_before == y_test
n_correct = correctly_classified.sum()

flipped = (labels_after != labels_before) & correctly_classified
asr = flipped.sum() / n_correct if n_correct > 0 else 0.0

avg_confidence_drop = float(
    np.mean(confidence_before[correctly_classified] - confidence_after[correctly_classified])
)

print(f"\nSamples originally correct: {n_correct} / {len(X_test)}")
print(f"FGSM Attack Success Rate (ASR): {asr:.4f}")
print(f"Average confidence drop: {avg_confidence_drop:.4f}")

# ---- 7. Build per-sample logs (first 20, for readability) ----
samples_log = []
for i in range(min(20, len(X_test))):
    samples_log.append({
        "id": i,
        "orig_pred": int(labels_before[i]),
        "adv_pred": int(labels_after[i]),
        "conf_delta": round(float(confidence_before[i] - confidence_after[i]), 4),
        "perturbation_norm": round(float(np.linalg.norm(X_adv[i] - X_test[i])), 4),
    })

# ---- 8. Write raw_results.json — the exact contract from ARCHITECTURE.md ----
raw_results = {
    "scan_id": "local-test-m1",
    "clean_accuracy": None,  # filled in from baseline_metrics.json by the caller in later milestones
    "evasion": {
        "fgsm": {
            "asr": round(float(asr), 4),
            "avg_confidence_drop": round(avg_confidence_drop, 4),
            "epsilon": EPSILON,
            "samples": samples_log,
        }
    },
}

with open("raw_results.json", "w") as f:
    json.dump(raw_results, f, indent=2)

print("\nSaved raw_results.json — this is what M2's scoring engine will read.")