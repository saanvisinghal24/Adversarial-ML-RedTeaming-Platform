"""Shared helpers for building/validating the cross-team JSON contracts.

These live on M1's side only as *shape* helpers — no attack, sandbox or ATLAS
logic belongs here. If a shape changes, ARCHITECTURE.md changes in the same commit.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID


def build_job_config(
    *,
    scan_id: UUID,
    model_path: str,
    model_type: str,
    threat_model: str,
    attacks: list[str],
    params: dict[str, dict[str, Any]],
    dataset_path: str | None = None,
) -> dict[str, Any]:
    """Contract #3 (ARCHITECTURE.md section 3). This is what M2's sandbox receives."""
    job: dict[str, Any] = {
        "scan_id": str(scan_id),
        "model_path": model_path,
        "model_type": model_type,
        "threat_model": threat_model,
        "attacks": attacks,
        "params": _with_default_params(attacks, params),
    }
    if dataset_path:
        job["dataset_path"] = dataset_path
    return job


DEFAULT_PARAMS: dict[str, dict[str, Any]] = {
    "fgsm": {"epsilon": 0.05},
    "pgd": {"epsilon": 0.05, "step_size": 0.01, "iterations": 40},
    "hopskipjump": {"query_budget": 2000},
    "poisoning": {"contamination_pct": [1, 5, 10], "method": "label_flip"},
}


def _with_default_params(attacks: list[str], params: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Caller-supplied params win; anything omitted falls back to the documented defaults."""
    merged: dict[str, dict[str, Any]] = {}
    for attack in attacks:
        merged[attack] = {**DEFAULT_PARAMS.get(attack, {}), **params.get(attack, {})}
    return merged


REQUIRED_RAW_RESULT_KEYS = ("scan_id", "clean_accuracy")
REQUIRED_SCORE_KEYS = ("scan_id", "component_scores", "weights", "final_score_0_100", "grade")


class ContractViolation(ValueError):
    """Raised when a teammate's (or the mock's) output doesn't match ARCHITECTURE.md."""


def assert_raw_results_shape(payload: dict[str, Any]) -> None:
    _require(payload, REQUIRED_RAW_RESULT_KEYS, "raw_results.json")


def assert_score_shape(payload: dict[str, Any]) -> None:
    _require(payload, REQUIRED_SCORE_KEYS, "score.json")
    if payload["grade"] not in {"A", "B", "C", "D", "F"}:
        raise ContractViolation(f"score.json: unknown grade {payload['grade']!r}")


def assert_findings_shape(payload: dict[str, Any]) -> None:
    _require(payload, ("scan_id", "findings"), "findings.json")
    if not isinstance(payload["findings"], list):
        raise ContractViolation("findings.json: 'findings' must be a list")


def _require(payload: dict[str, Any], keys: tuple[str, ...], label: str) -> None:
    missing = [k for k in keys if k not in payload]
    if missing:
        raise ContractViolation(f"{label}: missing key(s) {', '.join(missing)}")
