"""Tests for the Code Intelligence module - paper to code mapping."""

from pathlib import Path

from backend.code.evidence import SourceIndex
from backend.code.mapper import PaperCodeMapper
from backend.code.parameters import ParameterCandidate, ParameterExtractor
from backend.code.python_analysis import analyze_python_file, is_python_file
from backend.code.schemas import (
    MappingStatus,
    PaperEvidenceRef,
)
from backend.code.utils import collect_repository_files


class TestPaperCodeMapping:
    def test_mapping_all_matched(self, sample_repo_path: Path):
        """All parameters from the expected JSON should match."""
        files = collect_repository_files(sample_repo_path)
        from backend.code.python_analysis import is_python_file

        python_files = [f for f in files if is_python_file(f)]
        analyses = [analyze_python_file(f) for f in python_files]
        analyses = [a for a in analyses if a]
        extractor = ParameterExtractor(analyses)
        candidates = extractor.candidates_by_name()
        source_index = SourceIndex(sample_repo_path)

        # Paper parameters from the fixture
        paper_params = {
            "dataset": "synthetic-toy-corpus",
            "model": "EncoderClassifier",
            "optimizer": "AdamW",
            "learning_rate": 0.001,
            "batch_size": 64,
            "epochs": 10,
            "scheduler": "cosine",
            "weight_decay": 0.01,
            "dropout": 0.1,
            "random_seed": 42,
            "metric": "accuracy",
            "loss_function": "CrossEntropyLoss",
        }
        paper_evidence = {
            "learning_rate": [PaperEvidenceRef(page=1, quote="lr = 0.001")],
            "batch_size": [PaperEvidenceRef(page=1, quote="batch_size = 64")],
        }

        mapper = PaperCodeMapper(paper_params, candidates, source_index, paper_evidence)
        mappings = mapper.map_all()

        statuses = {m.paper_field: m.status for m in mappings}

        # All should match
        for field in [
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
            "loss_function",
        ]:
            assert statuses.get(field) == MappingStatus.matched, f"{field}: {statuses.get(field)}"

        # Check specific confidences
        lr_mapping = next(m for m in mappings if m.paper_field == "learning_rate")
        assert lr_mapping.confidence >= 0.9
        assert lr_mapping.evidence is not None
        assert lr_mapping.evidence.verified is True

        # Scheduler: paper says "cosine", code says "CosineAnnealingLR" -> matched via token
        sched_mapping = next(m for m in mappings if m.paper_field == "scheduler")
        assert sched_mapping.status == MappingStatus.matched

    def test_mapping_mismatched(self):
        """Test that numeric differences are flagged as mismatched."""
        candidates = {
            "learning_rate": [
                ParameterCandidate(
                    name="learning_rate",
                    value=0.01,
                    file="train.py",
                    line=10,
                    quote="lr = 0.01",
                    origin="assignment",
                    confidence=0.9,
                )
            ]
        }
        paper_params = {"learning_rate": 0.001}
        source_index = SourceIndex(Path("."))

        mapper = PaperCodeMapper(paper_params, candidates, source_index)
        mappings = mapper.map_all()
        lr_mapping = next(m for m in mappings if m.paper_field == "learning_rate")

        assert lr_mapping.status == MappingStatus.mismatched
        assert lr_mapping.code_value == 0.01
        assert "differ" in lr_mapping.reason.lower()

    def test_mapping_missing_in_code(self):
        """Test that paper params with no code value are missing_in_code."""
        candidates = {}  # no code candidates
        paper_params = {"learning_rate": 0.001}
        source_index = SourceIndex(Path("."))

        mapper = PaperCodeMapper(paper_params, candidates, source_index)
        mappings = mapper.map_all()
        lr_mapping = next(m for m in mappings if m.paper_field == "learning_rate")

        assert lr_mapping.status == MappingStatus.missing_in_code
        assert lr_mapping.code_value is None

    def test_mapping_missing_in_paper(self):
        """Test that code params with no paper value are missing_in_paper."""
        candidates = {
            "dropout": [
                ParameterCandidate(
                    name="dropout",
                    value=0.2,
                    file="train.py",
                    line=5,
                    quote="dropout = 0.2",
                    origin="assignment",
                    confidence=0.9,
                )
            ]
        }
        paper_params = {}  # paper doesn't mention dropout
        source_index = SourceIndex(Path("."))

        mapper = PaperCodeMapper(paper_params, candidates, source_index)
        mappings = mapper.map_all()
        dropout_mapping = next(m for m in mappings if m.paper_field == "dropout")

        assert dropout_mapping.status == MappingStatus.missing_in_paper
        assert dropout_mapping.code_value == 0.2

    def test_mapping_conflicting_candidates(self):
        """Test that conflicting code values produce uncertain."""
        candidates = {
            "learning_rate": [
                ParameterCandidate(
                    name="learning_rate",
                    value=0.001,
                    file="config.py",
                    line=10,
                    quote="lr = 0.001",
                    origin="dict_key",
                    confidence=0.92,
                ),
                ParameterCandidate(
                    name="learning_rate",
                    value=0.01,
                    file="train.py",
                    line=20,
                    quote="lr = 0.01",
                    origin="assignment",
                    confidence=0.9,
                ),
            ]
        }
        paper_params = {"learning_rate": 0.001}
        source_index = SourceIndex(Path("."))

        mapper = PaperCodeMapper(paper_params, candidates, source_index)
        mappings = mapper.map_all()
        lr_mapping = next(m for m in mappings if m.paper_field == "learning_rate")

        assert lr_mapping.status == MappingStatus.uncertain
        assert len(lr_mapping.conflicting_evidence) >= 1

    def test_mapping_textual_aliases(self):
        """Test scheduler 'cosine' matches 'CosineAnnealingLR'."""
        candidates = {
            "scheduler": [
                ParameterCandidate(
                    name="scheduler",
                    value="CosineAnnealingLR",
                    file="train.py",
                    line=10,
                    quote="CosineAnnealingLR",
                    origin="scheduler_call",
                    confidence=0.95,
                )
            ]
        }
        paper_params = {"scheduler": "cosine"}
        source_index = SourceIndex(Path("."))

        mapper = PaperCodeMapper(paper_params, candidates, source_index)
        mappings = mapper.map_all()
        sched_mapping = next(m for m in mappings if m.paper_field == "scheduler")

        assert sched_mapping.status == MappingStatus.matched

    def test_mapping_evidence_verification(self, sample_repo_path: Path):
        """Test that evidence quotes are verified against source."""
        files = collect_repository_files(sample_repo_path)
        python_files = [f for f in files if is_python_file(f)]
        analyses = [analyze_python_file(f) for f in python_files]
        analyses = [a for a in analyses if a]
        extractor = ParameterExtractor(analyses)
        candidates = extractor.candidates_by_name()
        source_index = SourceIndex(sample_repo_path)

        paper_params = {"learning_rate": 0.001}
        mapper = PaperCodeMapper(paper_params, candidates, source_index)
        mappings = mapper.map_all()
        lr_mapping = next(m for m in mappings if m.paper_field == "learning_rate")

        assert lr_mapping.evidence is not None
        assert lr_mapping.evidence.verified is True
        assert lr_mapping.evidence.file in {"train.py", "config.py"}
