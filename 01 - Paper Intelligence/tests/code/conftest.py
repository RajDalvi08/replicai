"""Test fixtures and configuration for Code Intelligence tests."""

import shutil
from pathlib import Path

import pytest

from backend.code.ingestion import RepositoryIngestor


@pytest.fixture
def sample_repo_path() -> Path:
    """Path to the synthetic research repository fixture."""
    return Path(__file__).parent.parent / "fixtures" / "sample_repo"


@pytest.fixture
def fake_ingestor():
    """Factory for an ingestor that copies the fixture instead of cloning."""

    def _make(fixture_path: Path):
        def fake_runner(args, timeout, cwd):
            from unittest.mock import MagicMock

            dest = Path(args[-1])
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(fixture_path, dest)
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            return result

        return RepositoryIngestor(runner=fake_runner)

    return _make


@pytest.fixture
def sample_paper_params():
    """Expected paper parameters for the sample repository."""
    return {
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
