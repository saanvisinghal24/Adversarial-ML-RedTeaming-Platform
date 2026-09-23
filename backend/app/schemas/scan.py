"""Request/response shapes for scans. The nested contract objects mirror
ARCHITECTURE.md contracts #3-#6 exactly — do not add fields here without editing that file."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ThreatModel = Literal["white_box", "black_box"]
AttackName = Literal["fgsm", "pgd", "hopskipjump", "poisoning"]
ScanStatus = Literal["queued", "running", "done", "failed"]
Severity = Literal["low", "medium", "high", "critical"]


class ScanCreateRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: UUID
    threat_model: ThreatModel = "white_box"
    attacks: list[AttackName] = Field(default_factory=lambda: ["fgsm"], min_length=1)
    # free-form per-attack params; shape is contract #3's "params" block
    params: dict[str, dict[str, Any]] = Field(default_factory=dict)


class ScoreResponse(BaseModel):
    """Contract #5."""

    model_config = ConfigDict(from_attributes=True)

    component_scores: dict[str, float]
    weights: dict[str, float]
    final_score_0_100: float = Field(..., ge=0, le=100)
    grade: Literal["A", "B", "C", "D", "F"]


class FindingResponse(BaseModel):
    """Contract #6, one entry."""

    model_config = ConfigDict(from_attributes=True)

    attack: str
    atlas_tactic: str
    atlas_technique: str
    severity: Severity
    evidence: dict[str, Any] = Field(default_factory=dict)
    mitigation: str
    owasp_ml_top10: str | None = None
    nist_ai_rmf: str | None = None


class ScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID
    model_id: UUID
    status: ScanStatus
    threat_model: ThreatModel
    attack_config: dict[str, Any]
    created_at: datetime
    completed_at: datetime | None = None
    error: str | None = None
    # populated only once status == "done"
    score: ScoreResponse | None = None
    findings: list[FindingResponse] = Field(default_factory=list)
    raw_results: dict[str, Any] | None = Field(
        None, description="contract #4 blob, verbatim as produced by the attack engine"
    )


class ScanSummary(BaseModel):
    """Row shape for GET /models/{id}/scans (score-history trend view)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: ScanStatus
    created_at: datetime
    final_score: float | None = None
    grade: str | None = None
