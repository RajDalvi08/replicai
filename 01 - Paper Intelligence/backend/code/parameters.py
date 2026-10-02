"""Canonical parameter vocabulary and normalization.

Part 2 uses exactly the same canonical parameter names as Part 1 so that a
paper value extracted from a PDF and a value detected in source code can be
compared without translation.

Design rules:

* a parameter is only reported when a value could actually be read from code,
* nothing is inferred or defaulted; undetectable parameters keep ``value=None``,
* every detected value keeps file, line, quote and confidence.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from backend.code.python_analysis import (
    LOSS_SYMBOLS,
    OPTIMIZER_SYMBOLS,
    SCHEDULER_SYMBOLS,
    PythonFileAnalysis,
)
from backend.code.schemas import CodeOptimizer, CodeParameter, CodeSymbolUsage

#: Canonical parameter names, ordered exactly like the Part 1 ``Experiment``.
CANONICAL_PARAMETERS: tuple[str, ...] = (
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
)

#: Parameters that must be numeric when a value is present.
NUMERIC_PARAMETERS: frozenset[str] = frozenset(
    {"learning_rate", "batch_size", "epochs", "weight_decay", "dropout", "random_seed"}
)

#: Parameters whose value is a short textual name.
TEXTUAL_PARAMETERS: frozenset[str] = frozenset(
    {"dataset", "model", "optimizer", "scheduler", "metric", "loss_function"}
)

#: Documented alias table. Keys are compared after ``normalize_key``.
PARAMETER_ALIASES: dict[str, str] = {
    # learning rate
    "lr": "learning_rate",
    "learning_rate": "learning_rate",
    "learningrate": "learning_rate",
    "init_lr": "learning_rate",
    "base_lr": "learning_rate",
    "peak_lr": "learning_rate",
    "start_lr": "learning_rate",
    "train_lr": "learning_rate",
    # batch size
    "bs": "batch_size",
    "batch": "batch_size",
    "batchsize": "batch_size",
    "train_batch_size": "batch_size",
    "batch_size_train": "batch_size",
    "train_batchsize": "batch_size",
    "per_device_train_batch_size": "batch_size",
    "global_batch_size": "batch_size",
    "mini_batch_size": "batch_size",
    # epochs
    "epoch": "epochs",
    "num_epochs": "epochs",
    "n_epochs": "epochs",
    "max_epochs": "epochs",
    "num_epoch": "epochs",
    "n_epoch": "epochs",
    "total_epochs": "epochs",
    "train_epochs": "epochs",
    "num_train_epochs": "epochs",
    "epochs_train": "epochs",
    # weight decay
    "wd": "weight_decay",
    "weight_decay": "weight_decay",
    "weightdecay": "weight_decay",
    "l2": "weight_decay",
    "weight_decay_rate": "weight_decay",
    # dropout
    "drop": "dropout",
    "dropout_rate": "dropout",
    "dropout_p": "dropout",
    "dropout_ratio": "dropout",
    # random seed
    "seed": "random_seed",
    "random_seed": "random_seed",
    "manual_seed": "random_seed",
    "torch_seed": "random_seed",
    "np_seed": "random_seed",
    "global_seed": "random_seed",
    # optimizer
    "opt": "optimizer",
    "optim": "optimizer",
    "optim_name": "optimizer",
    "optimizer_name": "optimizer",
    # scheduler
    "lr_scheduler": "scheduler",
    "lr_sched": "scheduler",
    "sched": "scheduler",
    "scheduler_name": "scheduler",
    "schedule": "scheduler",
    # model
    "model_name": "model",
    "architecture": "model",
    "arch": "model",
    "network": "model",
    "net": "model",
    "backbone": "model",
    # dataset
    "dataset_name": "dataset",
    "corpus": "dataset",
    "data_name": "dataset",
    "train_dataset": "dataset",
    # metric
    "metric_name": "metric",
    "eval_metric": "metric",
    "evaluation_metric": "metric",
    "test_metric": "metric",
    "scoring_metric": "metric",
    # loss
    "loss": "loss_function",
    "loss_fn": "loss_function",
    "loss_name": "loss_function",
    "criterion": "loss_function",
}

#: Confidence assigned per detection origin. Higher means stronger evidence.
ORIGIN_CONFIDENCE: dict[str, float] = {
    "optimizer_call": 0.97,
    "scheduler_call": 0.95,
    "loss_call": 0.95,
    "metric_call": 0.93,
    "metric_literal": 0.82,
    "cli_argument": 0.9,
    "dict_key": 0.92,
    "assignment": 0.9,
    "keyword": 0.86,
    "class_name": 0.85,
    "literal_argument": 0.85,
    "call_target": 0.8,
}

#: Penalty applied when a value was resolved through a module level constant.
INDIRECT_PENALTY = 0.15

#: Detection priority per origin. Higher wins when several values exist.
ORIGIN_PRIORITY: dict[str, int] = {
    "optimizer_call": 6,
    "scheduler_call": 5,
    "loss_call": 5,
    "metric_call": 4,
    "metric_literal": 2,
    "cli_argument": 4,
    "dict_key": 3,
    "assignment": 3,
    "keyword": 2,
    "class_name": 2,
    "literal_argument": 2,
    "call_target": 1,
}


def normalize_key(raw_name: str) -> str:
    """Normalize a raw identifier into a comparable alias key."""
    cleaned = str(raw_name).strip().lower()
    while cleaned.startswith("-"):
        cleaned = cleaned[1:]
    cleaned = cleaned.replace("-", "_").replace(" ", "_").replace(".", "_")
    cleaned = cleaned.strip("_")
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned


def canonical_parameter_name(raw_name: str) -> str | None:
    """Return the canonical parameter name for ``raw_name`` or ``None``."""
    key = normalize_key(raw_name)
    if not key:
        return None
    if key in CANONICAL_PARAMETERS:
        return key
    return PARAMETER_ALIASES.get(key)


def _coerce_value(canonical_name: str, value: Any) -> Any:
    """Keep values verbatim; only widen strings for numeric parameters."""
    if value is None or isinstance(value, (list, tuple, dict, set)):
        return None
    if canonical_name in NUMERIC_PARAMETERS and isinstance(value, str):
        from backend.code.utils import coerce_to_number

        return coerce_to_number(value)
    if canonical_name in TEXTUAL_PARAMETERS and isinstance(value, (int, float, bool)):
        # A bare number is not a meaningful dataset/model/metric name.
        return None
    if isinstance(value, str) and len(value) > 200:
        return None
    return value


@dataclass
class ParameterCandidate:
    name: str
    value: Any
    file: str
    line: int
    quote: str
    origin: str
    confidence: float

    @property
    def priority(self) -> int:
        return ORIGIN_PRIORITY.get(self.origin, 0)

    def sort_key(self) -> tuple[int, float, int]:
        return (self.priority, self.confidence, -self.line)


class ParameterExtractor:
    """Turns static findings into canonical, evidence-bearing parameters."""

    def __init__(self, analyses: list[PythonFileAnalysis]) -> None:
        self._analyses = analyses

    # -- public API --------------------------------------------------------- #
    def extract(self) -> list[CodeParameter]:
        candidates = self._collect_candidates()
        selected = self._select_best(candidates)
        return [
            CodeParameter(
                name=name,
                value=candidate.value,
                file=candidate.file,
                line=candidate.line,
                quote=candidate.quote,
                confidence=candidate.confidence,
                origin=candidate.origin,
            )
            for name, candidate in sorted(selected.items())
        ]

    def candidates_by_name(self) -> dict[str, list[ParameterCandidate]]:
        return self._group(self._collect_candidates())

    def optimizers(self) -> list[CodeOptimizer]:
        results: list[CodeOptimizer] = []
        seen: set[tuple[str, int]] = set()
        for analysis in self._analyses:
            for signal in analysis.signals_named("optimizer_call"):
                if signal.detail is None or signal.detail not in OPTIMIZER_SYMBOLS:
                    continue
                key = (analysis.path, signal.line)
                if key in seen:
                    continue
                seen.add(key)
                results.append(
                    CodeOptimizer(
                        name=signal.detail,
                        file=analysis.path,
                        line=signal.line,
                        learning_rate=self._keyword_value(
                            analysis, signal.line, {"lr", "learning_rate"}
                        ),
                        weight_decay=self._keyword_value(
                            analysis, signal.line, {"weight_decay", "wd"}
                        ),
                        momentum=self._keyword_value(analysis, signal.line, {"momentum"}),
                        quote=signal.quote,
                    )
                )
        results.sort(key=lambda item: (item.file, item.line))
        return results

    def _symbol_usages(self, signal_name: str, symbols: Iterable[str]) -> list[CodeSymbolUsage]:
        allowed = set(symbols)
        results: list[CodeSymbolUsage] = []
        seen: set[tuple[str, str, int]] = set()
        for analysis in self._analyses:
            for signal in analysis.signals_named(signal_name):
                if signal.detail is None or signal.detail not in allowed:
                    continue
                key = (analysis.path, signal.detail, signal.line)
                if key in seen:
                    continue
                seen.add(key)
                results.append(
                    CodeSymbolUsage(
                        name=signal.detail,
                        file=analysis.path,
                        line=signal.line,
                        quote=signal.quote,
                    )
                )
        results.sort(key=lambda item: (item.file, item.line))
        return results

    def schedulers(self) -> list[CodeSymbolUsage]:
        return self._symbol_usages("scheduler_call", SCHEDULER_SYMBOLS)

    def loss_functions(self) -> list[CodeSymbolUsage]:
        return self._symbol_usages("loss_call", LOSS_SYMBOLS)

    def metrics(self) -> list[CodeSymbolUsage]:
        results: list[CodeSymbolUsage] = []
        seen: set[tuple[str, str, int]] = set()
        for analysis in self._analyses:
            for signal_name in ("metric_call", "metric_literal"):
                for signal in analysis.signals_named(signal_name):
                    canonical = signal.detail
                    if canonical is None:
                        continue
                    key = (analysis.path, canonical, signal.line)
                    if key in seen:
                        continue
                    seen.add(key)
                    results.append(
                        CodeSymbolUsage(
                            name=canonical,
                            file=analysis.path,
                            line=signal.line,
                            quote=signal.quote,
                        )
                    )
        results.sort(key=lambda item: (item.file, item.line))
        return results

    # -- internals ------------------------------------------------------------ #
    @staticmethod
    def _keyword_value(analysis: PythonFileAnalysis, line: int, names: set[str]) -> float | None:
        for call in analysis.calls:
            if call.line != line:
                continue
            for key, value in call.keywords.items():
                if key in names and isinstance(value, (int, float)):
                    return float(value)
        return None

    def _collect_candidates(self) -> list[ParameterCandidate]:
        candidates: list[ParameterCandidate] = []
        for analysis in self._analyses:
            candidates.extend(self._from_config_values(analysis))
            candidates.extend(self._from_cli_arguments(analysis))
            candidates.extend(self._from_symbols(analysis))
        return candidates

    @staticmethod
    def _add(
        candidates: list[ParameterCandidate],
        name: str,
        value: Any,
        analysis: PythonFileAnalysis,
        line: int,
        quote: str,
        origin: str,
    ) -> None:
        if name not in CANONICAL_PARAMETERS:
            return
        coerced = _coerce_value(name, value)
        if coerced is None:
            return
        candidates.append(
            ParameterCandidate(
                name=name,
                value=coerced,
                file=analysis.path,
                line=line,
                quote=quote,
                origin=origin,
                confidence=round(ORIGIN_CONFIDENCE.get(origin, 0.7), 4),
            )
        )

    def _from_config_values(self, analysis: PythonFileAnalysis) -> list[ParameterCandidate]:
        candidates: list[ParameterCandidate] = []
        for config in analysis.config_values:
            canonical = canonical_parameter_name(config.name)
            if canonical is None:
                continue
            if config.value is None:
                continue
            confidence = ORIGIN_CONFIDENCE.get(config.origin, 0.7)
            if config.indirect:
                confidence = max(0.35, confidence - INDIRECT_PENALTY)
            candidates.append(
                ParameterCandidate(
                    name=canonical,
                    value=_coerce_value(canonical, config.value),
                    file=analysis.path,
                    line=config.line,
                    quote=config.quote,
                    origin=config.origin,
                    confidence=round(confidence, 4),
                )
            )
        return [candidate for candidate in candidates if candidate.value is not None]

    def _from_cli_arguments(self, analysis: PythonFileAnalysis) -> list[ParameterCandidate]:
        candidates: list[ParameterCandidate] = []
        for argument in analysis.cli_arguments:
            canonical = canonical_parameter_name(argument.name)
            if canonical is None or argument.default is None:
                continue
            coerced = _coerce_value(canonical, argument.default)
            if coerced is None:
                continue
            candidates.append(
                ParameterCandidate(
                    name=canonical,
                    value=coerced,
                    file=analysis.path,
                    line=argument.line,
                    quote=argument.quote,
                    origin="cli_argument",
                    confidence=ORIGIN_CONFIDENCE["cli_argument"],
                )
            )
        return candidates

    def _from_symbols(self, analysis: PythonFileAnalysis) -> list[ParameterCandidate]:
        candidates: list[ParameterCandidate] = []
        for signal in analysis.signals_named("optimizer_call"):
            if signal.detail in OPTIMIZER_SYMBOLS:
                self._add(
                    candidates,
                    "optimizer",
                    signal.detail,
                    analysis,
                    signal.line,
                    signal.quote,
                    "optimizer_call",
                )
                for call in analysis.calls:
                    if call.line != signal.line:
                        continue
                    for key, value in call.keywords.items():
                        canonical = canonical_parameter_name(key)
                        if canonical in {"learning_rate", "weight_decay", "momentum"}:
                            if canonical == "momentum":
                                continue
                            self._add(
                                candidates,
                                canonical,
                                value,
                                analysis,
                                call.line,
                                call.quote,
                                "optimizer_call",
                            )
        for signal in analysis.signals_named("scheduler_call"):
            if signal.detail in SCHEDULER_SYMBOLS:
                self._add(
                    candidates,
                    "scheduler",
                    signal.detail,
                    analysis,
                    signal.line,
                    signal.quote,
                    "scheduler_call",
                )
        for signal in analysis.signals_named("loss_call"):
            if signal.detail in LOSS_SYMBOLS:
                self._add(
                    candidates,
                    "loss_function",
                    signal.detail,
                    analysis,
                    signal.line,
                    signal.quote,
                    "loss_call",
                )
        for signal_name in ("metric_call", "metric_literal"):
            for signal in analysis.signals_named(signal_name):
                canonical_metric = signal.detail
                if not canonical_metric:
                    continue
                self._add(
                    candidates,
                    "metric",
                    canonical_metric,
                    analysis,
                    signal.line,
                    signal.quote,
                    signal_name,
                )
        candidates.extend(self._from_dataset_and_model(analysis))
        return candidates

    def _from_dataset_and_model(self, analysis: PythonFileAnalysis) -> list[ParameterCandidate]:
        """Dataset and model names come from loader calls and module classes."""
        candidates: list[ParameterCandidate] = []
        for signal in analysis.signals_named("dataset_load"):
            if signal.detail not in {"load_dataset", "load_split", "get_dataset", "load_data"}:
                continue
            for call in analysis.calls:
                if call.line != signal.line:
                    continue
                if call.first_string_argument:
                    self._add(
                        candidates,
                        "dataset",
                        call.first_string_argument,
                        analysis,
                        call.line,
                        call.quote,
                        "call_target",
                    )
                break
        for call in analysis.calls:
            if call.symbol == "from_pretrained" and call.positional_count:
                if call.first_string_argument:
                    self._add(
                        candidates,
                        "model",
                        call.first_string_argument,
                        analysis,
                        call.line,
                        call.quote,
                        "call_target",
                    )
        for class_info in analysis.classes:
            bases = {base.split(".")[-1] for base in class_info.bases}
            if bases & {"Module", "Model", "PreTrainedModel", "LightningModule"}:
                self._add(
                    candidates,
                    "model",
                    class_info.name,
                    analysis,
                    class_info.line_start,
                    f"class {class_info.name}",
                    "class_name",
                )
            if class_info.name.endswith(("Dataset", "DataLoader", "Corpus")):
                self._add(
                    candidates,
                    "dataset",
                    class_info.name,
                    analysis,
                    class_info.line_start,
                    f"class {class_info.name}",
                    "class_name",
                )
        return candidates

    @staticmethod
    def _group(
        candidates: list[ParameterCandidate],
    ) -> dict[str, list[ParameterCandidate]]:
        grouped: dict[str, list[ParameterCandidate]] = {}
        for candidate in candidates:
            grouped.setdefault(candidate.name, []).append(candidate)
        for values in grouped.values():
            values.sort(key=lambda item: item.sort_key(), reverse=True)
        return grouped

    def _select_best(self, candidates: list[ParameterCandidate]) -> dict[str, ParameterCandidate]:
        selected: dict[str, ParameterCandidate] = {}
        for name, values in self._group(candidates).items():
            selected[name] = values[0]
        return selected
