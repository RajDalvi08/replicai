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


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    sha256 = Column(String(128), nullable=False, index=True)
    page_count = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    experiments = relationship(
        "ExperimentRecord", back_populates="paper", cascade="all, delete-orphan"
    )


class ExperimentRecord(Base):
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False)
    experiment_key = Column(String(128), nullable=False)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    extraction_confidence = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    paper = relationship("Paper", back_populates="experiments")
    parameters = relationship(
        "ExperimentParameter", back_populates="experiment", cascade="all, delete-orphan"
    )
    evidences = relationship(
        "EvidenceRecord", back_populates="experiment", cascade="all, delete-orphan"
    )


class ExperimentParameter(Base):
    __tablename__ = "experiment_parameters"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False)
    field_name = Column(String(128), nullable=False)
    field_value = Column(JSON, nullable=True)
    value_type = Column(String(32), nullable=True)
    observed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    experiment = relationship("ExperimentRecord", back_populates="parameters")


class EvidenceRecord(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False)
    field = Column(String(128), nullable=False)
    value = Column(JSON, nullable=True)
    page = Column(Integer, nullable=True)
    source_type = Column(String(64), nullable=True)
    source_label = Column(String(128), nullable=True)
    quote = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    experiment = relationship("ExperimentRecord", back_populates="evidences")
