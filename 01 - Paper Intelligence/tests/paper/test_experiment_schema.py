import pytest
from pydantic import ValidationError

from backend.paper.schemas import Experiment, ExperimentEvidence, SyntheticExperiment


def test_experiment_schema_accepts_missing_optional_values():
    experiment = Experiment(
        experiment_id="exp-1",
        title="Training run",
        description="Baseline training",
        dataset="CIFAR-10",
        model="ResNet-50",
        optimizer="SGD",
        learning_rate=0.01,
        batch_size=64,
        epochs=50,
        scheduler=None,
        weight_decay=None,
        dropout=None,
        random_seed=42,
        metric="accuracy",
        reported_results={"accuracy": {"value": 87.6, "unit": "%", "higher_is_better": True}},
        procedure="Train for 50 epochs.",
        evidence=[
            ExperimentEvidence(
                field="batch_size",
                value=64,
                page=7,
                source_type="table",
                source_label="Table 3",
                quote="Batch size 64",
                confidence=0.96,
            )
        ],
        extraction_confidence=0.8,
        warnings=[],
    )

    assert experiment.dataset == "CIFAR-10"
    assert experiment.scheduler is None


def test_experiment_schema_rejects_invalid_evidence():
    with pytest.raises(ValidationError):
        ExperimentEvidence(
            field="batch_size",
            value=64,
            page=7,
            source_type="table",
            source_label="Table 3",
            quote="Batch size 64",
            confidence=1.5,
        )


def test_synthetic_experiment_placeholder():
    synthetic = SyntheticExperiment(
        experiment_id="synth-1",
        title="Synthetic experiment",
        description="This is used to test a synthetic entry.",
        dataset="MNIST",
        model="MLP",
        optimizer="Adam",
        learning_rate=0.001,
        batch_size=32,
        epochs=10,
        scheduler=None,
        weight_decay=None,
        dropout=None,
        random_seed=7,
        metric="loss",
        reported_results={"loss": {"value": 0.72, "unit": "", "higher_is_better": False}},
        procedure="Train on MNIST.",
        evidence=[],
        extraction_confidence=0.7,
        warnings=[],
    )
    assert synthetic.experiment_id == "synth-1"
