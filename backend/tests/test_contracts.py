"""Contract-shape tests — these are the ones that break loudly when someone's merge drifts."""

import json
from pathlib import Path

from app.services import atlas_client, sandbox_client
from app.services.contracts import (
    assert_findings_shape,
    assert_raw_results_shape,
    assert_score_shape,
    build_job_config,
)

FIXTURES = Path(__file__).resolve().parents[1] / "app" / "fixtures"
SCAN_ID = "3f1a1e26-6d2d-4b2a-9b4e-6a2f9f1c0b11"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_fixtures_match_their_contracts() -> None:
    assert_raw_results_shape(_fixture("raw_results.example.json"))
    assert_score_shape(_fixture("score.example.json"))
    assert_findings_shape(_fixture("findings.example.json"))


def test_mock_pipeline_produces_contract_shapes() -> None:
    job = build_job_config(
        scan_id=SCAN_ID,
        model_path="/data/model.pkl",
        model_type="sklearn",
        threat_model="white_box",
        attacks=["fgsm", "pgd", "hopskipjump", "poisoning"],
        params={},
    )
    assert job["params"]["pgd"]["iterations"] == 40  # documented default filled in

    raw = sandbox_client.run_scan(job)
    score = sandbox_client.score_results(raw)
    findings = atlas_client.get_findings(raw, score)

    assert_raw_results_shape(raw)
    assert_score_shape(score)
    assert_findings_shape(findings)
    assert set(raw["evasion"]) == {"fgsm", "pgd"}
    assert raw["black_box"]["hopskipjump"]["queries_used"] <= raw["black_box"]["hopskipjump"]["query_budget"]


def test_scoring_formula_matches_architecture_section_5() -> None:
    raw = {
        "scan_id": SCAN_ID,
        "clean_accuracy": 0.97,
        "evasion": {"fgsm": {"asr": 0.5}, "pgd": {"asr": 0.5}},
        "black_box": {"hopskipjump": {"asr": 0.5}},
        "poisoning": {"10pct": {"accuracy_drop": 0.5}},
    }
    score = sandbox_client.score_results(raw)
    # 100 - 100 * (0.4*0.5 + 0.3*0.5 + 0.3*0.5) = 50.0 -> grade D
    assert score["final_score_0_100"] == 50.0
    assert score["grade"] == "D"


def test_severity_thresholds() -> None:
    assert atlas_client.severity_for(0.61) == "high"
    assert atlas_client.severity_for(0.35) == "medium"
    assert atlas_client.severity_for(0.1) == "low"
