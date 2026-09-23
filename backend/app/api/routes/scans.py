"""Scan creation + polling. The background task runs the mocked M2/M3/M4 pipeline."""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, DbSession
from app.core.logging import get_logger
from app.db.base import MLModel, Scan
from app.schemas.common import ErrorResponse
from app.schemas.scan import (
    FindingResponse,
    ScanCreateRequest,
    ScanResponse,
    ScanSummary,
    ScoreResponse,
)
from app.services.pipeline import run_scan_pipeline

router = APIRouter(tags=["scans"])
logger = get_logger(__name__)


def _owned_model(db: Session, model_id: UUID, user_id: UUID) -> MLModel:
    model = db.get(MLModel, model_id)
    if model is None or model.user_id != user_id:
        # 404 rather than 403 — don't confirm that someone else's model id exists
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="model not found")
    return model


@router.post(
    "/scans",
    response_model=ScanResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={404: {"model": ErrorResponse, "description": "model not found"}},
    summary="Queue a scan (returns immediately; poll GET /scans/{id})",
)
def create_scan(
    payload: ScanCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: DbSession,
) -> ScanResponse:
    _owned_model(db, payload.model_id, current_user.id)

    scan = Scan(
        model_id=payload.model_id,
        status="queued",
        threat_model=payload.threat_model,
        attack_config={"attacks": payload.attacks, "params": payload.params},
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    background_tasks.add_task(run_scan_pipeline, scan.id)
    logger.info("scan queued", extra={"scan_id": str(scan.id), "attacks": payload.attacks})
    return _to_response(scan)


@router.get(
    "/scans/{scan_id}",
    response_model=ScanResponse,
    responses={404: {"model": ErrorResponse, "description": "scan not found"}},
    summary="Scan status; score + findings once status is done",
)
def get_scan(scan_id: UUID, current_user: CurrentUser, db: DbSession) -> ScanResponse:
    return _to_response(_owned_scan(db, scan_id, current_user.id))


@router.get(
    "/models/{model_id}/scans",
    response_model=list[ScanSummary],
    responses={404: {"model": ErrorResponse, "description": "model not found"}},
    summary="Score history for one model (trend view)",
)
def list_model_scans(model_id: UUID, current_user: CurrentUser, db: DbSession) -> list[ScanSummary]:
    _owned_model(db, model_id, current_user.id)
    scans = db.scalars(
        select(Scan).where(Scan.model_id == model_id).order_by(Scan.created_at.desc())
    ).all()
    return [
        ScanSummary(
            id=s.id,
            status=s.status,
            created_at=s.created_at,
            final_score=s.score.final_score if s.score else None,
            grade=s.score.grade if s.score else None,
        )
        for s in scans
    ]


@router.get(
    "/scans/{scan_id}/score",
    response_model=ScoreResponse,
    responses={404: {"model": ErrorResponse, "description": "scan not found"},
               409: {"model": ErrorResponse, "description": "scan has no score yet"}},
    summary="Just the scorecard (contract #5)",
)
def get_scan_score(scan_id: UUID, current_user: CurrentUser, db: DbSession) -> ScoreResponse:
    scan = _owned_scan(db, scan_id, current_user.id)
    if scan.score is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"no score yet; scan status is {scan.status}",
        )
    return ScoreResponse(
        component_scores=scan.score.component_scores,
        weights=scan.score.weights,
        final_score_0_100=scan.score.final_score,
        grade=scan.score.grade,
    )


@router.get(
    "/scans/{scan_id}/findings",
    response_model=list[FindingResponse],
    responses={404: {"model": ErrorResponse, "description": "scan not found"}},
    summary="Ranked ATLAS findings (contract #6 rows), most severe first",
)
def get_scan_findings(scan_id: UUID, current_user: CurrentUser, db: DbSession) -> list[FindingResponse]:
    scan = _owned_scan(db, scan_id, current_user.id)
    return sorted(
        (_finding_response(f) for f in scan.findings),
        key=lambda f: SEVERITY_ORDER.get(f.severity, 0),
        reverse=True,
    )


SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def _owned_scan(db: Session, scan_id: UUID, user_id: UUID) -> Scan:
    scan = db.get(Scan, scan_id)
    if scan is None or scan.model.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scan not found")
    return scan


def _finding_response(f) -> FindingResponse:
    return FindingResponse(
        attack=f.attack,
        atlas_tactic=f.atlas_tactic,
        atlas_technique=f.atlas_technique,
        severity=f.severity,
        evidence=f.evidence,
        mitigation=f.mitigation,
        owasp_ml_top10=f.owasp_ref,
        nist_ai_rmf=f.nist_ref,
    )


def _to_response(scan: Scan) -> ScanResponse:
    score = None
    if scan.score is not None:
        score = ScoreResponse(
            component_scores=scan.score.component_scores,
            weights=scan.score.weights,
            final_score_0_100=scan.score.final_score,
            grade=scan.score.grade,
        )
    return ScanResponse(
        id=scan.id,
        model_id=scan.model_id,
        status=scan.status,
        threat_model=scan.threat_model,
        attack_config=scan.attack_config,
        created_at=scan.created_at,
        completed_at=scan.completed_at,
        error=scan.error,
        score=score,
        findings=sorted(
            (_finding_response(f) for f in scan.findings),
            key=lambda f: SEVERITY_ORDER.get(f.severity, 0),
            reverse=True,
        ),
        raw_results=scan.raw_result.json_blob if scan.raw_result else None,
    )
