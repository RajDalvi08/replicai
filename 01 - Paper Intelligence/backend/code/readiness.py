"""Deterministic reproducibility readiness engine.

The readiness score answers one narrow question: *does this repository appear to
contain enough explicit configuration to attempt a reproduction run?* It is not
a claim that a reproduction will succeed, and no LLM is involved in computing
it.

The overall score is fully reproducible from the per-category scores::

    overall_score = sum(category.weight * category.score)

The weights below total exactly 100, so the overall score is already a
percentage. Overall status thresholds are product logic, documented here and in
the README:

===========  ===========
score range  status
===========  ===========
90 - 100     ready
75 - 89      mostly_ready
50 - 74      partial
0 - 49       not_ready
===========  ===========
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from backend.code.analyzer import RepositoryStructure
from backend.code.evidence import SourceIndex, make_evidence
from backend.code.schemas import (
    CodeEvidence,
    CodeOptimizer,
    CodeParameter,
    FileRole,
    MappingStatus,
    OverallReadinessStatus,
    ParameterMapping,
    PipelineDetection,
    PipelineStageStatus,
    ReadinessBlocker,
    ReadinessCategoryStatus,
    ReadinessItem,
    ReadinessWarning,
)

logger = logging.getLogger("replicai.code.readiness")

#: Category -> weight. The weights sum to 100.
CATEGORY_WEIGHTS: dict[str, float] = {
    "entry_point": 15.0,
    "dataset": 15.0,
    "model": 15.0,
    "training_parameters": 15.0,
    "optimizer": 10.0,
    "evaluation": 10.0,
    "metrics": 10.0,
    "dependencies": 5.0,
    "random_seed": 2.5,
    "paper_code_consistency": 2.5,
}

#: Reporting order for categories.
CATEGORY_ORDER: tuple[str, ...] = (
    "entry_point",
    "dataset",
    "model",
    "training_parameters",
    "optimizer",
    "evaluation",
    "metrics",
    "dependencies",
    "random_seed",
    "paper_code_consistency",
)

CATEGORY_LABELS: dict[str, str] = {
    "entry_point": "Entry point",
    "dataset": "Dataset",
    "model": "Model",
    "training_parameters": "Training parameters",
    "optimizer": "Optimizer",
    "evaluation": "Evaluation",
    "metrics": "Metrics",
    "dependencies": "Dependencies",
    "random_seed": "Random seed",
    "paper_code_consistency": "Paper/code consistency",
}

#: Documented overall status thresholds (inclusive lower bound).
STATUS_THRESHOLDS: tuple[tuple[float, OverallReadinessStatus], ...] = (
    (90.0, OverallReadinessStatus.ready),
    (75.0, OverallReadinessStatus.mostly_ready),
    (50.0, OverallReadinessStatus.partial),
    (0.0, OverallReadinessStatus.not_ready),
)

#: Parameters required for a fully specified training configuration.
TRAINING_PARAMETER_KEYS: tuple[str, ...] = ("learning_rate", "batch_size", "epochs")

#: Parameters considered when measuring paper/code agreement.
CONSISTENCY_KEYS: tuple[str, ...] = (
    "dataset",
    "model",
    "optimizer",
    "learning_rate",
    "batch_size",
    "epochs",
    "scheduler",
    "weight_decay",
    "dropout",
    "random_seed",
    "metric",
)


def status_for_score(score: float) -> ReadinessCategoryStatus:
    """Map a category score in [0, 1] onto a status label."""
    if score >= 0.9:
        return ReadinessCategoryStatus.ready
    if score >= 0.5:
        return ReadinessCategoryStatus.partial
    if score > 0.0:
        return ReadinessCategoryStatus.uncertain
    return ReadinessCategoryStatus.missing


def overall_status_for(score: float) -> OverallReadinessStatus:
    """Map an overall percentage onto a product status label."""
    for threshold, status in STATUS_THRESHOLDS:
        if score >= threshold:
            return status
    return OverallReadinessStatus.not_ready  # pragma: no cover - unreachable


@dataclass
class CategoryResult:
    category: str
    score: float
    reason: str
    evidence: list[CodeEvidence] = field(default_factory=list)


@dataclass(frozen=True)
class ReadinessOutcome:
    items: list[ReadinessItem]
    overall_score: float
    status: OverallReadinessStatus
    blockers: list[ReadinessBlocker]
    warnings: list[ReadinessWarning]


def _evidence_for_parameter(
    parameter: CodeParameter | None, source_index: SourceIndex | None
) -> list[CodeEvidence]:
    if parameter is None or parameter.file is None or parameter.line is None:
        return []
    return [
        make_evidence(
            parameter.file,
            parameter.line,
            parameter.quote,
            parameter.confidence,
            source_index=source_index,
        )
    ]


# --------------------------------------------------------------------------- #
# Per-category rules. Every rule is a pure function of observed evidence.
# --------------------------------------------------------------------------- #
def _entry_point_result(structure: RepositoryStructure) -> CategoryResult:
    entries = structure.entry_points()
    if not entries:
        return CategoryResult(
            "entry_point",
            0.0,
            "No training, evaluation or inference entry point was detected.",
        )
    best = max(entries, key=lambda item: item.confidence)
    if best.role is not FileRole.training_entrypoint:
        return CategoryResult(
            "entry_point",
            0.4,
            f"Only a {best.role.value} ({best.path}) was detected; no training entry "
            "point was found.",
        )
    if best.confidence >= 0.8:
        return CategoryResult(
            "entry_point",
            1.0,
            f"Training entry point {best.path} detected with confidence {best.confidence}.",
        )
    if best.confidence >= 0.5:
        return CategoryResult(
            "entry_point",
            0.7,
            f"Likely training entry point {best.path} detected with weak supporting evidence.",
        )
    return CategoryResult(
        "entry_point",
        0.4,
        f"{best.path} only weakly resembles a training entry point.",
    )


def _named_parameter_result(
    category: str,
    parameter: CodeParameter | None,
    required: str,
    source_index: SourceIndex | None,
) -> CategoryResult:
    if parameter is None:
        return CategoryResult(
            category, 0.0, f"No {required} could be identified from the repository."
        )
    return CategoryResult(
        category,
        1.0,
        f"{required} {parameter.value!r} detected in {parameter.file}:{parameter.line}.",
        _evidence_for_parameter(parameter, source_index),
    )


def _file_only_result(
    category: str, structure: RepositoryStructure, role: FileRole, required: str
) -> CategoryResult:
    detected = structure.detected_by_role(role)
    if not detected:
        return CategoryResult(category, 0.0, f"No {required} was found in the repository.")
    best = max(detected, key=lambda item: item.confidence)
    return CategoryResult(
        category,
        0.6,
        f"{required} code found in {best.path} but no explicit name was detected.",
    )


def _training_parameters_result(
    parameters: dict[str, CodeParameter], source_index: SourceIndex | None
) -> CategoryResult:
    found = [key for key in TRAINING_PARAMETER_KEYS if key in parameters]
    missing = [key for key in TRAINING_PARAMETER_KEYS if key not in parameters]
    ratio = round(len(found) / len(TRAINING_PARAMETER_KEYS), 4)
    evidence: list[CodeEvidence] = []
    for key in found:
        evidence.extend(_evidence_for_parameter(parameters[key], source_index))
    if not missing:
        return CategoryResult(
            "training_parameters",
            1.0,
            "Learning rate, batch size and epochs are all configured explicitly.",
            evidence,
        )
    configured = ", ".join(f"{key}={parameters[key].value!r}" for key in found)
    reason = f"Configured training parameters: {configured}. Missing: {', '.join(missing)}."
    return CategoryResult("training_parameters", ratio, reason, evidence)


def _optimizer_result(
    parameters: dict[str, CodeParameter],
    optimizers: list[CodeOptimizer],
    source_index: SourceIndex | None,
) -> CategoryResult:
    optimizer = parameters.get("optimizer")
    learning_rate = parameters.get("learning_rate")
    if optimizer is not None and learning_rate is not None:
        return CategoryResult(
            "optimizer",
            1.0,
            f"{optimizer.value} with learning rate {learning_rate.value} detected in "
            f"{optimizer.file}:{optimizer.line}.",
            _evidence_for_parameter(optimizer, source_index)
            + _evidence_for_parameter(learning_rate, source_index),
        )
    if optimizer is not None:
        return CategoryResult(
            "optimizer",
            0.75,
            f"{optimizer.value} detected in {optimizer.file}:{optimizer.line} but no "
            "explicit learning rate was found.",
            _evidence_for_parameter(optimizer, source_index),
        )
    if learning_rate is not None:
        return CategoryResult(
            "optimizer",
            0.5,
            f"A learning rate of {learning_rate.value} was found in "
            f"{learning_rate.file}:{learning_rate.line} but no optimizer was identified.",
            _evidence_for_parameter(learning_rate, source_index),
        )
    if optimizers:
        return CategoryResult(
            "optimizer",
            0.4,
            f"{len(optimizers)} optimizer construction(s) were observed but no "
            "readable optimizer configuration value was found.",
        )
    return CategoryResult("optimizer", 0.0, "No optimizer was detected.")


def _stage_result(
    category: str, pipeline: PipelineDetection, stage_name: str, required: str
) -> CategoryResult:
    for stage in pipeline.stages:
        if stage.name != stage_name:
            continue
        if stage.status is PipelineStageStatus.detected:
            return CategoryResult(
                category, 1.0, f"{required} detected: {stage.reason}.", list(stage.evidence)
            )
        if stage.status is PipelineStageStatus.partial:
            return CategoryResult(
                category,
                0.5,
                f"{required} only partially detected: {stage.reason}.",
                list(stage.evidence),
            )
    return CategoryResult(category, 0.0, f"No {required} was detected.")


def _dependencies_result(structure: RepositoryStructure, dependencies: list[str]) -> CategoryResult:
    if not structure.dependency_manifests:
        return CategoryResult(
            "dependencies",
            0.0,
            "No dependency manifest (requirements.txt, pyproject.toml, ...) was found.",
        )
    manifest = structure.dependency_manifests[0]
    if not dependencies:
        return CategoryResult(
            "dependencies",
            0.6,
            f"{manifest} is present but no dependency names could be read statically.",
        )
    return CategoryResult(
        "dependencies",
        1.0,
        f"{manifest} declares {len(dependencies)} dependencies.",
    )


def _random_seed_result(
    parameters: dict[str, CodeParameter],
    structure: RepositoryStructure,
    source_index: SourceIndex | None,
) -> CategoryResult:
    seed = parameters.get("random_seed")
    if seed is not None:
        return CategoryResult(
            "random_seed",
            1.0,
            f"Fixed random seed {seed.value} detected in {seed.file}:{seed.line}.",
            _evidence_for_parameter(seed, source_index),
        )
    has_seeding = any(
        analysis.signals_named("seeding_call") or analysis.signals_named("seeding_function")
        for analysis in structure.analyses
    )
    if has_seeding:
        return CategoryResult(
            "random_seed",
            0.4,
            "A seeding routine is present but no fixed seed value was found.",
        )
    return CategoryResult("random_seed", 0.0, "No fixed random seed detected.")


def _consistency_result(mappings: list[ParameterMapping]) -> CategoryResult:
    compared = [
        mapping
        for mapping in mappings
        if mapping.paper_field in CONSISTENCY_KEYS and mapping.paper_value is not None
    ]
    if not compared:
        return CategoryResult(
            "paper_code_consistency",
            0.0,
            "The paper experiment does not state comparable parameters, so paper/code "
            "agreement cannot be assessed.",
        )
    matched = [m for m in compared if m.status is MappingStatus.matched]
    mismatched = [m for m in compared if m.status is MappingStatus.mismatched]
    uncertain = [m for m in compared if m.status is MappingStatus.uncertain]
    total = len(compared)
    score = (len(matched) - 0.5 * len(mismatched) - 0.5 * len(uncertain)) / total
    reason = (
        f"{len(matched)} of {total} paper parameters match the code; "
        f"{len(mismatched)} mismatch and {len(uncertain)} remain uncertain."
    )
    if mismatched:
        reason += " Mismatched fields: " + ", ".join(m.paper_field for m in mismatched) + "."
    return CategoryResult("paper_code_consistency", round(min(1.0, max(0.0, score)), 4), reason)


def build_items(
    structure: RepositoryStructure,
    parameters: list[CodeParameter],
    pipeline: PipelineDetection,
    optimizers: list[CodeOptimizer],
    dependencies: list[str],
    mappings: list[ParameterMapping],
    source_index: SourceIndex | None = None,
) -> list[ReadinessItem]:
    """Evaluate every readiness category from observed evidence only."""
    index = {parameter.name: parameter for parameter in parameters}

    dataset_result = _named_parameter_result(
        "dataset", index.get("dataset"), "dataset", source_index
    )
    if index.get("dataset") is None:
        dataset_result = _file_only_result(
            "dataset", structure, FileRole.dataset, "dataset loading code"
        )
    model_result = _named_parameter_result("model", index.get("model"), "model", source_index)
    if index.get("model") is None:
        model_result = _file_only_result(
            "model", structure, FileRole.model_definition, "model definition"
        )

    results: list[CategoryResult] = [
        _entry_point_result(structure),
        dataset_result,
        model_result,
        _training_parameters_result(index, source_index),
        _optimizer_result(index, optimizers, source_index),
        _stage_result("evaluation", pipeline, "evaluation", "evaluation"),
        _stage_result("metrics", pipeline, "metric_calculation", "metric calculation"),
        _dependencies_result(structure, dependencies),
        _random_seed_result(index, structure, source_index),
        _consistency_result(mappings),
    ]
    return [
        ReadinessItem(
            category=result.category,
            weight=CATEGORY_WEIGHTS[result.category],
            status=status_for_score(result.score),
            score=result.score,
            reason=result.reason,
            evidence=result.evidence,
        )
        for result in results
    ]


def _build_blockers_and_warnings(
    items: list[ReadinessItem],
) -> tuple[list[ReadinessBlocker], list[ReadinessWarning]]:
    blockers: list[ReadinessBlocker] = []
    warnings: list[ReadinessWarning] = []
    for item in items:
        label = CATEGORY_LABELS.get(item.category, item.category)
        if item.status is ReadinessCategoryStatus.missing:
            blockers.append(
                ReadinessBlocker(
                    category=item.category,
                    message=f"{label}: {item.reason}",
                    severity="high" if item.weight >= 10 else "medium",
                )
            )
        elif item.status in {
            ReadinessCategoryStatus.partial,
            ReadinessCategoryStatus.uncertain,
        }:
            warnings.append(
                ReadinessWarning(category=item.category, message=f"{label}: {item.reason}")
            )
    return blockers, warnings


def calculate_readiness(items: list[ReadinessItem]) -> ReadinessOutcome:
    """Compute overall score, status, blockers and warnings from category items.

    ``overall_score`` is exactly ``sum(weight * score)`` so the number can always
    be recomputed from the reported items.
    """
    by_category = {item.category: item for item in items}
    ordered = [by_category[category] for category in CATEGORY_ORDER if category in by_category]
    for item in ordered:
        if abs(item.weight - CATEGORY_WEIGHTS[item.category]) > 1e-9:  # pragma: no cover
            raise ValueError(f"Readiness weight mismatch for {item.category}.")

    overall = round(sum(item.weight * item.score for item in ordered), 2)
    blockers, warnings = _build_blockers_and_warnings(ordered)
    status = overall_status_for(overall)
    logger.info(
        "event=readiness_calculated score=%s status=%s blockers=%s warnings=%s",
        overall,
        status.value,
        len(blockers),
        len(warnings),
    )
    return ReadinessOutcome(
        items=ordered,
        overall_score=overall,
        status=status,
        blockers=blockers,
        warnings=warnings,
    )


def analyze_repository_readiness(
    structure: RepositoryStructure,
    parameters: list[CodeParameter],
    pipeline: PipelineDetection,
    optimizers: list[CodeOptimizer],
    dependencies: list[str],
    mappings: list[ParameterMapping],
    source_index: SourceIndex | None = None,
) -> ReadinessOutcome:
    items = build_items(
        structure,
        parameters,
        pipeline,
        optimizers,
        dependencies,
        mappings,
        source_index,
    )
    return calculate_readiness(items)
