"""Pydantic schemas for the Code Intelligence module (Part 2)."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FileRole(str, Enum):
    training_entrypoint = "training_entrypoint"
    evaluation_entrypoint = "evaluation_entrypoint"
    inference_entrypoint = "inference_entrypoint"
    configuration = "configuration"
    dataset = "dataset"
    model_definition = "model_definition"
    optimizer = "optimizer"
    scheduler = "scheduler"
    metrics = "metrics"
    documentation = "documentation"
    dependency_manifest = "dependency_manifest"
    unknown = "unknown"


class MappingStatus(str, Enum):
    matched = "matched"
    mismatched = "mismatched"
    missing_in_code = "missing_in_code"
    missing_in_paper = "missing_in_paper"
    uncertain = "uncertain"


class PipelineStageStatus(str, Enum):
    detected = "detected"
    partial = "partial"
    not_detected = "not_detected"
    unknown = "unknown"


class ReadinessCategoryStatus(str, Enum):
    ready = "ready"
    partial = "partial"
    missing = "missing"
    uncertain = "uncertain"


class OverallReadinessStatus(str, Enum):
    ready = "ready"
    mostly_ready = "mostly_ready"
    partial = "partial"
    not_ready = "not_ready"


class RepositoryAnalysisStatus(str, Enum):
    analyzed = "analyzed"
    partial = "partial"
    failed = "failed"


def _clamp_confidence(value: float) -> float:
    if value < 0 or value > 1:
        raise ValueError("confidence must be between 0 and 1")
    return round(value, 4)


# --------------------------------------------------------------------------- #
# Evidence
# --------------------------------------------------------------------------- #
class CodeEvidence(BaseModel):
    """A verifiable pointer into an analyzed source file."""

    model_config = ConfigDict(extra="forbid")

    source_type: str = "code"
    file: str
    line_start: int | None = None
    line_end: int | None = None
    quote: str | None = None
    confidence: float = 0.0
    verified: bool = True

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        return _clamp_confidence(value)


# --------------------------------------------------------------------------- #
# Request / response envelopes
# --------------------------------------------------------------------------- #
class CodeAnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repository_url: str = Field(min_length=1, max_length=2048)
    paper_id: str | None = None
    experiment_id: str = Field(min_length=1, max_length=128)
    branch: str | None = Field(default=None, max_length=255)


class RepositorySummary(BaseModel):
    id: str
    url: str
    normalized_url: str
    owner: str
    name: str
    branch: str | None = None
    commit_sha: str | None = None
    analyzed_at: str
    file_count: int
    python_file_count: int
    analysis_status: RepositoryAnalysisStatus
    warnings: list[str] = Field(default_factory=list)


class DetectedFile(BaseModel):
    path: str
    file_type: str
    role: FileRole
    confidence: float
    evidence: list[str] = Field(default_factory=list)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        return _clamp_confidence(value)


class CodeParameter(BaseModel):
    """A single canonical parameter detected in repository source code."""

    name: str
    value: Any = None
    file: str | None = None
    line: int | None = None
    quote: str | None = None
    confidence: float = 0.0
    origin: str | None = None

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        return _clamp_confidence(value)


class CodeOptimizer(BaseModel):
    name: str
    file: str
    line: int
    learning_rate: float | None = None
    weight_decay: float | None = None
    momentum: float | None = None
    quote: str


class CodeSymbolUsage(BaseModel):
    name: str
    file: str
    line: int
    quote: str


class PipelineStage(BaseModel):
    name: str
    status: PipelineStageStatus
    evidence: list[CodeEvidence] = Field(default_factory=list)
    reason: str | None = None


class PipelineDetection(BaseModel):
    stages: list[PipelineStage] = Field(default_factory=list)


class PaperEvidenceRef(BaseModel):
    """Provenance for a paper-side value, taken from the Part 1 evidence table."""

    model_config = ConfigDict(extra="forbid")

    page: int | None = None
    quote: str | None = None
    source_type: str | None = None
    source_label: str | None = None
    confidence: float | None = None


class ParameterMapping(BaseModel):
    paper_field: str
    paper_value: Any = None
    code_field: str | None = None
    code_value: Any = None
    status: MappingStatus
    confidence: float = 0.0
    reason: str
    evidence: CodeEvidence | None = None
    conflicting_evidence: list[CodeEvidence] = Field(default_factory=list)
    paper_evidence: list[PaperEvidenceRef] = Field(default_factory=list)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        return _clamp_confidence(value)


class ReadinessItem(BaseModel):
    category: str
    weight: float
    status: ReadinessCategoryStatus
    score: float
    reason: str
    evidence: list[CodeEvidence] = Field(default_factory=list)

    @field_validator("score")
    @classmethod
    def validate_score(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("score must be between 0 and 1")
        return round(value, 4)


class ReadinessBlocker(BaseModel):
    category: str
    message: str
    severity: str


class ReadinessWarning(BaseModel):
    category: str
    message: str


class ReadinessReportSummary(BaseModel):
    id: str
    overall_score: float
    status: OverallReadinessStatus
    generated_at: str
    items: list[ReadinessItem] = Field(default_factory=list)
    blockers: list[ReadinessBlocker] = Field(default_factory=list)
    warnings: list[ReadinessWarning] = Field(default_factory=list)


class CodeAnalysisResponse(BaseModel):
    repository: RepositorySummary
    experiment_id: str
    paper_id: str | None = None
    entry_points: list[DetectedFile] = Field(default_factory=list)
    files: list[DetectedFile] = Field(default_factory=list)
    code_parameters: list[CodeParameter] = Field(default_factory=list)
    optimizers: list[CodeOptimizer] = Field(default_factory=list)
    schedulers: list[CodeSymbolUsage] = Field(default_factory=list)
    loss_functions: list[CodeSymbolUsage] = Field(default_factory=list)
    metrics: list[CodeSymbolUsage] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    pipeline: PipelineDetection
    mappings: list[ParameterMapping] = Field(default_factory=list)
    readiness: ReadinessReportSummary
    warnings: list[str] = Field(default_factory=list)


class RepositoryDetailResponse(RepositorySummary):
    entry_points: list[DetectedFile] = Field(default_factory=list)


class RepositoryFilesResponse(BaseModel):
    repository_id: str
    total: int
    files: list[DetectedFile] = Field(default_factory=list)


class RepositoryMappingsResponse(BaseModel):
    repository_id: str
    experiment_id: str | None = None
    total: int
    mappings: list[ParameterMapping] = Field(default_factory=list)


class RepositoryReadinessResponse(BaseModel):
    repository_id: str
    experiment_id: str | None = None
    readiness: ReadinessReportSummary
