# ARCHITECTURE — Adversarial ML Red-Teaming Platform

This is the single source of truth for how the system fits together. Every member codes against
the contracts in this file, not against each other's code. If you change a contract, edit this file
in the same commit and add a line to PROJECT_LOG.md.

## 0. Roles → Modules (no overlap)

| Owner | Role type | Owns |
|---|---|---|
| **M1** | Software + light AI/ML | FastAPI backend, PostgreSQL/SQLAlchemy schema, JWT auth, React frontend, deployment |
| **M2** | Cybersecurity #1 | Docker sandbox provisioning/isolation, Robustness Scoring Engine (A–F formula), score history |
| **M3** | Cybersecurity #2 | MITRE ATLAS technique catalogue, Mitigation Recommendation Module, OWASP/NIST compliance mapping, report content |
| **M4** | Heavy AI/ML | Attack Orchestrator: FGSM/PGD (white-box), HopSkipJump (black-box), poisoning simulation, sacrificial target models |

Nobody touches another owner's files. All communication is through the JSON contracts below and
the DB schema. This is what lets 4 people build in parallel and merge at each milestone.

## 1. High-level data flow (one scan)

```
React UI (M1)
   │  POST /scans  {model_id, attack_config}
   ▼
FastAPI (M1) ── writes Scan row (status=queued) ── PostgreSQL (M1 schema)
   │  background task
   ▼
Sandbox Manager (M2) ── docker run --cpu --mem --timeout --no-net  container
   │  mounts model file + attack config (JSON, contract #3)
   ▼
Attack Orchestrator (M4, runs INSIDE the container)
   │  loads model → ART estimator → runs FGSM/PGD/HopSkipJump/poisoning
   │  writes raw_results.json (contract #4) to a shared volume
   ▼
Sandbox Manager (M2) reads raw_results.json → tears down container
   │
   ▼
Robustness Scoring Engine (M2) ── raw_results.json → score.json (contract #5)
   │
   ▼
ATLAS + Mitigation Module (M3) ── score.json → findings.json (contract #6)
   │
   ▼
FastAPI (M1) persists Scan/Score/Finding rows ── PostgreSQL
   │
   ▼
React UI (M1) polls GET /scans/{id} → renders scorecard, ASR charts, mitigation list, PDF export
```

Every arrow above is a **file or DB contract**, defined once below. As long as each member's code
reads/writes the correct contract shape, the pieces snap together without needing to read each
other's internals.

## 2. Tech stack (fixed — do not swap mid-project)

- Backend: Python 3.10+, FastAPI, SQLAlchemy 2.0, Alembic, PyJWT, Uvicorn
- Attack engine: PyTorch, ART (adversarial-robustness-toolbox), scikit-learn, XGBoost
- Sandbox: Docker Engine 24+, Docker SDK for Python
- DB: PostgreSQL 15 (Supabase/Railway)
- Frontend: React 18 + Vite, Tailwind, Recharts, React Query, Zustand
- Repo layout:
```
/backend        (M1: FastAPI app, models, routers, auth)
/sandbox        (M2: docker image, sandbox_manager.py, resource limit configs)
/attack_engine  (M4: orchestrator.py, attacks/, target_models/, datasets/)
/atlas          (M3: atlas_catalogue.json, mitigation_engine.py, compliance_map.json)
/frontend       (M1: React app)
/docs           (ARCHITECTURE.md, PROJECT_LOG.md, paper drafts)
```

## 3. Contract: Sandbox input (M2 provides container, M4 code runs inside it)

