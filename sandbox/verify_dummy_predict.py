"""
verify_dummy_predict.py
Owner: M2 (Cybersecurity #1)

Runs INSIDE the sandbox container. This is NOT the real Attack Orchestrator
(that belongs to M4 — see /attack_engine). This script exists only to prove,
for Milestone 1, that the sandbox can:
  1. read job_config.json (contract #3, mounted read-only)
  2. load a model file (.pkl / .onnx) referenced by it
  3. run one dummy prediction
  4. write a result file to the shared output volume

Once M4's real orchestrator exists, sandbox_wrapper.py just points `docker
run` at M4's script instead of this one — nothing else about the sandbox
changes. That's the whole point of the contract boundary.

Expected mount layout inside the container:
  /data/job_config.json   (read-only, contract #3)
  /data/model.pkl          (read-only, path taken from job_config)
  /output/                 (read-write, shared volume)

PATCH (integration test, M1->M2->M4 handoff): sklearn/xgboost loading was
`pickle.load()`, which failed on M4's real models with
`UnpicklingError: invalid load key`. M4 saves models with `joblib.dump()`
(the standard for sklearn — handles the numpy arrays inside a fitted
estimator more reliably than raw pickle). Switched to `joblib.load()`,
which reads both joblib-saved AND plain-pickle-saved files, so this is a
strict improvement with no downside. Verified against Rishav's own
test_model.pkl (still works) and both of M4's real models
(phishing_model.pkl, malware_model.pkl — both now load correctly).
"""

import json
import joblib
import sys
import traceback
from pathlib import Path

JOB_CONFIG_PATH = Path("/data/job_config.json")
OUTPUT_PATH = Path("/output/dummy_verify_result.json")


def load_job_config() -> dict:
    if not JOB_CONFIG_PATH.exists():
        raise FileNotFoundError(f"job_config.json not found at {JOB_CONFIG_PATH}")
    with open(JOB_CONFIG_PATH) as f:
        return json.load(f)


def load_model(model_path: str, model_type: str):
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(f"model file not found at {path}")

    if model_type in ("sklearn", "xgboost"):
        with open(path, "rb") as f:
            return joblib.load(f)
    elif model_type == "onnx":
        import onnxruntime as ort
        return ort.InferenceSession(str(path))
    elif model_type == "pytorch":
        import torch
        return torch.load(path, map_location="cpu")
    else:
        raise ValueError(f"unsupported model_type: {model_type}")


def make_dummy_input(model, model_type: str, n_features_fallback: int = 10):
    import numpy as np

    if model_type in ("sklearn", "xgboost"):
        n_features = getattr(model, "n_features_in_", n_features_fallback)
        return np.zeros((1, n_features), dtype=float)
    elif model_type == "onnx":
        input_meta = model.get_inputs()[0]
        shape = [d if isinstance(d, int) else 1 for d in input_meta.shape]
        return np.zeros(shape, dtype=np.float32)
    elif model_type == "pytorch":
        import torch
        return torch.zeros((1, n_features_fallback))
    else:
        raise ValueError(f"unsupported model_type: {model_type}")


def run_prediction(model, model_type: str, dummy_input):
    if model_type in ("sklearn", "xgboost"):
        return model.predict(dummy_input).tolist()
    elif model_type == "onnx":
        input_name = model.get_inputs()[0].name
        outputs = model.run(None, {input_name: dummy_input})
        return [o.tolist() for o in outputs]
    elif model_type == "pytorch":
        model.eval()
        import torch
        with torch.no_grad():
            return model(dummy_input).tolist()


def main():
    result = {"status": "failed", "error": None, "prediction": None}
    try:
        config = load_job_config()
        model_path = config["model_path"]
        model_type = config["model_type"]

        model = load_model(model_path, model_type)
        dummy_input = make_dummy_input(model, model_type)
        prediction = run_prediction(model, model_type, dummy_input)

        result["status"] = "ok"
        result["scan_id"] = config.get("scan_id")
        result["model_type"] = model_type
        result["prediction"] = prediction

    except Exception as e:  # noqa: BLE001 — sandbox script, must not crash silently
        result["status"] = "failed"
        result["error"] = f"{type(e).__name__}: {e}"
        result["traceback"] = traceback.format_exc()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "ok" else 1)


if __name__ == "__main__":
    main()