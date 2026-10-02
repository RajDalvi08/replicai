"""Repository structure analysis.

Detects which files in an untrusted repository are likely to be training,
evaluation, configuration, dataset or model files. Classification starts from
file naming conventions and is then refined with static evidence gathered from
the file itself, so confidence is only raised when the code actually supports
the hypothesis.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from backend.code.config import DEPENDENCY_MANIFEST_NAMES, DOCUMENTATION_NAMES
from backend.code.python_analysis import PythonFileAnalysis
from backend.code.schemas import DetectedFile, FileRole
from backend.code.utils import RepositoryFile, read_text_file

logger = logging.getLogger("replicai.code.analyzer")

#: Filename -> role, with the confidence granted by the name alone.
FILENAME_ROLE_RULES: dict[str, tuple[FileRole, float]] = {
    "train.py": (FileRole.training_entrypoint, 0.75),
    "training.py": (FileRole.training_entrypoint, 0.7),
    "main.py": (FileRole.training_entrypoint, 0.6),
    "run.py": (FileRole.training_entrypoint, 0.55),
    "pretrain.py": (FileRole.training_entrypoint, 0.6),
    "evaluate.py": (FileRole.evaluation_entrypoint, 0.75),
    "eval.py": (FileRole.evaluation_entrypoint, 0.7),
    "test.py": (FileRole.evaluation_entrypoint, 0.6),
    "validation.py": (FileRole.evaluation_entrypoint, 0.6),
    "inference.py": (FileRole.inference_entrypoint, 0.7),
    "predict.py": (FileRole.inference_entrypoint, 0.7),
    "infer.py": (FileRole.inference_entrypoint, 0.65),
    "config.py": (FileRole.configuration, 0.75),
    "configuration.py": (FileRole.configuration, 0.7),
    "args.py": (FileRole.configuration, 0.7),
    "arguments.py": (FileRole.configuration, 0.7),
    "hyperparameters.py": (FileRole.configuration, 0.75),
    "hyperparams.py": (FileRole.configuration, 0.75),
    "settings.py": (FileRole.configuration, 0.7),
    "dataset.py": (FileRole.dataset, 0.75),
    "datasets.py": (FileRole.dataset, 0.7),
    "data.py": (FileRole.dataset, 0.65),
    "data_loader.py": (FileRole.dataset, 0.7),
    "dataloader.py": (FileRole.dataset, 0.7),
    "corpus.py": (FileRole.dataset, 0.7),
    "model.py": (FileRole.model_definition, 0.7),
    "models.py": (FileRole.model_definition, 0.65),
    "network.py": (FileRole.model_definition, 0.7),
    "net.py": (FileRole.model_definition, 0.7),
    "architectures.py": (FileRole.model_definition, 0.7),
    "metrics.py": (FileRole.metrics, 0.7),
    "metric.py": (FileRole.metrics, 0.7),
    "evaluation.py": (FileRole.metrics, 0.6),
    "optim.py": (FileRole.optimizer, 0.7),
    "optimizer.py": (FileRole.optimizer, 0.7),
    "schedulers.py": (FileRole.scheduler, 0.7),
    "scheduler.py": (FileRole.scheduler, 0.7),
}

#: Directories whose contents default to a role.
DIRECTORY_ROLE_RULES: dict[str, FileRole] = {
    "configs": FileRole.configuration,
    "config": FileRole.configuration,
    "conf": FileRole.configuration,
    "configs/": FileRole.configuration,
    "models": FileRole.model_definition,
    "model": FileRole.model_definition,
    "src/models": FileRole.model_definition,
    "datasets": FileRole.dataset,
    "data": FileRole.dataset,
    "src/data": FileRole.dataset,
    "evaluation": FileRole.metrics,
    "eval": FileRole.metrics,
    "metrics": FileRole.metrics,
    "scripts": FileRole.training_entrypoint,
}

#: Roles that represent a runnable entry point.
ENTRY_POINT_ROLES: frozenset[FileRole] = frozenset(
    {
        FileRole.training_entrypoint,
        FileRole.evaluation_entrypoint,
        FileRole.inference_entrypoint,
    }
)


@dataclass
class RepositoryStructure:
    root_path: str
    files: list[RepositoryFile] = field(default_factory=list)
    detected: list[DetectedFile] = field(default_factory=list)
    analyses: list[PythonFileAnalysis] = field(default_factory=list)
    dependency_manifests: list[str] = field(default_factory=list)
    python_file_count: int = 0
    parse_failures: list[str] = field(default_factory=list)

    def entry_points(self) -> list[DetectedFile]:
        return [item for item in self.detected if item.role in ENTRY_POINT_ROLES]

    def detected_by_role(self, role: FileRole) -> list[DetectedFile]:
        return [item for item in self.detected if item.role == role]

    def has_role(self, role: FileRole, minimum_confidence: float = 0.0) -> bool:
        return any(
            item.role == role and item.confidence >= minimum_confidence for item in self.detected
        )

    def best_of_role(self, role: FileRole) -> DetectedFile | None:
        candidates = self.detected_by_role(role)
        if not candidates:
            return None
        return max(candidates, key=lambda item: (item.confidence, -len(item.path)))


def _file_type(repository_file: RepositoryFile) -> str:
    if repository_file.suffix == ".py":
        return "python"
    if repository_file.suffix in {".md", ".rst", ".txt"}:
        return "text"
    if repository_file.suffix in {".toml", ".yml", ".yaml", ".cfg", ".ini"}:
        return "config"
    if repository_file.suffix in {".json"}:
        return "json"
    if repository_file.suffix in {".sh", ".bash"}:
        return "shell"
    if repository_file.suffix in {".ipynb"}:
        return "notebook"
    if repository_file.suffix in {".ipynb", ".ckpt", ".pt", ".pth"}:
        return "artifact"
    return repository_file.suffix.lstrip(".") or "other"


def _content_signals(analysis: PythonFileAnalysis) -> dict[str, bool]:
    signal_names = {signal.name for signal in analysis.signals}
    detail_names = {signal.detail for signal in analysis.signals if signal.detail}
    return {
        "main_block": "main_block" in signal_names,
        "optimizer": "optimizer_call" in signal_names,
        "scheduler": "scheduler_call" in signal_names,
        "loss": "loss_call" in signal_names,
        "metric": bool({"metric_call", "metric_literal"} & signal_names),
        "training_loop": bool(
            {"backward_pass", "optimizer_step", "epoch_loop", "training_function"} & signal_names
        ),
        "dataset": "dataset_load" in signal_names,
        "tokenizer": "tokenization" in signal_names,
        "evaluation": bool({"evaluation_function", "eval_mode_call"} & signal_names),
        "inference": "inference_context" in signal_names,
        "checkpoint": "checkpoint_save" in signal_names,
        "cli": "cli_framework" in signal_names,
        "model_class": any(
            info.name.endswith(("Model", "Net", "Network", "Classifier"))
            or any(
                base.split(".")[-1] in {"Module", "Model", "PreTrainedModel"} for base in info.bases
            )
            for info in analysis.classes
        ),
        "optimizer_class": any(info.name.endswith("Optimizer") for info in analysis.classes),
        "scheduler_class": any(
            info.name.endswith(("Scheduler", "LR")) for info in analysis.classes
        ),
        "metric_detail": bool(detail_names & {"accuracy", "f1", "bleu", "rouge"}),
    }


def _refine_role(
    role: FileRole, signals: dict[str, bool], analysis: PythonFileAnalysis
) -> tuple[FileRole, float, str] | None:
    """Return an updated role/confidence/reason when the code supports it."""
    if role is FileRole.training_entrypoint:
        if signals["optimizer"] and (
            signals["training_loop"] or signals["epoch_loop"] or signals["main_block"]
        ):
            bonus = 0.21 if signals["main_block"] and signals["optimizer"] else 0.15
            return (
                role,
                bonus,
                "declares an optimizer together with a training loop or epoch range",
            )
        if signals["optimizer"] and signals["loss"]:
            return role, 0.1, "constructs an optimizer and a loss function"
        if signals["main_block"] and signals["training_loop"]:
            return role, 0.12, "guarded by __main__ and contains a training loop"
        return (
            role,
            -0.2,
            "named like a training script but no optimizer or training loop was found",
        )
    if role is FileRole.evaluation_entrypoint:
        if signals["evaluation"] and (signals["metric"] or signals["inference"]):
            return role, 0.18, "defines evaluation logic and computes a metric"
        if signals["evaluation"] or signals["metric"]:
            return role, 0.08, "defines an evaluation routine"
        return (
            role,
            -0.2,
            "named like an evaluation script but no evaluation logic was found",
        )
    if role is FileRole.inference_entrypoint:
        if signals["inference"] or signals["evaluation"]:
            return role, 0.1, "runs inference or evaluation passes"
        return role, -0.1, "named like an inference script"
    if role is FileRole.model_definition:
        if signals["model_class"]:
            return role, 0.18, "defines a neural network class"
        return (
            role,
            -0.15,
            "named like a model module but no network class was found",
        )
    if role is FileRole.dataset:
        if signals["dataset"]:
            return role, 0.18, "constructs a dataset or data loader"
        if any(info.name.endswith(("Dataset", "Corpus")) for info in analysis.classes):
            return role, 0.1, "defines a dataset class"
        return (
            role,
            -0.15,
            "named like a dataset module but no dataset loading was found",
        )
    if role is FileRole.configuration:
        if signals["cli"] or any(
            value.origin in {"assignment", "dict_key"} for value in analysis.config_values
        ):
            return role, 0.12, "declares configuration values"
        return role, -0.1, "named like a configuration module"
    if role is FileRole.metrics:
        if signals["metric"]:
            return role, 0.15, "computes a metric"
        return role, -0.1, "named like a metrics module"
    if role is FileRole.optimizer:
        if signals["optimizer"] or signals["optimizer_class"]:
            return role, 0.15, "constructs optimizer instances"
        return role, -0.1, "named like an optimizer module"
    if role is FileRole.scheduler:
        if signals["scheduler"] or signals["scheduler_class"]:
            return role, 0.15, "constructs learning rate schedulers"
        return role, -0.1, "named like a scheduler module"
    return None


def _classify_python_file(
    repository_file: RepositoryFile, analysis: PythonFileAnalysis
) -> DetectedFile:
    name = PurePosixPath(repository_file.path).name.lower()
    signals = _content_signals(analysis)
    reason_parts: list[str] = []

    role, confidence = FILENAME_ROLE_RULES.get(name, (FileRole.unknown, 0.3))
    if role is not FileRole.unknown:
        reason_parts.append(f"filename '{name}' matches the {role.value} convention")
    else:
        directory = PurePosixPath(repository_file.path).parent.as_posix()
        directory_role = DIRECTORY_ROLE_RULES.get(directory)
        if directory_role is not None:
            role, confidence = directory_role, 0.45
            reason_parts.append(f"located in the '{directory}/' directory")

    refinement = _refine_role(role, signals, analysis)
    if refinement is not None:
        new_role, delta, reason = refinement
        confidence = max(0.05, min(0.98, confidence + delta))
        reason_parts.append(reason)
        if delta < 0:
            role = new_role

    if role is FileRole.unknown and signals["main_block"]:
        if signals["training_loop"] and signals["optimizer"]:
            role, confidence = FileRole.training_entrypoint, 0.55
            reason_parts.append("__main__ block runs an optimizer-driven training loop")
        elif signals["evaluation"] or signals["inference"]:
            role, confidence = FileRole.evaluation_entrypoint, 0.45
            reason_parts.append("__main__ block runs evaluation logic")
        else:
            role, confidence = FileRole.unknown, 0.35
            reason_parts.append("has a __main__ block but no recognizable role")
    elif role is FileRole.unknown and signals["optimizer"] and signals["training_loop"]:
        role, confidence = FileRole.training_entrypoint, 0.4
        reason_parts.append("builds an optimizer and contains a training loop")

    if analysis.parse_error:
        reason_parts.append(f"file could not be parsed ({analysis.parse_error})")
        confidence = min(confidence, 0.5)

    return DetectedFile(
        path=repository_file.path,
        file_type=_file_type(repository_file),
        role=role,
        confidence=round(confidence, 4),
        evidence=reason_parts,
    )


def _classify_plain_file(repository_file: RepositoryFile) -> DetectedFile:
    name = PurePosixPath(repository_file.path).name.lower()
    if name in DEPENDENCY_MANIFEST_NAMES:
        return DetectedFile(
            path=repository_file.path,
            file_type=_file_type(repository_file),
            role=FileRole.dependency_manifest,
            confidence=0.95,
            evidence=[f"'{name}' is a Python dependency manifest"],
        )
    if name in DOCUMENTATION_NAMES:
        return DetectedFile(
            path=repository_file.path,
            file_type=_file_type(repository_file),
            role=FileRole.documentation,
            confidence=0.95,
            evidence=[f"'{name}' is repository documentation"],
        )
    directory = PurePosixPath(repository_file.path).parent.as_posix()
    if directory in DIRECTORY_ROLE_RULES:
        return DetectedFile(
            path=repository_file.path,
            file_type=_file_type(repository_file),
            role=DIRECTORY_ROLE_RULES[directory],
            confidence=0.4,
            evidence=[f"located in the '{directory}/' directory"],
        )
    return DetectedFile(
        path=repository_file.path,
        file_type=_file_type(repository_file),
        role=FileRole.unknown,
        confidence=0.2,
        evidence=["no structural signal matched this file"],
    )


def parse_dependencies(root: object, manifests: list[str]) -> list[str]:
    """Read dependency names from manifests without importing or installing."""
    from pathlib import Path as _Path

    from backend.code.config import settings

    packages: list[str] = []
    for manifest in manifests:
        name = PurePosixPath(manifest).name.lower()
        path = _Path(str(root)) / manifest
        content = read_text_file(path, max_bytes=settings.max_dependency_manifest_bytes)
        if content is None:
            continue
        if name == "requirements.txt" or name.startswith("requirements"):
            for line in content.splitlines():
                cleaned = line.split("#", 1)[0].strip()
                if not cleaned or cleaned.startswith("-"):
                    continue
                package = cleaned.split("==")[0].split(">=")[0].split("<")[0]
                package = package.split("[")[0].strip()
                if package:
                    packages.append(package)
        elif name == "pyproject.toml":
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("name") and "=" in stripped:
                    value = stripped.split("=", 1)[1].strip().strip('"').strip("'")
                    if value:
                        packages.append(value)
    deduped: list[str] = []
    for package in packages:
        if package not in deduped:
            deduped.append(package)
    return sorted(deduped)


def analyze_structure(
    root: object, files: list[RepositoryFile], analyses: list[PythonFileAnalysis]
) -> RepositoryStructure:
    """Classify every collected file and derive structural facts."""
    structure = RepositoryStructure(root_path=str(root), files=files, analyses=analyses)
    analysis_by_path = {item.path: item for item in analyses}
    structure.python_file_count = len(analyses)

    for repository_file in files:
        analysis = analysis_by_path.get(repository_file.path)
        if analysis is None:
            detected = _classify_plain_file(repository_file)
        else:
            detected = _classify_python_file(repository_file, analysis)
            if analysis.parse_error:
                structure.parse_failures.append(repository_file.path)
        if detected.role is FileRole.dependency_manifest:
            structure.dependency_manifests.append(repository_file.path)
        structure.detected.append(detected)

    structure.detected.sort(key=lambda item: item.path)
    logger.info(
        "event=structure_analyzed files=%s python_files=%s entry_points=%s",
        len(structure.files),
        structure.python_file_count,
        len(structure.entry_points()),
    )
    return structure
