"""SQLAlchemy models for the Code Intelligence module (Part 2).

Design notes:

* repository *source code* is never stored; only metadata, detected file roles,
  parameter evidence, mappings and readiness results are persisted,
* Part 1 tables (``papers``, ``experiments``, ``experiment_parameters``,
  ``evidence``) are reused through foreign keys and are not duplicated,
* JSON columns are used only for genuinely structured payloads (file role
  evidence and per-item evidence lists).
"""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from backend.database import Base


class Repository(Base):
    """Metadata about one analyzed GitHub repository."""

    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=True, index=True)
    url = Column(String(2048), nullable=False)
    normalized_url = Column(String(2048), nullable=False, index=True)
    owner = Column(String(128), nullable=False)
    name = Column(String(255), nullable=False)
    branch = Column(String(255), nullable=True)
    commit_sha = Column(String(128), nullable=True)
    analyzed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(String(32), nullable=False, default="analyzed")
    file_count = Column(Integer, nullable=False, default=0)
    python_file_count = Column(Integer, nullable=False, default=0)
    total_bytes = Column(Integer, nullable=False, default=0)
    warnings = Column(JSON, nullable=True)

    files = relationship("CodeFile", back_populates="repository", cascade="all, delete-orphan")
    evidences = relationship(
        "CodeEvidence", back_populates="repository", cascade="all, delete-orphan"
    )
    readiness_reports = relationship(
        "ReadinessReport",
        back_populates="repository",
        cascade="all, delete-orphan",
    )
    mappings = relationship(
        "ExperimentCodeMapping", back_populates="repository", cascade="all, delete-orphan"
    )


class CodeFile(Base):
    """A detected repository file and the role ReplicAI assigned to it."""

    __tablename__ = "code_files"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    path = Column(String(1024), nullable=False)
    file_type = Column(String(32), nullable=True)
    role = Column(String(64), nullable=False)
    confidence = Column(Float, nullable=False, default=0.0)
    size_bytes = Column(Integer, nullable=True)
    evidence = Column(JSON, nullable=True)

    repository = relationship("Repository", back_populates="files")


class CodeEvidence(Base):
    """A verifiable pointer into an analyzed source file."""

    __tablename__ = "code_evidence"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    code_file_id = Column(Integer, ForeignKey("code_files.id"), nullable=True, index=True)
    file_path = Column(String(1024), nullable=False)
    evidence_type = Column(String(64), nullable=False)
    symbol = Column(String(255), nullable=True)
    value = Column(JSON, nullable=True)
    line_start = Column(Integer, nullable=True)
    line_end = Column(Integer, nullable=True)
    quote = Column(Text, nullable=True)
    confidence = Column(Float, nullable=False, default=0.0)
    verified = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    repository = relationship("Repository", back_populates="evidences")


class ExperimentCodeMapping(Base):
    """A paper parameter compared against a detected code parameter."""

    __tablename__ = "experiment_code_mappings"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    paper_field = Column(String(128), nullable=False)
    paper_value = Column(JSON, nullable=True)
    code_field = Column(String(128), nullable=True)
    code_value = Column(JSON, nullable=True)
    status = Column(String(32), nullable=False)
    confidence = Column(Float, nullable=False, default=0.0)
    reason = Column(Text, nullable=True)
    code_evidence_id = Column(Integer, ForeignKey("code_evidence.id"), nullable=True)
    paper_evidence = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    repository = relationship("Repository", back_populates="mappings")
    code_evidence = relationship("CodeEvidence")


class ReadinessReport(Base):
    """A deterministic readiness score for one experiment/repository pair."""

    __tablename__ = "readiness_reports"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    overall_score = Column(Float, nullable=False, default=0.0)
    status = Column(String(32), nullable=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    repository = relationship("Repository", back_populates="readiness_reports")
    items = relationship("ReadinessItem", back_populates="report", cascade="all, delete-orphan")


class ReadinessItem(Base):
    """One readiness category contributing to the overall score."""

    __tablename__ = "readiness_items"

    id = Column(Integer, primary_key=True, index=True)
    readiness_report_id = Column(
        Integer, ForeignKey("readiness_reports.id"), nullable=False, index=True
    )
    category = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False)
    weight = Column(Float, nullable=False, default=0.0)
    score = Column(Float, nullable=False, default=0.0)
    reason = Column(Text, nullable=True)
    evidence = Column(JSON, nullable=True)

    report = relationship("ReadinessReport", back_populates="items")
