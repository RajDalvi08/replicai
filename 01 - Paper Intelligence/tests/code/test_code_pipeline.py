"""Tests for the Code Intelligence module - training pipeline detection."""

from pathlib import Path

from backend.code.evidence import SourceIndex
from backend.code.pipeline import detect_pipeline
from backend.code.python_analysis import analyze_python_file
from backend.code.schemas import PipelineStageStatus
from backend.code.utils import collect_repository_files


def test_detect_pipeline(sample_repo_path: Path):
    files = collect_repository_files(sample_repo_path)
    analyses = [a for f in files if (a := analyze_python_file(f))]
    source_index = SourceIndex(sample_repo_path)
    pipeline = detect_pipeline(analyses, source_index)

    stages = {s.name: s for s in pipeline.stages}

    # All expected stages present
    expected = [
        "dataset_loading",
        "preprocessing",
        "model_creation",
        "optimizer_creation",
        "scheduler_creation",
        "training_loop",
        "evaluation",
        "metric_calculation",
        "checkpoint_saving",
    ]
    for name in expected:
        assert name in stages

    # Check statuses
    assert stages["dataset_loading"].status == PipelineStageStatus.detected
    assert stages["preprocessing"].status == PipelineStageStatus.not_detected
    assert stages["model_creation"].status == PipelineStageStatus.detected
    assert stages["optimizer_creation"].status == PipelineStageStatus.detected
    assert stages["scheduler_creation"].status == PipelineStageStatus.detected
    assert stages["training_loop"].status == PipelineStageStatus.detected
    assert stages["evaluation"].status == PipelineStageStatus.detected
    assert stages["metric_calculation"].status == PipelineStageStatus.partial
    assert stages["checkpoint_saving"].status == PipelineStageStatus.detected

    # Evidence should be verifiable
    for stage in pipeline.stages:
        for evidence in stage.evidence:
            assert evidence.verified is True or evidence.line_start is None
