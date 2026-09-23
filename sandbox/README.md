# /sandbox — M2 (Cybersecurity #1)

Milestone 1 deliverables. Per ARCHITECTURE.md, M2 owns container isolation
and the scoring engine (scoring engine comes in Milestone 3). Nobody else
should need to edit files in this folder — M4's orchestrator is mounted in
at runtime, not baked into the image, so M2's and M4's code never collide.

## Files

| File | Purpose |
|---|---|
| `Dockerfile` | Base sandbox image: python3.10 + ART + sklearn + xgboost + onnxruntime + torch |
| `requirements.txt` | Pinned deps for the image |
| `sandbox_wrapper.py` | Host-side script — plain `docker run` wrapper with resource-limit CLI flags |
| `verify_dummy_predict.py` | Container-side script — loads a model, runs one dummy prediction, writes output. Stands in for M4's real orchestrator until it exists |
| `sample_job_config.json` | Fixture matching contract #3, for local testing |
| `make_test_model.py` | Throwaway helper to generate a test `.pkl` so you're not blocked on M4 |

## 1. Build the image

```bash
docker build -t adv-ml-sandbox:latest .
```

## 2. Generate a test model + config

```bash
python make_test_model.py test_model.pkl
```

`sample_job_config.json` already points at `/data/model.pkl` (the path
the container sees, not the host path — the host path is supplied
separately via `--model` on the CLI).

## 3. Run the sandbox wrapper

```bash
python sandbox_wrapper.py \
  --image adv-ml-sandbox:latest \
  --model ./test_model.pkl \
  --job-config ./sample_job_config.json \
  --output-dir ./scan_output \
  --script ./verify_dummy_predict.py \
  --cpus 1.0 \
  --memory 2g \
  --timeout 60 \
  --network none
```

Expected result: `scan_output/dummy_verify_result.json` contains
`"status": "ok"` and a `"prediction"` field. That's the Milestone 1
"Verify" bullet satisfied — a container loaded a `.pkl` and ran one
dummy prediction, output landed in the shared volume.

## Resource limits — CLI flags (all enforced at `docker run` time)

| Flag | Default | What it does |
|---|---|---|
| `--cpus` | `1.0` | CPU core cap, passed straight to `docker run --cpus` |
| `--memory` | `2g` | Memory cap (`--memory` + matching `--memory-swap` so it can't spill into swap) |
| `--network` | `none` | `none` = fully isolated (default, matches contract #3's `--network=none`). `bridge` only if a future scan explicitly needs egress — none do yet |
| `--timeout` | `60` (seconds) | **Wrapper-enforced**, not a native Docker flag. `subprocess.run(..., timeout=...)`; on expiry the wrapper force-kills and removes the container |

Additional hardening baked into every run, not exposed as flags (no
reason a caller should be able to turn these off):
- `--pids-limit 256` — fork-bomb guard
- `--cap-drop ALL` + `--security-opt no-new-privileges`
- `--read-only` root filesystem, with `--tmpfs /tmp` for scratch space
- non-root user inside the image (`sandboxuser`, uid 1000)
- `--rm` — no stopped containers left behind after a run

## What's still stubbed (per ARCHITECTURE.md's milestone map)

- This is a plain `subprocess` wrapper, not the Docker SDK. Milestone 2
  replaces it with `sandbox_manager.py`'s `run_scan(job_config) ->
  raw_results.json` using `docker-py`.
- `verify_dummy_predict.py` is a placeholder for M4's real Attack
  Orchestrator — it proves the pipe works, it doesn't run any attacks.
- Only `.pkl` (sklearn/xgboost) and `.onnx` paths are exercised so far;
  `.pt` (pytorch) loading is implemented but untested until M4 ships a
  real pytorch model.
- No health-check-then-fail-fast step yet (that's a Milestone 2 item).

## Note on this environment

This code was written and syntax-checked, but not built/run against a
live Docker daemon in this environment (network access is disabled
here). Build and run it locally with Docker installed before treating
the "Verify" step as complete — that's the actual Milestone 1 checkpoint.
