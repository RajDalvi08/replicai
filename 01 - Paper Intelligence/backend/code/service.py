"""Orchestration service for the Code Intelligence module.

Flow for ``POST /api/v1/code/analyze``:

1. validate and normalize the repository URL,
2. load the Part 1 experiment (the expected specification),
3. clone the repository into a temporary directory (never executing its code),
4. classify repository structure,
5. statically analyze Python files with ``ast``,
6. normalize detected values onto the Part 1 parameter vocabulary,
7. reconstruct the training pipeline,
8. map paper parameters onto code parameters,
9. verify every code quote against the analyzed source,
10. compute the deterministic readiness score,
11. persist results and return the JSON response.

The temporary checkout is always removed, including on failure.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from backend.code import repository as repository_store
from backend.code.analyzer import analyze_structure, parse_dependencies
from backend.code.config import settings
from backend.code.evidence import SourceIndex
from backend.code.exceptions import (
    CodeAnalysisTimeoutError,
    ExperimentNotFoundError,
    RepositoryAnalysisError,
    RepositoryNotFoundError,
    RepositoryValidationError,
)
from backend.code.ingestion import RepositoryIngestor, RepositoryWorkspace
from backend.code.llm import CodeLLMAdapter, merge_llm_role_suggestions
from backend.code.mapper import PaperCodeMapper
from backend.code.models import Repository
from backend.code.parameters import ParameterExtractor
from backend.code.pipeline import detect_pipeline
from backend.code.python_analysis import (
    PythonFileAnalysis,
    analyze_python_file,
    enforce_analysis_deadline,
    is_python_file,
)
from backend.code.readiness import analyze_repository_readiness
from backend.code.schemas import (
    CodeAnalysisResponse,
    CodeAnalyzeRequest,
    DetectedFile,
    FileRole,
    MappingStatus,
    PaperEvidenceRef,
    ParameterMapping,
    ReadinessReportSummary,
    RepositoryAnalysisStatus,
    RepositoryDetailResponse,
    RepositoryFilesResponse,
    RepositoryMappingsResponse,
    RepositoryReadinessResponse,
    RepositorySummary,
)
from backend.code.utils import (
    NormalizedRepository,
    collect_repository_files,
    normalize_repository_url,
)
from backend.paper.models import ExperimentRecord, Paper

logger = logging.getLogger("replicai.code.service")

#: Part 1 experiment fields compared against the code.
PAPER_PARAMETER_FIELDS: tuple[str, ...] = (
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


class CodeAnalysisService:
    def __init__(self, db: Session, ingestor: RepositoryIngestor | None = None) -> None:
        self.db = db
        self._ingestor = ingestor

    def ingestor(self) -> RepositoryIngestor:
        if self._ingestor is None:
            self._ingestor = RepositoryIngestor()
        return self._ingestor

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def analyze(self, request: CodeAnalyzeRequest) -> dict[str, Any]:
        started_at = time.monotonic()
        logger.info(
            "event=code_analysis_started experiment_id=%s",
            request.experiment_id,
        )
        target = normalize_repository_url(request.repository_url, request.branch)
        experiment_record, paper_id = self._load_experiment(request.experiment_id)
        paper_parameters, paper_evidence = self._paper_specification(experiment_record)

        workspace = self.ingestor().analyze(request.repository_url, request.branch)
        try:
            response = self._analyze_workspace(
                workspace,
                target,
                experiment_record=experiment_record,
                paper_id=paper_id,
                paper_parameters=paper_parameters,
                paper_evidence=paper_evidence,
                started_at=started_at,
            )
        finally:
            workspace.cleanup()
        logger.info(
            "event=code_analysis_completed experiment_id=%s repository=%s score=%s",
            request.experiment_id,
            target.full_name,
            response.readiness.overall_score,
        )
        return response.model_dump(mode="json")

    def get_repository(self, repository_id: int) -> dict[str, Any]:
        repository = self._require_repository(repository_id)
        summary = repository_store.repository_summary(repository)
        files = repository_store.repository_files(self.db, repository_id)
        entry_points = [item for item in files if item.role in self._ENTRY_POINT_ROLES]
        detail = RepositoryDetailResponse(
            **summary.model_dump(),
            entry_points=entry_points,
        )
        return detail.model_dump(mode="json")

    def get_files(self, repository_id: int) -> dict[str, Any]:
        self._require_repository(repository_id)
        files = repository_store.repository_files(self.db, repository_id)
        return RepositoryFilesResponse(
            repository_id=str(repository_id),
            total=len(files),
            files=files,
        ).model_dump(mode="json")

    def get_mappings(self, repository_id: int, experiment_id: int | None = None) -> dict[str, Any]:
        self._require_repository(repository_id)
        mappings = repository_store.repository_mappings(self.db, repository_id, experiment_id)
        return RepositoryMappingsResponse(
            repository_id=str(repository_id),
            experiment_id=str(experiment_id) if experiment_id is not None else None,
            total=len(mappings),
            mappings=mappings,
        ).model_dump(mode="json")

    def get_readiness(self, repository_id: int, experiment_id: int | None = None) -> dict[str, Any]:
        self._require_repository(repository_id)
        report = repository_store.latest_readiness_report(self.db, repository_id, experiment_id)
        if report is None:
            raise RepositoryNotFoundError("No readiness report exists for this repository.")
        return RepositoryReadinessResponse(
            repository_id=str(repository_id),
            experiment_id=str(report.experiment_id),
            readiness=repository_store.readiness_report_summary(report),
        ).model_dump(mode="json")

    def get_experiment_code_analysis(self, experiment_id: int) -> dict[str, Any]:
        """Combine the Part 1 experiment with its latest repository analysis."""
        experiment_record, paper_id = self._load_experiment(str(experiment_id))
        repositories = repository_store.repositories_for_experiment(self.db, experiment_id)
        if not repositories:
            raise RepositoryNotFoundError("No code analysis exists for this experiment yet.")
        repository = repositories[0]
        return {
            "experiment_id": str(experiment_id),
            "paper_id": str(paper_id) if paper_id is not None else None,
            "experiment": {
                "title": experiment_record.title,
                "description": experiment_record.description,
                "extraction_confidence": experiment_record.extraction_confidence,
            },
            "repository": repository_store.repository_summary(repository).model_dump(mode="json"),
            "entry_points": [
                item.model_dump(mode="json")
                for item in repository_store.repository_entry_points(self.db, int(repository.id))
            ],
            "mappings": self.get_mappings(int(repository.id), experiment_id)["mappings"],
            "readiness": self.get_readiness(int(repository.id), experiment_id)["readiness"],
        }

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    _ENTRY_POINT_ROLES = frozenset(
        {
            FileRole.training_entrypoint,
            FileRole.evaluation_entrypoint,
            FileRole.inference_entrypoint,
        }
    )

    def _require_repository(self, repository_id: int) -> Repository:
        repository = repository_store.get_repository(self.db, repository_id)
        if repository is None:
            raise RepositoryNotFoundError("Repository analysis not found.")
        return repository

    def _load_experiment(self, experiment_id: str) -> tuple[ExperimentRecord, int | None]:
        """Load experiment by numeric ID or experiment_key."""
        record = None
        # Try numeric ID first
        try:
            numeric_id = int(experiment_id)
            record = (
                self.db.query(ExperimentRecord).filter(ExperimentRecord.id == numeric_id).first()
            )
        except (TypeError, ValueError):
            pass
        # Fall back to experiment_key lookup
        if record is None:
            record = (
                self.db.query(ExperimentRecord)
                .filter(ExperimentRecord.experiment_key == experiment_id)
                .first()
            )
        if record is None:
            raise ExperimentNotFoundError(
                "The referenced experiment does not exist. Analyze a paper first."
            )
        return record, int(record.paper_id)

    def _paper_specification(
        self, experiment_record: ExperimentRecord
    ) -> tuple[dict[str, Any], dict[str, list[PaperEvidenceRef]]]:
        """Read the Part 1 experiment as the expected specification."""
        parameters: dict[str, Any] = {}
        for item in experiment_record.parameters:
            if item.field_name in PAPER_PARAMETER_FIELDS:
                parameters[item.field_name] = item.field_value

        evidence: dict[str, list[PaperEvidenceRef]] = {}
        for item in experiment_record.evidences:
            reference = PaperEvidenceRef(
                page=item.page,
                quote=item.quote,
                source_type=item.source_type,
                source_label=item.source_label,
                confidence=item.confidence,
            )
            evidence.setdefault(item.field, []).append(reference)
        return parameters, evidence

    def _analyze_python_sources(
        self, files: list[Any], started_at: float
    ) -> list[PythonFileAnalysis]:
        python_files = [item for item in files if is_python_file(item)]
        if len(python_files) > settings.max_python_file_count:
            raise RepositoryAnalysisError(
                "Repository contains more Python files than the analysis limit."
            )
        analyses: list[PythonFileAnalysis] = []
        for repository_file in python_files:
            enforce_analysis_deadline(started_at)
            analysis = analyze_python_file(repository_file)
            if analysis is None:
                continue
            analyses.append(analysis)
        return analyses

    def _analyze_workspace(
        self,
        workspace: RepositoryWorkspace,
        target: NormalizedRepository,
        *,
        experiment_record: ExperimentRecord,
        paper_id: int | None,
        paper_parameters: dict[str, Any],
        paper_evidence: dict[str, list[PaperEvidenceRef]],
        started_at: float,
    ) -> CodeAnalysisResponse:
        root = workspace.root
        source_index = SourceIndex(root)
        warnings: list[str] = []

        files = collect_repository_files(root)
        analyses = self._analyze_python_sources(files, started_at)
        structure = analyze_structure(root, files, analyses)
        logger.info(
            "event=files_analyzed total=%s python=%s skipped=%s",
            len(structure.files),
            structure.python_file_count,
            len(structure.parse_failures),
        )
        if structure.parse_failures:
            warnings.append(
                "Some Python files could not be parsed: "
                + ", ".join(sorted(structure.parse_failures)[:5])
            )

        detected = self._apply_optional_llm(structure.detected)
        structure.detected = detected
        entry_points = [item for item in detected if item.role in self._ENTRY_POINT_ROLES]
        entry_points.sort(key=lambda item: (-item.confidence, item.path))
        logger.info("event=entry_points_detected count=%s", len(entry_points))

        extractor = ParameterExtractor(analyses)
        code_parameters = extractor.extract()
        candidates = extractor.candidates_by_name()
        optimizers = extractor.optimizers()
        schedulers = extractor.schedulers()
        loss_functions = extractor.loss_functions()
        metrics = extractor.metrics()
        logger.info(
            "event=parameters_detected count=%s optimizers=%s schedulers=%s",
            len(code_parameters),
            len(optimizers),
            len(schedulers),
        )

        pipeline = detect_pipeline(analyses, source_index)
        dependencies = parse_dependencies(root, structure.dependency_manifests)

        mapper = PaperCodeMapper(paper_parameters, candidates, source_index, paper_evidence)
        mappings = mapper.map_all()
        self._apply_paper_confidence(
            mappings, float(experiment_record.extraction_confidence or 0.0)
        )

        outcome = analyze_repository_readiness(
            structure,
            code_parameters,
            pipeline,
            optimizers,
            dependencies,
            mappings,
            source_index,
        )

        if not any(item.status.value == "ready" for item in outcome.items):
            warnings.append(
                "No readiness category reached 'ready'; the repository does not "
                "appear to be specified enough for an execution attempt."
            )

        repository_summary = RepositorySummary(
            id="pending",
            url=target.normalized_url,
            normalized_url=target.normalized_url,
            owner=target.owner,
            name=target.name,
            branch=workspace.ingested.branch,
            commit_sha=workspace.ingested.commit_sha,
            analyzed_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
            file_count=len(structure.files),
            python_file_count=structure.python_file_count,
            analysis_status=(
                RepositoryAnalysisStatus.analyzed
                if not structure.parse_failures
                else RepositoryAnalysisStatus.partial
            ),
            warnings=list(warnings),
        )

        response = CodeAnalysisResponse(
            repository=repository_summary,
            experiment_id=str(experiment_record.id),
            paper_id=str(paper_id) if paper_id is not None else None,
            entry_points=entry_points,
            files=detected,
            code_parameters=code_parameters,
            optimizers=optimizers,
            schedulers=schedulers,
            loss_functions=loss_functions,
            metrics=metrics,
            dependencies=dependencies,
            pipeline=pipeline,
            mappings=mappings,
            readiness=ReadinessReportSummary(
                id="pending",
                overall_score=outcome.overall_score,
                status=outcome.status,
                generated_at=repository_summary.analyzed_at,
                items=outcome.items,
                blockers=outcome.blockers,
                warnings=outcome.warnings,
            ),
            warnings=warnings,
        )

        repository_id = repository_store.persist_analysis(
            self.db,
            url=target.normalized_url,
            normalized_url=target.normalized_url,
            owner=target.owner,
            name=target.name,
            branch=workspace.ingested.branch,
            commit_sha=workspace.ingested.commit_sha,
            total_bytes=workspace.ingested.total_bytes,
            file_count=len(structure.files),
            python_file_count=structure.python_file_count,
            paper_id=paper_id,
            experiment_id=int(experiment_record.id),
            analysis=response,
        )
        response.repository.id = str(repository_id)
        response.readiness.id = str(repository_id)
        return response

    def _apply_optional_llm(self, detected: list[DetectedFile]) -> list[DetectedFile]:
        """Optionally label weakly classified files. Static results always win."""
        adapter = CodeLLMAdapter()
        if not adapter.is_configured():
            return detected
        try:
            suggestions = adapter.suggest_roles(detected)
        except CodeAnalysisTimeoutError:  # pragma: no cover - defensive
            return detected
        except Exception as exc:  # noqa: BLE001 - LLM is optional
            logger.info("event=llm_role_classification_failed reason=%s", type(exc).__name__)
            return detected
        return merge_llm_role_suggestions(detected, suggestions)

    def _apply_paper_confidence(
        self, mappings: list[ParameterMapping], paper_confidence: float
    ) -> None:
        """Discount decisions that depend on a weakly extracted paper value.

        A match is only as trustworthy as the paper value it was compared with,
        so the Part 1 extraction confidence scales matched/mismatched decisions.
        This is deterministic and never changes a status.
        """
        factor = round(0.75 + 0.25 * max(0.0, min(1.0, paper_confidence)), 4)
        if factor >= 1.0:
            return
        for mapping in mappings:
            if mapping.status in {MappingStatus.matched, MappingStatus.mismatched}:
                mapping.confidence = round(mapping.confidence * factor, 4)


def ensure_paper_exists(db: Session, paper_id: str | None) -> int | None:
    """Resolve an optional Part 1 paper id, rejecting unknown papers."""
    if paper_id is None:
        return None
    try:
        numeric_id = int(paper_id)
    except (TypeError, ValueError) as exc:
        raise RepositoryValidationError("paper_id must be numeric.") from exc
    paper = db.query(Paper).filter(Paper.id == numeric_id).first()
    if paper is None:
        raise RepositoryValidationError("The referenced paper does not exist.")
    return numeric_id
