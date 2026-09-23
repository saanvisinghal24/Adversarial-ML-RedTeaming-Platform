"""Model artefact upload + listing.

Milestone 1 ships the real route shape (so M2/M3/M4 can code against Swagger today) with
basic suffix/size/checksum validation. Milestone 2 hardens this — see /docs/HANDOFF.md.
"""

import hashlib
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.logging import get_logger
from app.db.base import MLModel
from app.schemas.common import ErrorResponse
from app.schemas.model import ModelResponse

router = APIRouter(prefix="/models", tags=["models"])
logger = get_logger(__name__)

CHUNK_SIZE = 1024 * 1024


@router.post(
    "",
    response_model=ModelResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "unsupported file type"},
        413: {"model": ErrorResponse, "description": "file exceeds MAX_MODEL_SIZE_MB"},
    },
    summary="Upload a model artefact (.pkl / .onnx / .pt)",
)
def upload_model(
    current_user: CurrentUser,
    db: DbSession,
    name: str = Form(..., max_length=255),
    model_type: str = Form(..., description="sklearn|xgboost|pytorch|onnx"),
    version: str = Form("1", max_length=32),
    file: UploadFile = File(...),
) -> ModelResponse:
    if model_type not in {"sklearn", "xgboost", "pytorch", "onnx"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"unsupported model_type: {model_type}")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in settings.ALLOWED_MODEL_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported file type {suffix or '(none)'}; allowed: {', '.join(settings.ALLOWED_MODEL_SUFFIXES)}",
        )

    model_id = uuid.uuid4()
    dest_dir = settings.STORAGE_DIR / str(current_user.id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{model_id}{suffix}"

    digest = hashlib.sha256()
    size = 0
    try:
        with dest.open("wb") as out:
            while chunk := file.file.read(CHUNK_SIZE):
                size += len(chunk)
                if size > settings.max_model_size_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"file exceeds {settings.MAX_MODEL_SIZE_MB} MB limit",
                    )
                digest.update(chunk)
                out.write(chunk)
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise
    except OSError as exc:
        dest.unlink(missing_ok=True)
        logger.exception("model write failed", extra={"model_id": str(model_id)})
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="could not store model") from exc
    finally:
        file.file.close()

    record = MLModel(
        id=model_id,
        user_id=current_user.id,
        name=name,
        file_path=str(dest.resolve()),
        model_type=model_type,
        version=version,
        checksum_sha256=digest.hexdigest(),
        size_bytes=size,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    logger.info("model uploaded", extra={"model_id": str(record.id), "size_bytes": size})
    return ModelResponse.model_validate(record)


@router.get("", response_model=list[ModelResponse], summary="List the caller's models")
def list_models(current_user: CurrentUser, db: DbSession) -> list[ModelResponse]:
    rows = db.scalars(
        select(MLModel).where(MLModel.user_id == current_user.id).order_by(MLModel.created_at.desc())
    ).all()
    return [ModelResponse.model_validate(r) for r in rows]
