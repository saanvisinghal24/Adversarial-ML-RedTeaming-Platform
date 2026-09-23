"""
M3 module — Milestone 1.
Pure lookup logic, no ML. Reads atlas_catalogue.json + a raw ASR value,
returns one findings.json entry per contract #6 in ARCHITECTURE.md.

Severity thresholds are a simple placeholder for M1 (finalized properly
in Milestone 2 per the milestone plan — see ARCHITECTURE.md contract #6).
"""
import json
from pathlib import Path

CATALOGUE_PATH = Path(__file__).parent / "atlas_catalogue.json"


def _load_catalogue() -> dict:
    with open(CATALOGUE_PATH) as f:
        return json.load(f)


def _severity(asr: float) -> str:
    # Placeholder thresholds — replace in Milestone 2 (documented deviation
    # must be logged in PROJECT_LOG.md if this changes).
    if asr >= 0.6:
        return "high"
    if asr >= 0.3:
        return "medium"
    return "low"


def get_finding(attack_name: str, asr: float, scan_id: str) -> dict:
    """
    attack_name: "fgsm" | "pgd"  (only these two exist in the M1 catalogue)
    asr: attack success rate for that attack, taken from raw_results.json
    scan_id: the scan this finding belongs to
    Returns one entry matching the `findings` array shape in contract #6.
    """
    catalogue = _load_catalogue()
    if attack_name not in catalogue:
        raise ValueError(f"No ATLAS entry for attack '{attack_name}' yet")

    entry = catalogue[attack_name]
    return {
        "attack": attack_name,
        "atlas_tactic": entry["atlas_tactic"],
        "atlas_technique": entry["atlas_technique"],
        "severity": _severity(asr),
        "evidence": {"asr": asr},
        "mitigation": entry["mitigation"],
        "owasp_ml_top10": entry["owasp_ml_top10"],
        "nist_ai_rmf": entry["nist_ai_rmf"],
    }


def build_findings_json(scan_id: str, raw_results: dict) -> dict:
    """
    Full contract #6 object. raw_results is contract #4's dict
    (i.e. the parsed raw_results.json M4 produces).
    """
    findings = []
    for attack_name, data in raw_results.get("evasion", {}).items():
        if attack_name in _load_catalogue():
            findings.append(get_finding(attack_name, data["asr"], scan_id))
    return {"scan_id": scan_id, "findings": findings}


if __name__ == "__main__":
    # Manual test for the Milestone 1 integration checkpoint:
    # feed it a fake raw_results.json with an fgsm block and check the output.
    sample_raw = {
        "scan_id": "test-scan-1",
        "evasion": {"fgsm": {"asr": 0.31, "avg_confidence_drop": 0.22}},
    }
    print(json.dumps(build_findings_json("test-scan-1", sample_raw), indent=2))
