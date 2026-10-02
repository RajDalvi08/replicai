"""Tests for the Code Intelligence module - parameter extraction and normalization."""

from pathlib import Path

from backend.code.parameters import (
    CANONICAL_PARAMETERS,
    ParameterExtractor,
    canonical_parameter_name,
    normalize_key,
)
from backend.code.python_analysis import analyze_python_file
from backend.code.utils import collect_repository_files


def test_canonical_parameters_defined():
    expected = {
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
    }
    assert set(CANONICAL_PARAMETERS) == expected


def test_normalize_key():
    assert normalize_key("learning_rate") == "learning_rate"
    assert normalize_key("learning-rate") == "learning_rate"
    assert normalize_key("learning rate") == "learning_rate"
    assert normalize_key("--learning-rate") == "learning_rate"
    assert normalize_key("batch_size") == "batch_size"
    assert normalize_key("batch-size") == "batch_size"
    assert normalize_key("num_epochs") == "num_epochs"
    assert normalize_key("seed") == "seed"


def test_canonical_parameter_name():
    assert canonical_parameter_name("learning_rate") == "learning_rate"
    assert canonical_parameter_name("lr") == "learning_rate"
    assert canonical_parameter_name("learning-rate") == "learning_rate"
    assert canonical_parameter_name("batch_size") == "batch_size"
    assert canonical_parameter_name("bs") == "batch_size"
    assert canonical_parameter_name("batch") == "batch_size"
    assert canonical_parameter_name("epochs") == "epochs"
    assert canonical_parameter_name("num_epochs") == "epochs"
    assert canonical_parameter_name("n_epochs") == "epochs"
    assert canonical_parameter_name("seed") == "random_seed"
    assert canonical_parameter_name("random_seed") == "random_seed"
    assert canonical_parameter_name("wd") == "weight_decay"
    assert canonical_parameter_name("dropout") == "dropout"
    assert canonical_parameter_name("optimizer") == "optimizer"
    assert canonical_parameter_name("scheduler") == "scheduler"
    assert canonical_parameter_name("model_name") == "model"
    assert canonical_parameter_name("dataset_name") == "dataset"
    assert canonical_parameter_name("metric_name") == "metric"
    assert canonical_parameter_name("loss") == "loss_function"
    assert canonical_parameter_name("unknown_param") is None


def test_parameter_extraction(sample_repo_path: Path):
    files = collect_repository_files(sample_repo_path)
    analyses = [a for f in files if (a := analyze_python_file(f))]
    extractor = ParameterExtractor(analyses)
    params = extractor.extract()
    param_map = {p.name: p for p in params}

    # All canonical parameters should have a value
    for name in CANONICAL_PARAMETERS:
        assert name in param_map, f"missing {name}"

    # Check specific values
    assert param_map["learning_rate"].value == 0.001
    assert param_map["batch_size"].value == 64
    assert param_map["epochs"].value == 10
    assert param_map["weight_decay"].value == 0.01
    assert param_map["dropout"].value == 0.1
    assert param_map["random_seed"].value == 42
    assert param_map["dataset"].value == "synthetic-toy-corpus"
    assert param_map["model"].value == "EncoderClassifier"
    assert param_map["optimizer"].value == "AdamW"
    assert param_map["scheduler"].value == "CosineAnnealingLR"
    assert param_map["loss_function"].value == "CrossEntropyLoss"
    assert param_map["metric"].value == "accuracy"

    # Check origins and files
    assert param_map["optimizer"].origin == "optimizer_call"
    assert param_map["scheduler"].origin == "scheduler_call"
    assert param_map["loss_function"].origin == "loss_call"
    assert param_map["metric"].origin == "dict_key"
    assert param_map["dataset"].origin == "dict_key"
    assert param_map["model"].origin == "dict_key"
    assert param_map["learning_rate"].origin == "cli_argument"
    assert param_map["batch_size"].origin == "cli_argument"
    assert param_map["epochs"].origin == "cli_argument"
    assert param_map["random_seed"].origin == "cli_argument"


def test_optimizer_extraction(sample_repo_path: Path):
    files = collect_repository_files(sample_repo_path)
    analyses = [a for f in files if (a := analyze_python_file(f))]
    extractor = ParameterExtractor(analyses)
    optimizers = extractor.optimizers()

    assert len(optimizers) == 1
    opt = optimizers[0]
    assert opt.name == "AdamW"
    assert opt.file == "train.py"
    assert opt.line == 73


def test_scheduler_extraction(sample_repo_path: Path):
    files = collect_repository_files(sample_repo_path)
    analyses = [a for f in files if (a := analyze_python_file(f))]
    extractor = ParameterExtractor(analyses)
    schedulers = extractor.schedulers()

    assert len(schedulers) == 1
    assert schedulers[0].name == "CosineAnnealingLR"


def test_loss_extraction(sample_repo_path: Path):
    files = collect_repository_files(sample_repo_path)
    analyses = [a for f in files if (a := analyze_python_file(f))]
    extractor = ParameterExtractor(analyses)
    losses = extractor.loss_functions()

    assert len(losses) == 1
    assert losses[0].name == "CrossEntropyLoss"


def test_metric_extraction(sample_repo_path: Path):
    files = collect_repository_files(sample_repo_path)
    analyses = [a for f in files if (a := analyze_python_file(f))]
    extractor = ParameterExtractor(analyses)
    metrics = extractor.metrics()

    # Should find 'accuracy' from multiple sources
    metric_names = {m.name for m in metrics}
    assert "accuracy" in metric_names
    # Should NOT find 'evaluate' (removed from METRIC_CALLABLES)
    assert "evaluate" not in metric_names
