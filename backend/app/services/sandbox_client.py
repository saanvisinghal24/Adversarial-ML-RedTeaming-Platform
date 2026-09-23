"""M2 seam — sandbox + scoring.

M2 will implement `sandbox_manager.run_scan(job_config) -> raw_results.json` and a
scoring engine. Until then these two functions return contract-shaped fixtures.

TO INTEGRATE (M2): replace the bodies of run_scan() and score_results() with calls into
/sandbox/sandbox_manager.py and /sandbox/scoring_engine.py. Keep these signatures —
nothing else in /backend imports anything sandbox-related.
"""

from __future__ import annotations

import random
import time
from typing import Any

from app.core.logging import get_logger
from app.services import contracts

logger = get_logger(__name__)

MOCK_LATENCY_SECONDS = 1.0


def run_scan(job_config: dict[str, Any]) -> dict[str, Any]:
    """Contract #3 in, contract #4 out. Real version: docker run, read raw_results.json."""
    logger.info("mock sandbox run_scan", extra={"scan_id": job_config["scan_id"], "attacks": job_config["attacks"]})
    time.sleep(MOCK_LATENCY_SECONDS)  # stands in for container spin-up + attack runtime
    raw = _mock_raw_results(job_config)
    contracts.assert_raw_results_shape(raw)
    return raw


def score_results(raw_results: dict[str, Any]) -> dict[str, Any]:
    """Contract #4 in, contract #5 out.

    The formula below is ARCHITECTURE.md section 5 v1 verbatim, so M2's real engine
    should produce the same numbers for the same input — it just replaces this body.
    """
    components = {
        "evasion": _mean(
            [block.get("asr", 0.0) for block in raw_results.get("evasion", {}).values()]
        ),
        "black_box": _mean(
            [block.get("asr", 0.0) for block in raw_results.get("black_box", {}).values()]
        ),
        "poisoning": _mean(
            [block.get("accuracy_drop", 0.0) for block in raw_results.get("poisoning", {}).values()]
        ),
    }
    weights = {"evasion": 0.4, "black_box": 0.3, "poisoning": 0.3}
    badness = sum(weights[k] * components[k] for k in weights)
    final = round(100 - 100 * badness, 1)
    score = {
        "scan_id": raw_results["scan_id"],
        "component_scores": {k: round(v, 3) for k, v in components.items()},
        "weights": weights,
        "final_score_0_100": final,
        "grade": grade_for(final),
    }
    contracts.assert_score_shape(score)
    return score


def grade_for(final_score: float) -> str:
    if final_score >= 90:
        return "A"
    if final_score >= 75:
        return "B"
    if final_score >= 60:
        return "C"
    if final_score >= 40:
        return "D"
    return "F"


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _mock_raw_results(job_config: dict[str, Any]) -> dict[str, Any]:
    """Plausible, contract-shaped output — deterministic per scan_id so demos repeat cleanly."""
    rng = random.Random(job_config["scan_id"])
    attacks = set(job_config["attacks"])
    raw: dict[str, Any] = {"scan_id": job_config["scan_id"], "clean_accuracy": round(rng.uniform(0.93, 0.98), 2)}

    evasion = {}
    for attack in ("fgsm", "pgd"):
        if attack in attacks:
            asr = round(rng.uniform(0.2, 0.75), 2)
            evasion[attack] = {
                "asr": asr,
                "avg_confidence_drop": round(asr * rng.uniform(0.6, 0.9), 2),
                "samples": [
                    {
                        "id": i,
                        "orig_pred": 1,
                        "adv_pred": 0,
                        "conf_delta": round(rng.uniform(0.1, 0.6), 2),
                        "perturbation_norm": job_config["params"].get(attack, {}).get("epsilon", 0.05),
                    }
                    for i in range(1, 4)
                ],
            }
    if evasion:
        raw["evasion"] = evasion

    if "hopskipjump" in attacks:
        budget = job_config["params"].get("hopskipjump", {}).get("query_budget", 2000)
        raw["black_box"] = {
            "hopskipjump": {
                "asr": round(rng.uniform(0.3, 0.6), 2),
                "queries_used": int(budget * rng.uniform(0.7, 0.99)),
                "query_budget": budget,
            }
        }

    if "poisoning" in attacks:
        raw["poisoning"] = {}
        for pct in job_config["params"].get("poisoning", {}).get("contamination_pct", [1, 5, 10]):
            drop = round(rng.uniform(0.01, 0.05) * pct, 2)
            raw["poisoning"][f"{pct}pct"] = {"accuracy_drop": drop, "f1_drop": round(drop * 1.15, 2)}

    return raw
