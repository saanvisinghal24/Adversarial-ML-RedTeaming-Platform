"""M3 seam — ATLAS technique mapping + mitigation text.

INTEGRATED (M3, Milestone 1): now calls the real /atlas/mitigation_engine.py,
which reads /atlas/atlas_catalogue.json. Replaces the mock catalogue below.
Verified against M4's real raw_results.json for both the phishing and
malware models — see PROJECT_LOG.md for the integration test notes.

Note: M3's build_findings_json(scan_id, raw_results) doesn't take `score` —
contract #6 (findings.json) never needed it, only contract #4 (raw_results).
Signature kept as (raw_results, score) here so nothing else in the backend
has to change; `score` is simply unused.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.services import contracts

logger = get_logger(__name__)

_ATLAS_DIR = Path(__file__).resolve().parents[3] / "atlas"
if str(_ATLAS_DIR) not in sys.path:
    sys.path.insert(0, str(_ATLAS_DIR))

from mitigation_engine import build_findings_json  # noqa: E402  (M3's real module)


def get_findings(raw_results: dict[str, Any], score: dict[str, Any]) -> dict[str, Any]:
    """Contract #4 + #5 in, contract #6 out. `score` unused — see module docstring."""
    logger.info("real atlas get_findings (M3)", extra={"scan_id": raw_results["scan_id"]})
    payload = build_findings_json(raw_results["scan_id"], raw_results)
    contracts.assert_findings_shape(payload)
    return payload