"""Tests for the Code Intelligence module - structure analysis."""

from pathlib import Path

from backend.code.analyzer import analyze_structure
from backend.code.python_analysis import analyze_python_file
from backend.code.schemas import FileRole
from backend.code.utils import collect_repository_files


def test_collect_repository_files(sample_repo_path: Path):
    files = collect_repository_files(sample_repo_path)
    paths = {f.path for f in files}
    assert "train.py" in paths
    assert "evaluate.py" in paths
    assert "config.py" in paths
    assert "model.py" in paths
    assert "dataset.py" in paths
    assert "requirements.txt" in paths
    assert "README.md" in paths


def test_analyze_structure(sample_repo_path: Path):
    files = collect_repository_files(sample_repo_path)
    from backend.code.python_analysis import is_python_file

    python_files = [f for f in files if is_python_file(f)]
    analyses = [analyze_python_file(f) for f in python_files]
    analyses = [a for a in analyses if a]
    structure = analyze_structure(sample_repo_path, files, analyses)

    assert structure.python_file_count == 5
    detected_paths = {d.path: d for d in structure.detected}

    # Check roles
    assert detected_paths["train.py"].role == FileRole.training_entrypoint
    assert detected_paths["train.py"].confidence >= 0.9
    assert detected_paths["evaluate.py"].role == FileRole.evaluation_entrypoint
    assert detected_paths["evaluate.py"].confidence >= 0.9
    assert detected_paths["config.py"].role == FileRole.configuration
    assert detected_paths["config.py"].confidence >= 0.8
    assert detected_paths["dataset.py"].role == FileRole.dataset
    assert detected_paths["model.py"].role == FileRole.model_definition
    assert detected_paths["requirements.txt"].role == FileRole.dependency_manifest
    assert detected_paths["README.md"].role == FileRole.documentation

    # Entry points
    entries = structure.entry_points()
    entry_paths = {e.path for e in entries}
    assert "train.py" in entry_paths
    assert "evaluate.py" in entry_paths

    # Best of role
    best_train = structure.best_of_role(FileRole.training_entrypoint)
    assert best_train is not None
    assert best_train.path == "train.py"

    best_model = structure.best_of_role(FileRole.model_definition)
    assert best_model is not None
    assert best_model.path == "model.py"


def test_has_role(sample_repo_path: Path):
    files = collect_repository_files(sample_repo_path)
    analyses = [a for a in (analyze_python_file(f) for f in files) if a]
    structure = analyze_structure(sample_repo_path, files, analyses)

    assert structure.has_role(FileRole.training_entrypoint)
    assert structure.has_role(FileRole.evaluation_entrypoint)
    assert structure.has_role(FileRole.configuration)
    assert structure.has_role(FileRole.dataset)
    assert structure.has_role(FileRole.model_definition)
    assert not structure.has_role(FileRole.optimizer, minimum_confidence=0.9)
