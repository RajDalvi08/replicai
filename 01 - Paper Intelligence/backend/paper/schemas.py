from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExperimentEvidence(BaseModel):
    field: str
    value: Any = None
    page: int | None = None
    source_type: str | None = None
    source_label: str | None = None
    quote: str | None = None
    confidence: float = 0.0

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("confidence must be between 0 and 1")
        return value


class ReportedResult(BaseModel):
    value: float | int | None = None
    unit: str | None = None
    higher_is_better: bool = True


class Experiment(BaseModel):
    model_config = ConfigDict(extra="allow")

    experiment_id: str
    title: str | None = None
    description: str | None = None
    dataset: str | None = None
    model: str | None = None
    optimizer: str | None = None
    learning_rate: float | None = None
    batch_size: int | None = None
    epochs: int | None = None
    scheduler: str | None = None
    weight_decay: float | None = None
    dropout: float | None = None
    random_seed: int | None = None
    metric: str | None = None
    reported_results: dict[str, ReportedResult] = Field(default_factory=dict)
    procedure: str | None = None
    evidence: list[ExperimentEvidence] = Field(default_factory=list)
    extraction_confidence: float = 0.0
    warnings: list[str] = Field(default_factory=list)

    @field_validator("extraction_confidence")
    @classmethod
    def validate_extraction_confidence(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("extraction_confidence must be between 0 and 1")
        return value


class SyntheticExperiment(Experiment):
    pass


class PaperAnalysisResponse(BaseModel):
    paper_id: str
    filename: str
    page_count: int
    experiments: list[Experiment]
    warnings: list[str] = Field(default_factory=list)


class PaperSummaryResponse(BaseModel):
    paper_id: str
    filename: str
    sha256: str
    page_count: int
    created_at: str
