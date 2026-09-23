"""The one place the four modules meet: job_config -> raw_results -> score -> findings -> DB.

Everything M2/M3/M4 owns is reached through sandbox_client / atlas_client only.
Swapping a mock for the real service never touches this file.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.db.base import Finding, RawResult, Scan, Score, utcnow
from app.db.session import SessionLocal
from app.services import atlas_client, sandbox_client
from app.services.contracts import build_job_config

logger = get_logger(__name__)


def run_scan_pipeline(scan_id: UUID) -> None:
    """Executed as a FastAPI BackgroundTask. Owns its own DB session — the request's is gone."""
    db: Session = SessionLocal()
    try:
        scan = db.get(Scan, scan_id)
        if scan is None:
            logger.error("pipeline: scan disappeared", extra={"scan_id": str(scan_id)})
            return

        scan.status = "running"
        db.commit()

        job_config = build_job_config(
            scan_id=scan.id,
            model_path=scan.model.file_path,
            model_type=scan.model.model_type,
            threat_model=scan.threat_model,
            attacks=scan.attack_config.get("attacks", ["fgsm"]),
            params=scan.attack_config.get("params", {}),
        )

        # Backstop timeout: M2's container has its own kill switch, but a hung/looping
        # sandbox must never leave a scan stuck on "running" forever.
        raw_results = _with_timeout(sandbox_client.run_scan, job_config)   # M2 seam
        score = sandbox_client.score_results(raw_results)                  # M2 seam
        findings = atlas_client.get_findings(raw_results, score)           # M3 seam

        _persist(db, scan, raw_results, score, findings)
        logger.info("scan complete", extra={"scan_id": str(scan_id), "grade": score["grade"]})

    except Exception as exc:  # noqa: BLE001 — background task must never die silently
        logger.exception("scan failed", extra={"scan_id": str(scan_id)})
        db.rollback()
        _mark_failed(db, scan_id, str(exc))
    finally:
        db.close()


class ScanTimeout(Exception):
    """The sandbox did not return within SCAN_TIMEOUT_SECONDS."""


def _with_timeout(func, job_config: dict) -> dict:
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(func, job_config)
        try:
            return future.result(timeout=settings.SCAN_TIMEOUT_SECONDS)
        except FuturesTimeout as exc:
            raise ScanTimeout(
                f"sandbox exceeded {settings.SCAN_TIMEOUT_SECONDS}s timeout"
            ) from exc


def _persist(db: Session, scan: Scan, raw_results: dict, score: dict, findings: dict) -> None:
    db.merge(RawResult(scan_id=scan.id, json_blob=raw_results))
    db.merge(
        Score(
            scan_id=scan.id,
            component_scores=score["component_scores"],
            weights=score["weights"],
            final_score=score["final_score_0_100"],
            grade=score["grade"],
        )
    )
    for entry in findings["findings"]:
        db.add(
            Finding(
                scan_id=scan.id,
                attack=entry["attack"],
                atlas_tactic=entry["atlas_tactic"],
                atlas_technique=entry["atlas_technique"],
                severity=entry["severity"],
                evidence=entry.get("evidence", {}),
                mitigation=entry["mitigation"],
                owasp_ref=entry.get("owasp_ml_top10"),
                nist_ref=entry.get("nist_ai_rmf"),
            )
        )
    scan.status = "done"
    scan.completed_at = utcnow()
    db.commit()


def _mark_failed(db: Session, scan_id: UUID, error: str) -> None:
    scan = db.get(Scan, scan_id)
    if scan is None:
        return
    scan.status = "failed"
    scan.error = error[:1000]
    scan.completed_at = utcnow()
    db.commit()
