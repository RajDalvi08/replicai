from __future__ import annotations

from typing import Any

import fitz  # type: ignore[import-untyped]
from sqlalchemy.orm import Session

from backend.config import settings
from backend.paper.evidence import validate_evidence
from backend.paper.exceptions import InvalidPDFError, LLMExtractionError
from backend.paper.experiment_extractor import build_experiment_payload
from backend.paper.extractor import extract_pdf_pages
from backend.paper.llm import StructuredLLMAdapter
from backend.paper.models import (
    EvidenceRecord,
    ExperimentParameter,
    ExperimentRecord,
    Paper,
)
from backend.paper.schemas import Experiment
from backend.paper.utils import compute_sha256, sanitize_filename


class PaperAnalysisService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _validate_upload(
        self, filename: str | None, content_type: str | None, file_bytes: bytes
    ) -> str:
        if not filename:
            raise InvalidPDFError("Uploaded file is missing a filename.")

        sanitized = sanitize_filename(filename)
        if not sanitized.lower().endswith(".pdf"):
            raise InvalidPDFError("Uploaded file is not a valid PDF.")

        if content_type and content_type.lower() not in {
            "application/pdf",
            "application/octet-stream",
        }:
            raise InvalidPDFError("Uploaded file is not a valid PDF.")

        if len(file_bytes) == 0:
            raise InvalidPDFError("Uploaded file is empty.")

        if len(file_bytes) > settings.max_upload_bytes:
            raise InvalidPDFError(
                f"Uploaded file exceeds the {settings.max_upload_bytes} byte limit."
            )

        try:
            document = fitz.open(stream=file_bytes, filetype="pdf")
            document.close()
        except Exception as exc:  # pragma: no cover - malformed PDF guard
            raise InvalidPDFError("Uploaded file is not a valid PDF.") from exc

        return sanitized

    def _score_experiment(self, experiment: Experiment, page_count: int) -> float:
        schema_quality = 1.0
        evidence_coverage = 1.0 if experiment.evidence else 0.4
        evidence_verification = 1.0
        for evidence in experiment.evidence:
            if evidence.page is None or evidence.page > page_count or evidence.page < 1:
                evidence_verification *= 0.75
        llm_confidence = float(experiment.extraction_confidence)
        missing_critical_fields = sum(
            1
            for field_name in [
                "dataset",
                "model",
                "optimizer",
                "learning_rate",
                "batch_size",
                "epochs",
                "metric",
            ]
            if getattr(experiment, field_name) is None
        )
        missing_penalty = min(missing_critical_fields / 7.0, 0.9)
        evidence_coverage = max(0.0, evidence_coverage - missing_penalty * 0.4)
        confidence = (
            0.30 * schema_quality
            + 0.30 * evidence_coverage
            + 0.25 * evidence_verification
            + 0.15 * llm_confidence
        )
        return round(max(0.0, min(1.0, confidence)), 4)

    def analyze_pdf(
        self, filename: str, file_bytes: bytes, content_type: str | None = None
    ) -> dict[str, Any]:
        safe_name = self._validate_upload(filename, content_type, file_bytes)
        page_count = 0
        page_texts: dict[int, str] = {}
        warnings: list[str] = []
        pages = extract_pdf_pages(file_bytes)
        page_count = len(pages)
        for page in pages:
            page_texts[page["page"]] = page.get("text", "")
            warnings.extend(page.get("warnings", []))

        llm_adapter = StructuredLLMAdapter()
        if llm_adapter.is_configured():
            try:
                llm_experiments = llm_adapter.extract_experiments(pages)
            except (LLMExtractionError, TypeError, ValueError):
                llm_experiments = []
        else:
            llm_experiments = []

        experiment_payloads = llm_experiments or build_experiment_payload(pages)
        validated_experiments: list[Experiment] = []
        for experiment_payload in experiment_payloads:
            parsed_model = Experiment.model_validate(experiment_payload)
            for item in parsed_model.evidence:
                result = validate_evidence(
                    item.model_dump(mode="json"), page_count, page_texts
                )
                if not result["valid"]:
                    parsed_model.warnings.extend(result["issues"])
            parsed_model.extraction_confidence = self._score_experiment(
                parsed_model, page_count
            )
            validated_experiments.append(parsed_model)

        paper_record = Paper(
            filename=safe_name,
            sha256=compute_sha256(file_bytes),
            page_count=page_count,
        )
        self.db.add(paper_record)
        self.db.flush()

        persisted_experiments: list[dict[str, Any]] = []
        for index, experiment in enumerate(validated_experiments, start=1):
            experiment_record = ExperimentRecord(
                paper_id=paper_record.id,
                experiment_key=f"exp-{paper_record.id}-{index}",
                title=experiment.title,
                description=experiment.description,
                extraction_confidence=experiment.extraction_confidence,
            )
            self.db.add(experiment_record)
            self.db.flush()

            serialized_experiment: dict[str, Any] = experiment.model_dump(mode="json")
            for field_name in [
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
            ]:
                value = serialized_experiment.get(field_name)
                if value is None:
                    continue
                self.db.add(
                    ExperimentParameter(
                        experiment_id=experiment_record.id,
                        field_name=field_name,
                        field_value=value,
                        value_type=type(value).__name__,
                    )
                )

            for evidence in experiment.evidence:
                evidence_payload = evidence.model_dump(mode="json")
                self.db.add(
                    EvidenceRecord(
                        experiment_id=experiment_record.id,
                        field=evidence_payload.get("field", "unknown"),
                        value=evidence_payload.get("value"),
                        page=evidence_payload.get("page"),
                        source_type=evidence_payload.get("source_type"),
                        source_label=evidence_payload.get("source_label"),
                        quote=evidence_payload.get("quote"),
                        confidence=evidence_payload.get("confidence"),
                    )
                )

            persisted_experiments.append(serialized_experiment)

        self.db.commit()

        return {
            "paper_id": str(paper_record.id),
            "filename": safe_name,
            "page_count": page_count,
            "experiments": persisted_experiments,
            "warnings": warnings,
        }
