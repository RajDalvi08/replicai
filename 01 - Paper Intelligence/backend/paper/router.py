from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.paper.exceptions import PaperProcessingError
from backend.paper.models import ExperimentRecord, Paper
from backend.paper.service import PaperAnalysisService

router = APIRouter()


@router.post("/paper/analyze")
async def analyze_paper(
    file: Annotated[UploadFile, File()],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    try:
        content = await file.read()
        service = PaperAnalysisService(db)
        return service.analyze_pdf(
            filename=file.filename or "paper.pdf",
            file_bytes=content,
            content_type=file.content_type,
        )
    except PaperProcessingError as exc:
        raise HTTPException(
            status_code=400, detail={"error": exc.code, "message": str(exc)}
        ) from exc
    except Exception as exc:  # pragma: no cover - safety fallback
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_ERROR",
                "message": "An unexpected error occurred.",
            },
        ) from exc


@router.get("/paper/{paper_id}")
def get_paper(paper_id: int, db: Annotated[Session, Depends(get_db)]) -> dict:
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if paper is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": "Paper not found."},
        )
    return {
        "paper_id": str(paper.id),
        "filename": paper.filename,
        "sha256": paper.sha256,
        "page_count": paper.page_count,
        "created_at": paper.created_at.isoformat(),
    }


@router.get("/paper/{paper_id}/experiments")
def get_experiments_for_paper(paper_id: int, db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if paper is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": "Paper not found."},
        )

    records = db.query(ExperimentRecord).filter(ExperimentRecord.paper_id == paper_id).all()
    output: list[dict] = []
    for record in records:
        output.append(
            {
                "experiment_id": str(record.id),
                "experiment_key": record.experiment_key,
                "title": record.title,
                "description": record.description,
                "extraction_confidence": record.extraction_confidence,
                "evidence": [
                    {
                        "field": evidence.field,
                        "value": evidence.value,
                        "page": evidence.page,
                        "source_type": evidence.source_type,
                        "source_label": evidence.source_label,
                        "quote": evidence.quote,
                        "confidence": evidence.confidence,
                    }
                    for evidence in record.evidences
                ],
            }
        )
    return output


@router.get("/experiment/{experiment_id}")
def get_experiment(experiment_id: int, db: Annotated[Session, Depends(get_db)]) -> dict:
    record = db.query(ExperimentRecord).filter(ExperimentRecord.id == experiment_id).first()
    if record is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": "Experiment not found."},
        )
    evidence = [
        {
            "field": item.field,
            "value": item.value,
            "page": item.page,
            "source_type": item.source_type,
            "source_label": item.source_label,
            "quote": item.quote,
            "confidence": item.confidence,
        }
        for item in record.evidences
    ]
    parameters = [
        {
            "field_name": item.field_name,
            "value": item.field_value,
            "value_type": item.value_type,
        }
        for item in record.parameters
    ]
    return {
        "experiment_id": str(record.id),
        "title": record.title,
        "description": record.description,
        "extraction_confidence": record.extraction_confidence,
        "parameters": parameters,
        "evidence": evidence,
    }
