"""Training pipeline reconstruction from static evidence.

The stages below are reported exactly as observed. A stage is only marked
``detected`` when concrete code evidence exists; ``partial`` means the stage was
observed indirectly. Nothing is inferred about stages the repository does not
show.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from backend.code.evidence import SourceIndex, make_evidence
from backend.code.python_analysis import PythonFileAnalysis
from backend.code.schemas import (
    CodeEvidence,
    PipelineDetection,
    PipelineStage,
    PipelineStageStatus,
)

logger = logging.getLogger("replicai.code.pipeline")

STAGE_ORDER: tuple[tuple[str, str], ...] = (
    ("dataset_loading", "Dataset loading"),
    ("preprocessing", "Preprocessing / tokenization"),
    ("model_creation", "Model creation"),
    ("optimizer_creation", "Optimizer creation"),
    ("scheduler_creation", "Scheduler creation"),
    ("training_loop", "Training loop"),
    ("evaluation", "Evaluation"),
    ("metric_calculation", "Metric calculation"),
    ("checkpoint_saving", "Checkpoint saving"),
)


@dataclass(frozen=True)
class _SignalSpec:
    name: str
    detail: str
    status: PipelineStageStatus
    confidence: float


#: Signal name -> pipeline stage contribution.
STAGE_SIGNALS: dict[str, tuple[_SignalSpec, ...]] = {
    "dataset_loading": (
        _SignalSpec(
            "dataset_load", "dataset/dataloader construction", PipelineStageStatus.detected, 0.9
        ),
    ),
    "preprocessing": (
        _SignalSpec(
            "tokenization", "tokenizer or preprocessing call", PipelineStageStatus.detected, 0.8
        ),
    ),
    "model_creation": (
        _SignalSpec(
            "model_class", "neural network class definition", PipelineStageStatus.detected, 0.9
        ),
        _SignalSpec("class_definition", "class definition", PipelineStageStatus.partial, 0.5),
    ),
    "optimizer_creation": (
        _SignalSpec("optimizer_call", "optimizer construction", PipelineStageStatus.detected, 0.95),
        _SignalSpec("optimizer_class", "optimizer class", PipelineStageStatus.detected, 0.8),
    ),
    "scheduler_creation": (
        _SignalSpec(
            "scheduler_call",
            "learning rate scheduler construction",
            PipelineStageStatus.detected,
            0.95,
        ),
        _SignalSpec("scheduler_class", "scheduler class", PipelineStageStatus.detected, 0.8),
    ),
    "training_loop": (
        _SignalSpec("optimizer_step", "optimizer step", PipelineStageStatus.detected, 0.95),
        _SignalSpec("backward_pass", "loss backward pass", PipelineStageStatus.detected, 0.9),
        _SignalSpec("epoch_loop", "epoch loop", PipelineStageStatus.detected, 0.9),
        _SignalSpec("range_loop", "loop over ranges", PipelineStageStatus.partial, 0.6),
        _SignalSpec(
            "training_function", "training function definition", PipelineStageStatus.partial, 0.6
        ),
    ),
    "evaluation": (
        _SignalSpec(
            "evaluation_function", "evaluation function", PipelineStageStatus.detected, 0.9
        ),
        _SignalSpec("eval_mode_call", "model.eval() switch", PipelineStageStatus.detected, 0.8),
        _SignalSpec(
            "inference_context", "inference context manager", PipelineStageStatus.partial, 0.6
        ),
    ),
    "metric_calculation": (
        _SignalSpec("metric_call", "metric computation", PipelineStageStatus.detected, 0.92),
        _SignalSpec("metric_literal", "metric name reference", PipelineStageStatus.partial, 0.7),
    ),
    "checkpoint_saving": (
        _SignalSpec(
            "checkpoint_save", "checkpoint or model save", PipelineStageStatus.detected, 0.9
        ),
    ),
}


def _collect_signals(
    analyses: list[PythonFileAnalysis], signal_name: str
) -> list[tuple[PythonFileAnalysis, int, str]]:
    found: list[tuple[PythonFileAnalysis, int, str]] = []
    for analysis in analyses:
        for signal in analysis.signals:
            if signal.name == signal_name:
                found.append((analysis, signal.line, signal.detail or signal_name))
    return found


def _detect_stage(
    stage: str, analyses: list[PythonFileAnalysis], source_index: SourceIndex | None
) -> PipelineStage:
    specs = STAGE_SIGNALS.get(stage, ())
    evidence: list[CodeEvidence] = []
    reasons: list[str] = []
    best_status = PipelineStageStatus.not_detected

    for spec in specs:
        for analysis, line, detail in _collect_signals(analyses, spec.name):
            if len(evidence) >= 4:
                break
            evidence.append(
                make_evidence(
                    analysis.path,
                    line,
                    analysis.quote_at(line) or detail,
                    spec.confidence,
                    source_index=source_index,
                )
            )
            reasons.append(f"{spec.detail} in {analysis.path}:{line}")
            if spec.status is PipelineStageStatus.detected:
                best_status = PipelineStageStatus.detected
            elif best_status is PipelineStageStatus.not_detected:
                best_status = PipelineStageStatus.partial
        if len(evidence) >= 4:
            break

    # A detected training loop plus an epoch range is strong evidence even when
    # the optimizer step is hidden behind a framework call.
    if stage == "training_loop" and best_status is not PipelineStageStatus.detected:
        if any(
            signal.name == "optimizer_step" for analysis in analyses for signal in analysis.signals
        ):
            best_status = PipelineStageStatus.detected

    reason = (
        "; ".join(reasons[:3])
        if reasons
        else f"no evidence for {stage.replace('_', ' ')} was found in the repository"
    )
    return PipelineStage(
        name=stage,
        status=best_status,
        evidence=evidence,
        reason=reason,
    )


def detect_pipeline(
    analyses: list[PythonFileAnalysis], source_index: SourceIndex | None = None
) -> PipelineDetection:
    """Build the ordered training pipeline for a repository."""
    stages = [_detect_stage(stage, analyses, source_index) for stage, _label in STAGE_ORDER]
    detected = sum(1 for stage in stages if stage.status is PipelineStageStatus.detected)
    logger.info("event=pipeline_detected stages=%s detected=%s", len(stages), detected)
    return PipelineDetection(stages=stages)
