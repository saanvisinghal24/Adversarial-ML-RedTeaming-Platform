# Backend (M1)

FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL 15. Owns the API, the DB schema, auth, and the
orchestration of one scan. Owns none of the attack/sandbox/ATLAS logic — those are reached through
the seams in `app/services/`.

## Setup

```bash
docker compose up -d db          # from the repo root
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then edit JWT_SECRET
alembic upgrade head
uvicorn app.main:app --reload
```

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Machine-readable contract for the rest of the team: http://localhost:8000/openapi.json

No Docker? Set `DATABASE_URL=sqlite:///./dev.db` in `.env` — migrations and every route work, you
just lose JSONB. Postgres is what we deploy on, so don't develop on SQLite for long.

## Tests

```bash
pytest -q        # 14 tests, no Postgres needed (they run on a temp SQLite file)
```

They cover the auth flow, model upload validation, a full scan through the mocked pipeline, the
failure path, report export, and the contract shapes. That last group is the one to watch during
merges.

Want data to click around in? `python -m scripts.seed_demo` creates
`demo@redteam.local` / `demo-password-123` with a finished four-attack scan.

## Layout

```
app/
  main.py                 FastAPI app, CORS, error handler
  core/
    config.py             pydantic-settings, all env vars
    security.py           bcrypt hashing, JWT issue/verify
    logging.py            structured JSON logging
  db/
    base.py               SQLAlchemy models = ARCHITECTURE.md section 7
    session.py            engine + get_db dependency
  schemas/                Pydantic request/response models
  api/
    deps.py               get_current_user, DB session dependency
    routes/               health, auth, models, scans
  services/
    contracts.py          builds/validates contracts #3-#6
    sandbox_client.py     M2 SEAM  - run_scan(), score_results()   [mocked]
    atlas_client.py       M3 SEAM  - get_findings()                [mocked]
    pipeline.py           the background task that chains them
    report.py             PDF (ReportLab) + HTML compliance report
scripts/seed_demo.py      demo account, model and finished scan
  fixtures/               frozen contract examples
alembic/                  migrations (0001 = full initial schema)
tests/
```

## Environment variables

| Var | Default | Notes |
|---|---|---|
| `DATABASE_URL` | local Postgres | one var, so swapping to Supabase/Railway is a one-line change |
| `JWT_SECRET` | dev placeholder | must be set for anything non-local |
| `JWT_ALGORITHM` | HS256 | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | `POST /auth/refresh` takes the refresh token |
| `STORAGE_DIR` | `./storage` | uploaded model artefacts, per-user subfolders |
| `MAX_MODEL_SIZE_MB` | 200 | enforced while streaming, not after |
| `SCAN_TIMEOUT_SECONDS` | 600 | backstop if the sandbox never returns |
| `CORS_ORIGINS` | Vite dev server | comma-separated; add the deployed frontend origin |
| `LOG_LEVEL` / `ENVIRONMENT` | INFO / dev | |

## API

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/health` | no | also reports DB connectivity |
| POST | `/auth/register` | no | 201 + token pair |
| POST | `/auth/login` | no | 401 on bad creds, same message either way |
| POST | `/auth/refresh` | no | refresh token in body |
| GET | `/auth/me` | yes | |
| POST | `/models` | yes | multipart; validates suffix, size, sha256 |
| GET | `/models` | yes | caller's models |
| POST | `/scans` | yes | 202, runs the pipeline as a BackgroundTask |
| GET | `/scans/{id}` | yes | status; score + findings + raw_results once done |
| GET | `/scans/{id}/score` | yes | contract #5 only; 409 while the scan is unfinished |
| GET | `/scans/{id}/findings` | yes | contract #6 rows, ranked most severe first |
| GET | `/scans/{id}/report` | token | `?format=pdf\|html&token=<jwt>` — see below |
| GET | `/models/{id}/scans` | yes | score history for the trend view |

The report route takes its JWT as a query parameter because a browser downloading through a link
click can't attach an Authorization header. Same token, same expiry.

Report layout and export are final; the *copy* inside it is M1 placeholder text until M3 hands over
their template — that's a string swap in `app/services/report.py`, nothing structural.
