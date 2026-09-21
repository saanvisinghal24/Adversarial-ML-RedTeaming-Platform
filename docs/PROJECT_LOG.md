# PROJECT LOG — read this first

> **Instructions for whoever (human or AI) picks this project up next:**
> 1. Read `ARCHITECTURE.md` for the system design and contracts.
> 2. Read the "CURRENT STATUS" block below — it tells you exactly which milestone is active and
>    what's done vs pending.
> 3. When a milestone is completed by all 4 members, append a new dated entry under
>    "MILESTONE HISTORY" (copy the template) BEFORE starting the next milestone's work.
> 4. If any contract in ARCHITECTURE.md changes, edit that file directly and note the change
>    in this log's "DECISIONS / DEVIATIONS" section — don't let the two files drift apart.
> 5. Keep entries short and factual (what shipped, what broke, what's still fake/stubbed).

---

## CURRENT STATUS
- **Active milestone:** M1 (Days 1–5) — Skeleton & Contracts
- **M4 (Heavy AI/ML) is DONE with M1.** M1 (Software), M2 (Cyber-1), M3 (Cyber-2) still pending.
- Last updated: (fill in today's date)

### M4's M1 deliverables (complete, tested, working)
- `train_phishing_model.py` — trains Logistic Regression on UCI phishing dataset (11,055 rows, 30 features). Clean accuracy 92.85%, F1 93.67%. Saves `phishing_model.pkl` + `phishing_scaler.pkl`.
- `fgsm_attack.py` — runs FGSM (via ART's SklearnClassifier) against the phishing model. ASR = 45.65%, avg confidence drop = 0.137. Writes `raw_results.json` in the exact contract #4 shape from ARCHITECTURE.md (evasion.fgsm block only, as planned for M1).
- `train_malware_model.py` — trains Logistic Regression on a 10,000-row EMBER-2018-derived sample (5,000 malware + 5,000 benign, 26 hand-picked scalar features: file size/structure, header fields, string statistics). Clean accuracy 85.60%, F1 85.05%. Saves `malware_model.pkl` + `malware_scaler.pkl`.
- `fgsm_attack_malware.py` — same FGSM attack against the malware model. ASR = 87.01% (this model is far more fragile than the phishing one — good finding for the paper's Results section). Writes `raw_results_malware.json`.

**Deviation from the original plan (see DECISIONS below):** used Logistic Regression instead of RandomForest/XGBoost for both target models, specifically so FGSM/PGD (gradient-based attacks) work natively via ART. Tree-based models will be added later as the target for black-box (HopSkipJump) attacks in M3, which don't need gradients.

**Data note:** malware data is a reduced, hand-extracted feature set from the real EMBER-2018 dataset (not the full 2381-dim vectorized EMBER features) — 26 scalar fields pulled directly from EMBER's raw JSON (`general`, `header`, `strings`, `section` blocks). This was necessary because full EMBER vectorization requires the official `ember` Python package (heavy LIEF dependency) which wasn't worth the setup cost for a 1-month capstone. Document this simplification in the paper's Methodology section.

**Still needed from M4 before M1 is fully "done" for the whole team:** nothing — M4's slice of M1 is complete. M4 can start looking ahead at PGD (M2's milestone) once M1's Aryan/Rishav/Saanvi pieces land.

---

## DECISIONS / DEVIATIONS
_(Log anything that changes from ARCHITECTURE.md's default plan — e.g. "switched Celery for
FastAPI BackgroundTasks", "using SQLite locally instead of Postgres until M2", etc. One line each.)_

- M4: target models for FGSM/PGD are **Logistic Regression**, not RandomForest/XGBoost — needed for native ART gradient support. RandomForest/XGBoost will be introduced when HopSkipJump (black-box, gradient-free) is built in M3.
- M4: malware target model uses a **26-feature hand-extracted subset of EMBER-2018** (general/header/strings/section scalar fields), not the full 2381-dim official EMBER vectorization — avoids the heavy `ember`+LIEF install for a 1-month timeline. Real, balanced EMBER samples (5,000 malware + 5,000 benign) pulled via Google Colab, not synthetic data.

---

## MILESTONE HISTORY
_(Copy this template for each completed milestone.)_

### Template
```
## M<N> — <name> — completed <date>
Owner status:
- M1 (Software): <what shipped> | <what's stubbed/fake> | <blockers>
- M2 (Cyber-1):  <...>
- M3 (Cyber-2):  <...>
- M4 (AI/ML):    <...>

Integration test result: <pass/fail + what was tested end-to-end>
Files/paths touched: <list>
Known issues carried into next milestone: <list>
```

---

## RESEARCH PAPER TRACKER
_(Fill in as milestones complete — this becomes the paper's backbone.)_

| Paper section | Status | Source milestone | Owner |
|---|---|---|---|
| Abstract | pending | M6 | M3 |
| Related Work / Literature Comparison | done (see Literature_Comparison_Adversarial_ML_Platform_final.xlsx) | pre-project | M3 |
| Research Gap statement | done (see xlsx "Key Gaps Summary" sheet) | pre-project | M3 |
| Methodology (sandbox + pipeline) | pending | M2, M5 | M2 |
| Attack Engine methodology | pending | M1–M4 | M4 |
| Scoring formula justification | pending | M3 | M2 |
| Compliance mapping (OWASP/NIST/ATLAS) | pending | M3 | M3 |
| Results / benchmarks | pending | M5 | M4 |
| Conclusion & Future Scope | pending | M6 | all |
