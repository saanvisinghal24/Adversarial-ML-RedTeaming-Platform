"""SQLAlchemy 2.0 models — ARCHITECTURE.md section 7, implemented verbatim.

Column types are chosen so the same models run on Postgres 15 (JSONB, native uuid)
and on SQLite for fast tests, without a second schema definition.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# JSONB on Postgres, plain JSON elsewhere (tests).
JSONType = JSON().with_variant(JSONB, "postgresql")

SCAN_STATUSES = ("queued", "running", "done", "failed")
THREAT_MODELS = ("white_box", "black_box")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    models: Mapped[list["MLModel"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class MLModel(Base):
    """`models` table. Class name avoids clashing with pydantic/SQLAlchemy `model_` namespaces."""

    __tablename__ = "models"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    model_type: Mapped[str] = mapped_column(String(32), nullable=False)  # sklearn|xgboost|pytorch|onnx
    version: Mapped[str] = mapped_column(String(32), default="1", nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    user: Mapped[User] = relationship(back_populates="models")
    scans: Mapped[list["Scan"]] = relationship(back_populates="model", cascade="all, delete-orphan")


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    model_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("models.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="queued", nullable=False)
    threat_model: Mapped[str] = mapped_column(String(16), nullable=False)
    attack_config: Mapped[dict] = mapped_column(JSONType, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    model: Mapped[MLModel] = relationship(back_populates="scans")
    raw_result: Mapped["RawResult | None"] = relationship(back_populates="scan", cascade="all, delete-orphan", uselist=False)
    score: Mapped["Score | None"] = relationship(back_populates="scan", cascade="all, delete-orphan", uselist=False)
    findings: Mapped[list["Finding"]] = relationship(back_populates="scan", cascade="all, delete-orphan")


class RawResult(Base):
    """Contract #4 stored verbatim — never reshaped, so M4 owns its format alone."""

    __tablename__ = "raw_results"

    scan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scans.id", ondelete="CASCADE"), primary_key=True)
    json_blob: Mapped[dict] = mapped_column(JSONType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    scan: Mapped[Scan] = relationship(back_populates="raw_result")


class Score(Base):
    """Contract #5."""

    __tablename__ = "scores"

    scan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scans.id", ondelete="CASCADE"), primary_key=True)
    component_scores: Mapped[dict] = mapped_column(JSONType, nullable=False)
    weights: Mapped[dict] = mapped_column(JSONType, nullable=False)
    final_score: Mapped[float] = mapped_column(Float, nullable=False)
    grade: Mapped[str] = mapped_column(String(1), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    scan: Mapped[Scan] = relationship(back_populates="score")


class Finding(Base):
    """Contract #6, one row per findings[] entry."""

    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scans.id", ondelete="CASCADE"), nullable=False)
    attack: Mapped[str] = mapped_column(String(32), nullable=False)
    atlas_tactic: Mapped[str] = mapped_column(String(32), nullable=False)
    atlas_technique: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    mitigation: Mapped[str] = mapped_column(Text, nullable=False)
    owasp_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    nist_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)

    scan: Mapped[Scan] = relationship(back_populates="findings")


Index("ix_scans_model_id_created_at", Scan.model_id, Scan.created_at.desc())
Index("ix_findings_scan_id", Finding.scan_id)
