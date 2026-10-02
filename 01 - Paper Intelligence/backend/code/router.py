"""FastAPI routes for the Code Intelligence module (Part 2)."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.code.exceptions import CodeIntelligenceError
from backend.code.schemas import (
    CodeAnalysisResponse,
    CodeAnalyzeRequest,
    RepositoryDetailResponse,
    RepositoryFilesResponse,
    RepositoryMappingsResponse,
    RepositoryReadinessResponse,
)
from backend.code.service import CodeAnalysisService
from backend.database import get_db

logger = logging.getLogger("replicai.code.router")

router = APIRouter(tags=["code-intelligence"])


def _to_http_exception(exc: CodeIntelligenceError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"error": exc.code, "message": str(exc)},
    )


@router.post("/code/analyze", response_model=CodeAnalysisResponse)
def analyze_repository_code(
    request: CodeAnalyzeRequest,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Statically analyze a GitHub repository against a Part 1 experiment."""
    try:
        return CodeAnalysisService(db).analyze(request)
    except CodeIntelligenceError as exc:
        logger.warning("event=code_analysis_rejected error=%s", exc.code)
        raise _to_http_exception(exc) from exc
    except Exception as exc:
        logger.exception("event=code_analysis_failed")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_ERROR",
                "message": "An unexpected error occurred while analyzing the repository.",
            },
        ) from exc


@router.get("/repository/{repository_id}", response_model=RepositoryDetailResponse)
def get_repository(repository_id: int, db: Annotated[Session, Depends(get_db)]) -> dict:
    try:
        return CodeAnalysisService(db).get_repository(repository_id)
    except CodeIntelligenceError as exc:
        raise _to_http_exception(exc) from exc


@router.get("/repository/{repository_id}/files", response_model=RepositoryFilesResponse)
def get_repository_files(repository_id: int, db: Annotated[Session, Depends(get_db)]) -> dict:
    try:
        return CodeAnalysisService(db).get_files(repository_id)
    except CodeIntelligenceError as exc:
        raise _to_http_exception(exc) from exc


@router.get("/repository/{repository_id}/mappings", response_model=RepositoryMappingsResponse)
def get_repository_mappings(
    repository_id: int,
    db: Annotated[Session, Depends(get_db)],
    experiment_id: Annotated[int | None, Query()] = None,
) -> dict:
    try:
        return CodeAnalysisService(db).get_mappings(repository_id, experiment_id)
    except CodeIntelligenceError as exc:
        raise _to_http_exception(exc) from exc


@router.get("/repository/{repository_id}/readiness", response_model=RepositoryReadinessResponse)
def get_repository_readiness(
    repository_id: int,
    db: Annotated[Session, Depends(get_db)],
    experiment_id: Annotated[int | None, Query()] = None,
) -> dict:
    try:
        return CodeAnalysisService(db).get_readiness(repository_id, experiment_id)
    except CodeIntelligenceError as exc:
        raise _to_http_exception(exc) from exc


@router.get("/experiment/{experiment_id}/code-analysis")
def get_experiment_code_analysis(
    experiment_id: int, db: Annotated[Session, Depends(get_db)]
) -> dict:
    """Combine a Part 1 experiment with its latest repository analysis."""
    try:
        return CodeAnalysisService(db).get_experiment_code_analysis(experiment_id)
    except CodeIntelligenceError as exc:
        raise _to_http_exception(exc) from exc