File `job_config.json`, mounted read-only into the container:
```json
{
  "scan_id": "uuid",
  "model_path": "/data/model.pkl",     // .pkl | .onnx | .pt
  "model_type": "sklearn|xgboost|pytorch|onnx",
  "dataset_path": "/data/sample.csv",   // optional, labelled sample
  "threat_model": "white_box|black_box",
  "attacks": ["fgsm", "pgd", "hopskipjump", "poisoning"],
  "params": {
    "fgsm": {"epsilon": 0.05},
    "pgd": {"epsilon": 0.05, "step_size": 0.01, "iterations": 40},
    "hopskipjump": {"query_budget": 2000},
    "poisoning": {"contamination_pct": [1, 5, 10], "method": "label_flip"}
  }
}
```
Resource limits (M2's responsibility, enforced at `docker run` time — M4 never sets these):
`--cpus`, `--memory`, `--network=none` (or egress-restricted), `--timeout` (wrapper-enforced kill).

## 4. Contract: Attack Orchestrator output (M4 writes, M2 reads)

File `raw_results.json`, written by M4's code to the mounted output volume:
```json
{
  "scan_id": "uuid",
  "clean_accuracy": 0.97,
  "evasion": {
    "fgsm": {"asr": 0.31, "avg_confidence_drop": 0.22, "samples": [ {"id":1,"orig_pred":1,"adv_pred":0,"conf_delta":0.4,"perturbation_norm":0.05} ] },
    "pgd":  {"asr": 0.68, "avg_confidence_drop": 0.51, "samples": [ ... ] }
  },
  "black_box": {
    "hopskipjump": {"asr": 0.44, "queries_used": 1840, "query_budget": 2000}
  },
  "poisoning": {
    "1pct":  {"accuracy_drop": 0.02, "f1_drop": 0.03},
    "5pct":  {"accuracy_drop": 0.09, "f1_drop": 0.11},
    "10pct": {"accuracy_drop": 0.21, "f1_drop": 0.24}
  }
}
```
This is the ONLY thing M2's scoring engine and M3's ATLAS mapper are allowed to depend on from M4.

## 5. Contract: Robustness Score (M2 produces, from raw_results.json)

`score.json`:
```json
{
  "scan_id": "uuid",
  "component_scores": {"evasion": 0.42, "black_box": 0.56, "poisoning": 0.31},
  "weights": {"evasion": 0.4, "black_box": 0.3, "poisoning": 0.3},
  "final_score_0_100": 63.4,
  "grade": "C"
}
```
Formula (v1, tune weights later — this is the whole engine, keep it this simple until Milestone 3):
`final = 100 - (100 * Σ weight_i * component_i)` where each `component_i` is a 0–1 "badness" score
(ASR or accuracy-drop, already 0–1). Grade thresholds: A ≥90, B ≥75, C ≥60, D ≥40, F <40.

## 6. Contract: ATLAS + Mitigation (M3 produces, from raw_results.json + score.json)

`findings.json`:
```json
{
  "scan_id": "uuid",
  "findings": [
    {
      "attack": "pgd",
      "atlas_tactic": "AML.TA0006",
      "atlas_technique": "AML.T0043",
      "severity": "high",
      "evidence": {"asr": 0.68},
      "mitigation": "Apply adversarial training with PGD-generated examples; add input-norm bounds checking.",
      "owasp_ml_top10": "ML01: Input Manipulation Attack",
      "nist_ai_rmf": "MEASURE 2.7"
    }
  ]
}
```
M3 owns `atlas/atlas_catalogue.json` — a static lookup table {attack_name → tactic/technique/mitigation/owasp/nist}. This is pure data + a small lookup function; no ML needed, ideal for a cybersecurity-focused member.

## 7. Database schema (M1 owns, others only read via API)

```
users(id, email, password_hash, created_at)
models(id, user_id, name, file_path, model_type, version, created_at)
scans(id, model_id, status[queued|running|done|failed], threat_model, attack_config JSON, created_at, completed_at)
raw_results(scan_id, json_blob)     -- contract #4 verbatim
scores(scan_id, component_scores JSON, final_score, grade, created_at)   -- contract #5
findings(id, scan_id, attack, atlas_tactic, atlas_technique, severity, mitigation, owasp_ref, nist_ref)  -- contract #6 rows
```

## 8. Key API endpoints (M1)

- `POST /auth/login` / `POST /auth/register`
- `POST /models` (multipart upload, validates .pkl/.onnx/.pt + size)
- `POST /scans` (model_id, attack_config) → 202, triggers background task
- `GET /scans/{id}` → status, and once done: score + findings
- `GET /scans/{id}/report` → PDF/HTML (M3 supplies the report template content; M1 wires PDF export)
- `GET /models/{id}/scans` → score history for trend view

## 9. Milestone → contract maturity map

| Milestone | What's real vs stubbed |
|---|---|
| M1 | Contracts #3–#6 exist as fixed JSON fixtures. Only FGSM implemented. Sandbox = plain subprocess, not yet Docker-isolated. |
| M2 | Sandbox = real Docker SDK container. PGD added. Auth real. |
| M3 | HopSkipJump added. Scoring engine v1 real (contract #5 live). |
| M4 | Poisoning added. Frontend hits real API end-to-end. |
| M5 | Deployed to cloud. PDF report real. Benchmarks run for paper. |
| M6 | Tests, hardening, paper, demo. |

See `TEAM_ROLES_AND_MILESTONES.docx` for the day-by-day task breakdown per person, and
`PROJECT_LOG.md` for what has actually been done so far (update it every milestone).
