"""Tests for the Code Intelligence module - Python AST analysis."""

from pathlib import Path

from backend.code.python_analysis import analyze_python_file, is_python_file
from backend.code.utils import collect_repository_files


def test_analyze_train_py(sample_repo_path: Path):
    files = collect_repository_files(sample_repo_path)
    train_file = next(f for f in files if f.path == "train.py")
    analysis = analyze_python_file(train_file)

    assert analysis is not None
    assert analysis.parse_error is None

    # Imports
    import_names = {imp.name for imp in analysis.imports}
    assert "argparse" in import_names
    assert "json" in import_names
    assert "os" in import_names
    assert "random" in import_names
    assert "numpy" in import_names or "numpy" in str(import_names)
    assert any("torch" in imp.name for imp in analysis.imports)

    # Functions
    func_names = {f.name for f in analysis.functions}
    assert "set_seed" in func_names
    assert "build_parser" in func_names
    assert "build_loaders" in func_names
    assert "build_model" in func_names
    assert "train" in func_names
    assert "main" in func_names

    # Classes
    class_names = {c.name for c in analysis.classes}
    assert "TrainingConfig" in class_names

    # CLI arguments
    cli_names = {arg.name for arg in analysis.cli_arguments}
    assert "learning_rate" in cli_names
    assert "batch_size" in cli_names
    assert "epochs" in cli_names
    assert "seed" in cli_names
    assert "resume" in cli_names

    # Config values
    config_names = {cv.name for cv in analysis.config_values}
    assert "learning_rate" in config_names
    assert "batch_size" in config_names
    assert "epochs" in config_names
    assert "weight_decay" in config_names
    assert "dropout" in config_names
    assert "seed" in config_names

    # Calls
    call_symbols = analysis.call_symbols()
    assert "AdamW" in call_symbols
    assert "CosineAnnealingLR" in call_symbols
    assert "CrossEntropyLoss" in call_symbols
    assert "DataLoader" in call_symbols

    # Signals
    signal_names = {s.name for s in analysis.signals}
    assert "optimizer_call" in signal_names
    assert "scheduler_call" in signal_names
    assert "loss_call" in signal_names
    assert "dataset_load" in signal_names
    assert "main_block" in signal_names
    assert "cli_framework" in signal_names
    assert "seeding_function" in signal_names
    assert "training_function" in signal_names

    # Main block
    assert analysis.has_main_block


def test_analyze_model_py(sample_repo_path: Path):
    files = collect_repository_files(sample_repo_path)
    model_file = next(f for f in files if f.path == "model.py")
    analysis = analyze_python_file(model_file)

    assert analysis is not None
    class_names = {c.name for c in analysis.classes}
    assert "EncoderClassifier" in class_names
    encoder = next(c for c in analysis.classes if c.name == "EncoderClassifier")
    assert any("Module" in base for base in encoder.bases)


def test_analyze_dataset_py(sample_repo_path: Path):
    files = collect_repository_files(sample_repo_path)
    dataset_file = next(f for f in files if f.path == "dataset.py")
    analysis = analyze_python_file(dataset_file)

    assert analysis is not None
    class_names = {c.name for c in analysis.classes}
    assert "ToySequenceDataset" in class_names
    ds = next(c for c in analysis.classes if c.name == "ToySequenceDataset")
    assert any("Dataset" in base for base in ds.bases)


def test_analyze_config_py(sample_repo_path: Path):
    files = collect_repository_files(sample_repo_path)
    config_file = next(f for f in files if f.path == "config.py")
    analysis = analyze_python_file(config_file)

    assert analysis is not None
    config_names = {cv.name for cv in analysis.config_values}
    # Dict keys from DEFAULT_CONFIG
    assert "learning_rate" in config_names
    assert "batch_size" in config_names
    assert "epochs" in config_names
    assert "weight_decay" in config_names
    assert "dropout" in config_names
    assert "random_seed" in config_names
    assert "dataset" in config_names
    assert "model" in config_names
    assert "metric" in config_names
    assert "scheduler" in config_names
    assert "optimizer" in config_names
    assert "loss_function" in config_names


def test_is_python_file():
    from backend.code.utils import RepositoryFile

    py = RepositoryFile("train.py", Path("train.py"), 100, ".py")
    assert is_python_file(py)
    setup = RepositoryFile("setup.py", Path("setup.py"), 100, ".py")
    assert is_python_file(setup)
    txt = RepositoryFile("readme.txt", Path("readme.txt"), 100, ".txt")
    assert not is_python_file(txt)
