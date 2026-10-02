"""Database access for the Code Intelligence module.

Thin persistence layer: it only converts between SQLAlchemy rows and the Pydantic
schemas defined in :mod:`backend.code.schemas`. No analysis logic lives here.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.code.models import (
    CodeEvidence,
    CodeFile,
    ExperimentCodeMapping,
    ReadinessItem,
    ReadinessReport,
    Repository,
)
from backend.code.schemas import (
    CodeAnalysisResponse,
    DetectedFile,
    OverallReadinessStatus,
    ParameterMapping,
    ReadinessReportSummary,
    RepositorySummary,
)
from backend.code.schemas import (
    CodeEvidence as CodeEvidenceSchema,
)
from backend.code.schemas import (
    ReadinessItem as ReadinessItemSchema,
)
from backend.code.utils import unique_preserving_order

logger = logging.getLogger("replicai.code.repository")


def persist_analysis(
    db: Session,
    *,
    url: str,
    normalized_url: str,
    owner: str,
    name: str,
    branch: str | None,
    commit_sha: str | None,
    total_bytes: int,
    file_count: int,
    python_file_count: int,
    paper_id: int | None,
    experiment_id: int,
    analysis: CodeAnalysisResponse,
) -> int:
    """Store the result of one repository analysis and return the repository id."""
    repository = Repository(
        paper_id=paper_id,
        experiment_id=experiment_id,
        url=url,
        normalized_url=normalized_url,
        owner=owner,
        name=name,
        branch=branch,
        commit_sha=commit_sha,
        status=analysis.repository.analysis_status.value,
        file_count=file_count,
        python_file_count=python_file_count,
        total_bytes=total_bytes,
        warnings=list(analysis.warnings),
    )
    db.add(repository)
    db.flush()

    file_ids: dict[str, int] = {}
    for detected in analysis.files:
        record = CodeFile(
            repository_id=repository.id,
            path=detected.path,
            file_type=detected.file_type,
            role=detected.role.value,
            confidence=detected.confidence,
            evidence=list(detected.evidence),
        )
        db.add(record)
        db.flush()
        file_ids[detected.path] = int(record.id)

    evidence_ids: dict[str, int] = {}

    def _store_evidence(
        evidence: CodeEvidenceSchema | None, evidence_type: str, symbol: str | None
    ) -> int | None:
        if evidence is None:
            return None
        record = CodeEvidence(
            repository_id=repository.id,
            code_file_id=file_ids.get(evidence.file),
            file_path=evidence.file,
            evidence_type=evidence_type,
            symbol=symbol,
            value=None,
            line_start=evidence.line_start,
            line_end=evidence.line_end,
            quote=evidence.quote,
            confidence=evidence.confidence,
            verified=1 if evidence.verified else 0,
        )
        db.add(record)
        db.flush()
        key = f"{evidence_type}:{symbol or ''}:{evidence.file}:{evidence.line_start}"
        evidence_ids.setdefault(key, int(record.id))
        return int(record.id)

    for parameter in analysis.code_parameters:
        _store_evidence(
            CodeEvidenceSchema(
                source_type="code",
                file=parameter.file or "",
                line_start=parameter.line,
                line_end=parameter.line,
                quote=parameter.quote,
                confidence=parameter.confidence,
            ),
            "parameter",
            parameter.name,
        )

    for stage in analysis.pipeline.stages:
        for evidence in stage.evidence:
            _store_evidence(evidence, "pipeline_stage", stage.name)

    for mapping in analysis.mappings:
        code_evidence_id = _store_evidence(mapping.evidence, "mapping", mapping.paper_field)
        db.add(
            ExperimentCodeMapping(
                experiment_id=experiment_id,
                repository_id=repository.id,
                paper_field=mapping.paper_field,
                paper_value=mapping.paper_value,
                code_field=mapping.code_field,
                code_value=mapping.code_value,
                status=mapping.status.value,
                confidence=mapping.confidence,
                reason=mapping.reason,
                code_evidence_id=code_evidence_id,
                paper_evidence=[item.model_dump(mode="json") for item in mapping.paper_evidence],
            )
        )

    report = ReadinessReport(
        experiment_id=experiment_id,
        repository_id=repository.id,
        overall_score=analysis.readiness.overall_score,
        status=analysis.readiness.status.value,
    )
    db.add(report)
    db.flush()
    for item in analysis.readiness.items:
        db.add(
            ReadinessItem(
                readiness_report_id=report.id,
                category=item.category,
                status=item.status.value,
                weight=item.weight,
                score=item.score,
                reason=item.reason,
                evidence=[evidence.model_dump(mode="json") for evidence in item.evidence],
            )
        )

    db.commit()
    logger.info(
        "event=analysis_persisted repository_id=%s experiment_id=%s",
        repository.id,
        experiment_id,
    )
    return int(repository.id)


# --------------------------------------------------------------------------- #
# Read helpers
# --------------------------------------------------------------------------- #
def get_repository(db: Session, repository_id: int) -> Repository | None:
    return db.get(Repository, repository_id)


def repository_summary(repository: Repository) -> RepositorySummary:
    return RepositorySummary(
        id=str(repository.id),
        url=str(repository.url),
        normalized_url=str(repository.normalized_url),
        owner=str(repository.owner),
        name=str(repository.name),
        branch=str(repository.branch) if repository.branch else None,
        commit_sha=str(repository.commit_sha) if repository.commit_sha else None,
        analyzed_at=repository.analyzed_at.isoformat() if repository.analyzed_at else "",
        file_count=int(repository.file_count or 0),
        python_file_count=int(repository.python_file_count or 0),
        analysis_status=repository.status,  # type: ignore[arg-type]
        warnings=list(repository.warnings or []),
    )


def repository_files(db: Session, repository_id: int) -> list[DetectedFile]:
    rows = (
        db.query(CodeFile)
        .filter(CodeFile.repository_id == repository_id)
        .order_by(CodeFile.path)
        .all()
    )
    return [
        DetectedFile(
            path=row.path,  # type: ignore[arg-type]
            file_type=row.file_type or "other",  # type: ignore[arg-type]
            role=row.role,  # type: ignore[arg-type]
            confidence=row.confidence or 0.0,  # type: ignore[arg-type]
            evidence=list(row.evidence or []),
        )
        for row in rows
    ]


def repository_entry_points(db: Session, repository_id: int) -> list[DetectedFile]:
    return [
        item
        for item in repository_files(db, repository_id)
        if item.role.value
        in {"training_entrypoint", "evaluation_entrypoint", "inference_entrypoint"}
    ]


def _evidence_schema(row: CodeEvidence) -> CodeEvidenceSchema:
    return CodeEvidenceSchema(
        source_type="code",
        file=row.file_path,  # type: ignore[arg-type]
        line_start=row.line_start,  # type: ignore[arg-type]
        line_end=row.line_end,  # type: ignore[arg-type]
        quote=row.quote,  # type: ignore[arg-type]
        confidence=row.confidence or 0.0,  # type: ignore[arg-type]
        verified=bool(row.verified),
    )


def repository_mappings(
    db: Session, repository_id: int, experiment_id: int | None = None
) -> list[ParameterMapping]:
    query = db.query(ExperimentCodeMapping).filter(
        ExperimentCodeMapping.repository_id == repository_id
    )
    if experiment_id is not None:
        query = query.filter(ExperimentCodeMapping.experiment_id == experiment_id)
    rows = query.order_by(ExperimentCodeMapping.paper_field).all()
    mappings: list[ParameterMapping] = []
    for row in rows:
        evidence = row.code_evidence
        mappings.append(
            ParameterMapping(
                paper_field=row.paper_field,  # type: ignore[arg-type]
                paper_value=row.paper_value,
                code_field=row.code_field,  # type: ignore[arg-type]
                code_value=row.code_value,
                status=row.status,  # type: ignore[arg-type]
                confidence=row.confidence or 0.0,  # type: ignore[arg-type]
                reason=row.reason or "",  # type: ignore[arg-type]
                evidence=_evidence_schema(evidence) if evidence is not None else None,
                paper_evidence=list(row.paper_evidence or []),
            )
        )
    return mappings


def latest_readiness_report(
    db: Session, repository_id: int, experiment_id: int | None = None
) -> ReadinessReport | None:
    query = db.query(ReadinessReport).filter(ReadinessReport.repository_id == repository_id)
    if experiment_id is not None:
        query = query.filter(ReadinessReport.experiment_id == experiment_id)
    return query.order_by(ReadinessReport.id.desc()).first()


def readiness_report_summary(report: ReadinessReport) -> ReadinessReportSummary:
    items: list[ReadinessItemSchema] = []
    for item in report.items:
        items.append(
            ReadinessItemSchema(
                category=item.category,  # type: ignore[arg-type]
                weight=item.weight or 0.0,  # type: ignore[arg-type]
                status=item.status,  # type: ignore[arg-type]
                score=item.score or 0.0,  # type: ignore[arg-type]
                reason=item.reason or "",  # type: ignore[arg-type]
                evidence=[
                    CodeEvidenceSchema.model_validate(entry) for entry in item.evidence or []
                ],
            )
        )
    items.sort(key=lambda entry: _category_order(entry.category))

    from backend.code.readiness import _build_blockers_and_warnings

    blockers, warnings = _build_blockers_and_warnings(items)
    return ReadinessReportSummary(
        id=str(report.id),
        overall_score=report.overall_score or 0.0,  # type: ignore[arg-type]
        status=OverallReadinessStatus(report.status),  # type: ignore[arg-type]
        generated_at=report.generated_at.isoformat() if report.generated_at else "",
        items=items,
        blockers=blockers,
        warnings=warnings,
    )


def _category_order(category: str) -> int:
    from backend.code.readiness import CATEGORY_ORDER

    try:
        return CATEGORY_ORDER.index(category)
    except ValueError:  # pragma: no cover - defensive
        return len(CATEGORY_ORDER)


def repositories_for_experiment(db: Session, experiment_id: int) -> list[Repository]:
    statement = (
        select(Repository)
        .where(Repository.experiment_id == experiment_id)
        .order_by(Repository.id.desc())
    )
    return list(db.execute(statement).scalars().all())


def entry_point_paths(files: list[DetectedFile]) -> list[str]:
    return unique_preserving_order(
        item.path
        for item in files
        if item.role.value
        in {"training_entrypoint", "evaluation_entrypoint", "inference_entrypoint"}
    )
