"""Tests for the Code Intelligence module - deterministic readiness engine."""

from pathlib import Path

from backend.code.analyzer import analyze_structure, parse_dependencies
from backend.code.evidence import SourceIndex
from backend.code.mapper import PaperCodeMapper
from backend.code.parameters import ParameterExtractor
from backend.code.pipeline import detect_pipeline
from backend.code.python_analysis import analyze_python_file, is_python_file
from backend.code.readiness import (
    CATEGORY_WEIGHTS,
    analyze_repository_readiness,
    overall_status_for,
    status_for_score,
)
from backend.code.utils import collect_repository_files


class TestReadinessEngine:
    def test_weights_sum_to_100(self):
        total = sum(CATEGORY_WEIGHTS.values())
        assert abs(total - 100.0) < 1e-9

    def test_status_thresholds(self):
        assert overall_status_for(95) == "ready"
        assert overall_status_for(90) == "ready"
        assert overall_status_for(89) == "mostly_ready"
        assert overall_status_for(75) == "mostly_ready"
        assert overall_status_for(74) == "partial"
        assert overall_status_for(50) == "partial"
        assert overall_status_for(49) == "not_ready"
        assert overall_status_for(0) == "not_ready"

    def test_category_status(self):
        assert status_for_score(1.0) == "ready"
        assert status_for_score(0.9) == "ready"
        assert status_for_score(0.8) == "partial"
        assert status_for_score(0.5) == "partial"
        assert status_for_score(0.3) == "uncertain"
        assert status_for_score(0.0) == "missing"


class TestFullReadinessAnalysis:
    def test_full_readiness_analysis(self, sample_repo_path: Path):
        """End-to-end readiness computation on the fixture."""
        files = collect_repository_files(sample_repo_path)
        python_files = [f for f in files if is_python_file(f)]
        analyses = [analyze_python_file(f) for f in python_files]
        analyses = [a for a in analyses if a]
        structure = analyze_structure(sample_repo_path, files, analyses)
        source_index = SourceIndex(sample_repo_path)

        extractor = ParameterExtractor(analyses)
        code_parameters = extractor.extract()
        optimizers = extractor.optimizers()
        dependencies = parse_dependencies(sample_repo_path, structure.dependency_manifests)
        pipeline = detect_pipeline(analyses, source_index)

        # Paper params (from expected JSON)
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
        candidates = extractor.candidates_by_name()
        mapper = PaperCodeMapper(paper_params, candidates, source_index)
        mappings = mapper.map_all()

        outcome = analyze_repository_readiness(
            structure, code_parameters, pipeline, optimizers, dependencies, mappings, source_index
        )

        # Overall score should be high for this well-specified repo
        assert outcome.overall_score >= 85, f"score={outcome.overall_score}"
        assert outcome.status in {"ready", "mostly_ready"}

        # Check individual categories
        items_by_cat = {item.category: item for item in outcome.items}
        assert items_by_cat["entry_point"].score == 1.0
        assert items_by_cat["dataset"].score == 1.0
        assert items_by_cat["model"].score == 1.0
        assert items_by_cat["training_parameters"].score == 1.0
        assert items_by_cat["optimizer"].score == 1.0
        assert items_by_cat["evaluation"].score == 1.0
        assert items_by_cat["metrics"].score >= 0.5  # partial
        assert items_by_cat["dependencies"].score == 1.0
        assert items_by_cat["random_seed"].score == 1.0
        assert items_by_cat["paper_code_consistency"].score >= 0.9

        # Score should equal sum(weight * score)
        recomputed = sum(item.weight * item.score for item in outcome.items)
        assert abs(outcome.overall_score - round(recomputed, 2)) < 0.01

        # Should have no high-severity blockers
        high_blockers = [b for b in outcome.blockers if b.severity == "high"]
        assert len(high_blockers) == 0

        # Warnings for partial categories
        warning_cats = {w.category for w in outcome.warnings}
        assert "metrics" in warning_cats  # partial

    def test_readiness_reproducible(self, sample_repo_path: Path):
        """Running twice yields identical results."""
        files = collect_repository_files(sample_repo_path)
        python_files = [f for f in files if is_python_file(f)]
        analyses = [analyze_python_file(f) for f in python_files]
        analyses = [a for a in analyses if a]
        structure = analyze_structure(sample_repo_path, files, analyses)
        source_index = SourceIndex(sample_repo_path)

        extractor = ParameterExtractor(analyses)
        code_parameters = extractor.extract()
        optimizers = extractor.optimizers()
        dependencies = parse_dependencies(sample_repo_path, structure.dependency_manifests)
        pipeline = detect_pipeline(analyses, source_index)

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
        }
        candidates = extractor.candidates_by_name()
        mapper = PaperCodeMapper(paper_params, candidates, source_index)
        mappings = mapper.map_all()

        outcome1 = analyze_repository_readiness(
            structure, code_parameters, pipeline, optimizers, dependencies, mappings, source_index
        )
        outcome2 = analyze_repository_readiness(
            structure, code_parameters, pipeline, optimizers, dependencies, mappings, source_index
        )

        assert outcome1.overall_score == outcome2.overall_score
        assert outcome1.status == outcome2.status
        for i1, i2 in zip(outcome1.items, outcome2.items):
            assert i1.score == i2.score
            assert i1.reason == i2.reason
