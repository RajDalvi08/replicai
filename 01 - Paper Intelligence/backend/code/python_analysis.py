"""Static analysis of Python source files using the standard library ``ast``.

The analyzer never imports, executes or evaluates repository code. It parses
text that has already been read from disk, walks the resulting syntax tree and
records facts that can be pointed back at a real file, line and quote.

Only the standard library is used, so the module works without extra
dependencies such as tree-sitter.
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

from backend.code.config import settings
from backend.code.exceptions import CodeAnalysisTimeoutError
from backend.code.utils import RepositoryFile, read_text_file, split_source_lines

logger = logging.getLogger("replicai.code.ast")

MAX_QUOTE_LENGTH = 240

# --------------------------------------------------------------------------- #
# Symbol vocabularies
# --------------------------------------------------------------------------- #
OPTIMIZER_SYMBOLS: frozenset[str] = frozenset(
    {
        "Adam",
        "AdamW",
        "SGD",
        "RMSprop",
        "Adagrad",
        "Adadelta",
        "Adamax",
        "NAdam",
        "RAdam",
        "Rprop",
        "ASGD",
        "LBFGS",
        "SparseAdam",
    }
)

SCHEDULER_SYMBOLS: frozenset[str] = frozenset(
    {
        "StepLR",
        "MultiStepLR",
        "MultiStepLRScheduler",
        "ExponentialLR",
        "CosineAnnealingLR",
        "CosineAnnealingWarmRestarts",
        "ReduceLROnPlateau",
        "OneCycleLR",
        "LambdaLR",
        "CyclicLR",
        "SequentialLR",
        "LinearLR",
        "PolynomialLR",
        "ChainedScheduler",
        "LRScheduler",
    }
)

LOSS_SYMBOLS: frozenset[str] = frozenset(
    {
        "CrossEntropyLoss",
        "MSELoss",
        "L1Loss",
        "SmoothL1Loss",
        "BCELoss",
        "BCEWithLogitsLoss",
        "NLLLoss",
        "KLDivLoss",
        "CTCLoss",
        "MarginRankingLoss",
        "MultiMarginLoss",
        "MultiLabelMarginLoss",
        "MultiLabelSoftMarginLoss",
        "HingeEmbeddingLoss",
        "CosineEmbeddingLoss",
        "TripletMarginLoss",
        "PoissonNLLLoss",
        "GaussianNLLLoss",
        "HuberLoss",
        "CrossEntropyLoss2d",
    }
)

METRIC_CALLABLES: dict[str, str] = {
    "accuracy_score": "accuracy",
    "balanced_accuracy_score": "accuracy",
    "top_k_accuracy_score": "accuracy",
    "precision_score": "precision",
    "recall_score": "recall",
    "f1_score": "f1",
    "fbeta_score": "f1",
    "roc_auc_score": "auc",
    "auc": "auc",
    "mean_squared_error": "mse",
    "mse": "mse",
    "mean_absolute_error": "mae",
    "mae": "mae",
    "root_mean_squared_error": "rmse",
    "rmse": "rmse",
    "r2_score": "r2",
    "log_loss": "log_loss",
    "classification_report": "classification_report",
    "confusion_matrix": "confusion_matrix",
    "bleu": "bleu",
    "bleu_score": "bleu",
    "corpus_bleu": "bleu",
    "sentence_bleu": "bleu",
    "rouge": "rouge",
    "rouge_score": "rouge",
    "rougeL": "rouge",
    "perplexity": "perplexity",
    "word_error_rate": "wer",
    "meteor": "meteor",
}

METRIC_IDENTIFIERS: frozenset[str] = frozenset(
    {
        "accuracy",
        "precision",
        "recall",
        "f1",
        "f1_score",
        "bleu",
        "rouge",
        "perplexity",
        "mse",
        "mae",
        "rmse",
        "auc",
        "exact_match",
    }
)

METRIC_LITERALS: frozenset[str] = frozenset(METRIC_IDENTIFIERS) | {"bleu-4", "rouge-l"}

SEEDING_CALLABLES: frozenset[str] = frozenset(
    {"manual_seed", "seed", "set_seed", "seed_everything"}
)

SEEDING_CALL_TARGETS: frozenset[str] = frozenset({"random", "np", "torch"})

CHECKPOINT_SAVE_CALLABLES: frozenset[str] = frozenset(
    {"save", "save_pretrained", "save_checkpoint", "torch_save", "state_dict"}
)

CHECKPOINT_SAVE_FUNCTIONS: frozenset[str] = frozenset(
    {"save_checkpoint", "save_model", "torch.save", "save_pretrained"}
)

DATA_LOADER_CLASSES: frozenset[str] = frozenset(
    {
        "DataLoader",
        "Dataset",
        "TensorDataset",
        "IterableDataset",
        "ConcatDataset",
        "Subset",
        "load_dataset",
        "load_dataset_from_disk",
        "load_split",
        "read_csv",
        "load_data",
        "get_dataset",
        "build_dataset",
        "make_dataset",
        "create_dataset",
    }
)

TOKENIZER_CALLABLES: frozenset[str] = frozenset(
    {
        "AutoTokenizer",
        "AutoModel",
        "tokenize",
        "encode",
        "encode_plus",
        "batch_encode_plus",
        "from_pretrained",
        "build_tokenizer",
        "preprocess",
    }
)

EVALUATION_FUNCTION_NAMES: frozenset[str] = frozenset(
    {
        "evaluate",
        "eval",
        "evaluation",
        "test",
        "validate",
        "validation",
        "compute_metrics",
        "evaluate_model",
        "run_eval",
        "run_evaluation",
        "assess",
    }
)

TRAINING_FUNCTION_NAMES: frozenset[str] = frozenset(
    {
        "train",
        "train_model",
        "train_step",
        "training_step",
        "fit",
        "run_training",
        "main",
        "train_one_epoch",
        "train_epoch",
    }
)

SEEDING_FUNCTION_NAMES: frozenset[str] = frozenset(
    {"set_seed", "seed_everything", "setup_seed", "fix_seed", "seed_all"}
)

MODEL_BASE_CLASSES: frozenset[str] = frozenset(
    {
        "Module",
        "Model",
        "PreTrainedModel",
        "LightningModule",
        "BaseModel",
        "BaseEstimator",
    }
)

DATASET_CLASS_SUFFIXES: tuple[str, ...] = ("Dataset", "Corpus")


# --------------------------------------------------------------------------- #
# Finding records
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ImportedModule:
    name: str
    alias: str | None
    line: int


@dataclass(frozen=True)
class FunctionInfo:
    name: str
    arguments: tuple[str, ...]
    defaults: tuple[str, ...]
    decorators: tuple[str, ...]
    line_start: int
    line_end: int


@dataclass(frozen=True)
class ClassInfo:
    name: str
    bases: tuple[str, ...]
    line_start: int
    line_end: int


@dataclass(frozen=True)
class CliArgument:
    name: str
    default: Any
    declared_type: str | None
    line: int
    quote: str
    indirect: bool = False


@dataclass(frozen=True)
class ConfigValue:
    """A literal configuration value found in source code."""

    name: str
    value: Any
    line: int
    quote: str
    origin: str
    indirect: bool = False


@dataclass(frozen=True)
class CallUsage:
    symbol: str
    line: int
    quote: str
    keywords: dict[str, Any] = field(default_factory=dict)
    positional_count: int = 0
    first_string_argument: str | None = None


@dataclass(frozen=True)
class SignalUsage:
    """A behavioural signal (loop, seeding, checkpointing, evaluation, ...)."""

    name: str
    line: int
    quote: str
    detail: str | None = None


@dataclass
class PythonFileAnalysis:
    path: str
    lines: list[str] = field(default_factory=list)
    imports: list[ImportedModule] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    cli_arguments: list[CliArgument] = field(default_factory=list)
    config_values: list[ConfigValue] = field(default_factory=list)
    calls: list[CallUsage] = field(default_factory=list)
    signals: list[SignalUsage] = field(default_factory=list)
    module_constants: dict[str, Any] = field(default_factory=dict)
    parse_error: str | None = None

    @property
    def has_main_block(self) -> bool:
        return any(signal.name == "main_block" for signal in self.signals)

    def signals_named(self, name: str) -> list[SignalUsage]:
        return [signal for signal in self.signals if signal.name == name]

    def call_symbols(self) -> set[str]:
        return {call.symbol for call in self.calls}

    def imported_roots(self) -> set[str]:
        return {module.name.split(".")[0] for module in self.imports}

    def has_import_root(self, root: str) -> bool:
        return root in self.imported_roots()

    def quote_at(self, line: int) -> str:
        if 1 <= line <= len(self.lines):
            return self.lines[line - 1].strip()
        return ""


# --------------------------------------------------------------------------- #
# AST helpers
# --------------------------------------------------------------------------- #
def _call_symbol(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Call):
        return _call_symbol(func)
    return ""


def _call_qualifier(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Attribute):
        base = func.value
        if isinstance(base, ast.Name):
            return base.id
        if isinstance(base, ast.Attribute):
            return base.attr
        if isinstance(base, ast.Call):
            return _call_symbol(base)
    return ""


def _literal(node: ast.AST | None) -> tuple[Any, bool]:
    """Return ``(value, ok)`` for literal nodes only. No evaluation, no names."""
    if node is None:
        return None, False
    if isinstance(node, ast.Constant):
        value = node.value
        if isinstance(value, (int, float, str, bool)) or value is None:
            return value, True
        return None, False
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd, ast.Not)):
        operand, ok = _literal(node.operand)
        if not ok or not isinstance(operand, (int, float)):
            return None, False
        if isinstance(node.op, ast.USub):
            return -operand, True
        if isinstance(node.op, ast.UAdd):
            return operand, True
        return not operand, True
    if isinstance(node, ast.List):
        items: list[Any] = []
        for element in node.elts:
            value, ok = _literal(element)
            if not ok:
                return None, False
            items.append(value)
        return items, True
    if isinstance(node, ast.Tuple):
        items = []
        for element in node.elts:
            value, ok = _literal(element)
            if not ok:
                return None, False
            items.append(value)
        return tuple(items), True
    return None, False


class _QuoteFactory:
    """Builds exact, verifiable quotes for AST nodes."""

    def __init__(self, source: str, lines: list[str]) -> None:
        self._source = source
        self._lines = lines

    def for_node(self, node: ast.AST) -> str:
        segment: str | None = None
        try:
            segment = ast.get_source_segment(self._source, node)
        except (ValueError, IndexError):  # pragma: no cover - defensive
            segment = None
        if segment and "\n" not in segment and len(segment) <= MAX_QUOTE_LENGTH:
            return segment.strip()
        lineno = getattr(node, "lineno", 0)
        return self.for_line(lineno)

    def for_line(self, lineno: int) -> str:
        if 1 <= lineno <= len(self._lines):
            return self._lines[lineno - 1].strip()[:MAX_QUOTE_LENGTH]
        return ""

    def for_range(self, start: int, end: int) -> str:
        if not (1 <= start <= len(self._lines)):
            return ""
        stop = min(end, len(self._lines), start + 2)
        joined = " ".join(self._lines[start - 1 : stop]).strip()
        return joined[:MAX_QUOTE_LENGTH]


class _FileVisitor(ast.NodeVisitor):
    """Single-pass collector for one Python module."""

    def __init__(self, analysis: PythonFileAnalysis, source: str, quotes: _QuoteFactory):
        self.analysis = analysis
        self.source = source
        self.quotes = quotes
        self._argparse_parsers: set[str] = set()
        self._in_main_block = False
        self._function_stack: list[str] = []
        self._collect_module_constants()

    # -- module level constants (used for single-hop name resolution) ----- #
    def _collect_module_constants(self) -> None:
        tree = ast.parse(self.source)
        constants: dict[str, Any] = {}
        for statement in tree.body:
            if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
                target = statement.targets[0]
                if isinstance(target, ast.Name):
                    value, ok = _literal(statement.value)
                    if ok:
                        constants[target.id] = value
            elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
                value, ok = _literal(statement.value)
                if ok:
                    constants[statement.target.id] = value
        self.analysis.module_constants = constants

    def _resolve(self, node: ast.AST) -> tuple[Any, bool, bool]:
        """Return ``(value, ok, indirect)`` including one-hop constant lookup."""
        value, ok = _literal(node)
        if ok:
            return value, True, False
        if isinstance(node, ast.Name) and node.id in self.analysis.module_constants:
            return self.analysis.module_constants[node.id], True, True
        return None, False, False

    # -- imports ----------------------------------------------------------- #
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.analysis.imports.append(
                ImportedModule(name=alias.name, alias=alias.asname, line=node.lineno)
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            self.analysis.imports.append(
                ImportedModule(
                    name=f"{module}.{alias.name}" if module else alias.name,
                    alias=alias.asname or alias.name,
                    line=node.lineno,
                )
            )
        self.generic_visit(node)

    # -- functions / classes ------------------------------------------------ #
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._record_function(node)
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._record_function(node)
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def _record_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        arguments = tuple(argument.arg for argument in node.args.args)
        defaults: list[str] = []
        for default in node.args.defaults:
            value, ok = _literal(default)
            if ok:
                defaults.append(repr(value))
            else:
                defaults.append(self.quotes.for_node(default))
        decorators = tuple(self._dotted(decorator) for decorator in node.decorator_list)
        self.analysis.functions.append(
            FunctionInfo(
                name=node.name,
                arguments=arguments,
                defaults=tuple(defaults),
                decorators=decorators,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
            )
        )
        if node.name in TRAINING_FUNCTION_NAMES:
            self._add_signal("training_function", node.lineno, node.name)
        if node.name in EVALUATION_FUNCTION_NAMES:
            self._add_signal("evaluation_function", node.lineno, node.name)
        if node.name in SEEDING_FUNCTION_NAMES:
            self._add_signal("seeding_function", node.lineno, node.name)
        self._collect_typed_cli_parameters(node)

    @staticmethod
    def _dotted(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            base = _FileVisitor._dotted(node.value)
            return f"{base}.{node.attr}" if base else node.attr
        if isinstance(node, ast.Call):
            return _FileVisitor._dotted(node.func)
        if isinstance(node, ast.Subscript):
            return _FileVisitor._dotted(node.value)
        return ""

    def _collect_typed_cli_parameters(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Detect typer-style CLI parameters declared through annotations."""
        annotations: list[ast.AST] = []
        if node.returns is not None:
            annotations.append(node.returns)
        for argument in node.args.args:
            if argument.annotation is not None:
                annotations.append(argument.annotation)

        for annotation in annotations:
            dotted = self._dotted(annotation)
            if "typer" not in dotted.lower():
                continue
            self._add_signal("cli_framework", node.lineno, dotted)
            defaults = list(node.args.defaults)
            offset = len(node.args.args) - len(defaults)
            for index, argument in enumerate(node.args.args):
                if index < offset:
                    continue
                default_node = defaults[index - offset]
                value, ok, indirect = self._resolve(default_node)
                self.analysis.cli_arguments.append(
                    CliArgument(
                        name=argument.arg,
                        default=value if ok else None,
                        declared_type=dotted or None,
                        line=default_node.lineno,
                        quote=self.quotes.for_node(default_node),
                        indirect=indirect,
                    )
                )
            break

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        bases = tuple(self._dotted(base) for base in node.bases)
        self.analysis.classes.append(
            ClassInfo(
                name=node.name,
                bases=bases,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
            )
        )
        base_names = {base.split(".")[-1] for base in bases}
        if base_names & MODEL_BASE_CLASSES:
            self._add_signal("model_class", node.lineno, node.name)
        if node.name.endswith(("Dataset", "Corpus")):
            self._add_signal("dataset_class", node.lineno, node.name)
        self._add_signal("class_definition", node.lineno, node.name)
        self.generic_visit(node)

    # -- assignments -------------------------------------------------------- #
    def visit_Assign(self, node: ast.Assign) -> None:
        value, ok, indirect = self._resolve(node.value)
        quote = self.quotes.for_node(node)
        for target in node.targets:
            name = self._target_name(target)
            if name is None:
                continue
            self.analysis.config_values.append(
                ConfigValue(
                    name=name,
                    value=value if ok else None,
                    line=node.lineno,
                    quote=quote,
                    origin="assignment",
                    indirect=indirect,
                )
            )
        if self._is_argparse_parser(node.value):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self._argparse_parsers.add(target.id)
        self._collect_dict_literals(node.value)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        name = self._target_name(node.target)
        if name is not None:
            if node.value is not None:
                value, ok, indirect = self._resolve(node.value)
            else:
                value, ok, indirect = None, False, False
            self.analysis.config_values.append(
                ConfigValue(
                    name=name,
                    value=value if ok else None,
                    line=node.lineno,
                    quote=self.quotes.for_node(node),
                    origin="assignment",
                    indirect=indirect,
                )
            )
            self._collect_dict_literals(node.value)
        self.generic_visit(node)

    @staticmethod
    def _target_name(target: ast.AST) -> str | None:
        if isinstance(target, ast.Name):
            return target.id
        if isinstance(target, ast.Attribute):
            return target.attr
        return None

    @staticmethod
    def _is_argparse_parser(node: ast.AST | None) -> bool:
        return isinstance(node, ast.Call) and _call_symbol(node) == "ArgumentParser"

    # -- main block --------------------------------------------------------- #
    def visit_If(self, node: ast.If) -> None:
        if self._is_main_guard(node.test):
            self._add_signal("main_block", node.lineno, "__name__ == '__main__'")
            for statement in node.body:
                self.visit(statement)
            for statement in node.orelse:
                self.visit(statement)
            return
        self.generic_visit(node)

    @staticmethod
    def _is_main_guard(test: ast.AST) -> bool:
        if not isinstance(test, ast.Compare):
            return False
        left = test.left
        if not (isinstance(left, ast.Name) and left.id == "__name__"):
            return False
        if len(test.ops) != 1 or len(test.comparators) != 1:
            return False
        comparator = test.comparators[0]
        return isinstance(comparator, ast.Constant) and comparator.value == "__main__"

    # -- calls --------------------------------------------------------------- #
    def visit_Call(self, node: ast.Call) -> None:
        symbol = _call_symbol(node)
        qualifier = _call_qualifier(node)
        keywords: dict[str, Any] = {}
        first_string: str | None = None
        for argument in node.args:
            if (
                first_string is None
                and isinstance(argument, ast.Constant)
                and isinstance(argument.value, str)
            ):
                first_string = argument.value
        for keyword in node.keywords:
            if keyword.arg is None:
                continue
            value, ok, _indirect = self._resolve(keyword.value)
            keywords[keyword.arg] = value if ok else None
            self.analysis.config_values.append(
                ConfigValue(
                    name=keyword.arg,
                    value=value if ok else None,
                    line=keyword.value.lineno or node.lineno,
                    quote=self.quotes.for_node(keyword.value),
                    origin="keyword",
                    indirect=False,
                )
            )
        self.analysis.calls.append(
            CallUsage(
                symbol=symbol,
                line=node.lineno,
                quote=self.quotes.for_node(node),
                keywords=keywords,
                positional_count=len(node.args),
                first_string_argument=first_string,
            )
        )
        self._record_call_signals(node, symbol, qualifier)
        self._record_cli_arguments(node, symbol, qualifier)
        self._record_dict_literals(node)
        self._record_loops(node)
        self.generic_visit(node)

    def _record_call_signals(self, node: ast.Call, symbol: str, qualifier: str) -> None:
        if symbol in OPTIMIZER_SYMBOLS or (
            qualifier in {"optim", "optimize", "torch"} and symbol.endswith("ptim")
        ):
            self._add_signal("optimizer_call", node.lineno, symbol)
        if symbol in SCHEDULER_SYMBOLS:
            self._add_signal("scheduler_call", node.lineno, symbol)
        if symbol in LOSS_SYMBOLS:
            self._add_signal("loss_call", node.lineno, symbol)
        if symbol in METRIC_CALLABLES:
            self._add_signal("metric_call", node.lineno, symbol, METRIC_CALLABLES[symbol])
        if symbol == "add_argument" or symbol in {"option", "argument"}:
            return
        if symbol in SEEDING_CALLABLES and (qualifier in SEEDING_CALL_TARGETS or not qualifier):
            self._add_signal("seeding_call", node.lineno, symbol)
        if symbol in {"train", "eval"} and qualifier in {"model", "module", "net"}:
            self._add_signal(f"{symbol}_mode_call", node.lineno, symbol)
        if symbol in CHECKPOINT_SAVE_CALLABLES and qualifier in {
            "torch",
            "self",
            "model",
            "trainer",
        }:
            self._add_signal("checkpoint_save", node.lineno, symbol)
        if symbol in CHECKPOINT_SAVE_FUNCTIONS or (
            symbol == "save" and qualifier in {"torch", "self", "trainer"}
        ):
            self._add_signal("checkpoint_save", node.lineno, symbol)
        if symbol in DATA_LOADER_CLASSES:
            self._add_signal("dataset_load", node.lineno, symbol)
        if symbol in TOKENIZER_CALLABLES:
            self._add_signal("tokenization", node.lineno, symbol)
        if symbol in {"no_grad", "inference_mode"}:
            self._add_signal("inference_context", node.lineno, symbol)
        if symbol in {"backward"}:
            self._add_signal("backward_pass", node.lineno, symbol)
        if symbol == "step" and qualifier in {"optimizer", "optim", "scheduler", "scaler"}:
            self._add_signal("optimizer_step", node.lineno, symbol)
        if symbol in {"zero_grad"}:
            self._add_signal("optimizer_zero_grad", node.lineno, symbol)

    def _record_cli_arguments(self, node: ast.Call, symbol: str, qualifier: str) -> None:
        if symbol == "add_argument" and qualifier in self._argparse_parsers | {"parser"}:
            self._add_signal("cli_framework", node.lineno, "argparse")
            if not node.args:
                return
            name_node = node.args[0]
            if not isinstance(name_node, ast.Constant) or not isinstance(name_node.value, str):
                return
            name = name_node.value.lstrip("-").replace("-", "_")
            default: Any = None
            declared_type: str | None = None
            indirect = False
            for keyword in node.keywords:
                if keyword.arg == "default":
                    value, ok, indirect = self._resolve(keyword.value)
                    default = value if ok else None
                elif keyword.arg == "type":
                    declared_type = self._dotted(keyword.value) or None
            self.analysis.cli_arguments.append(
                CliArgument(
                    name=name,
                    default=default,
                    declared_type=declared_type,
                    line=node.lineno,
                    quote=self.quotes.for_node(node),
                    indirect=indirect,
                )
            )
            return
        if symbol in {"option", "argument"} and qualifier in {"click", "app", "cli"}:
            self._add_signal("cli_framework", node.lineno, "click")
            if not node.args:
                return
            name_node = node.args[0]
            if not isinstance(name_node, ast.Constant) or not isinstance(name_node.value, str):
                return
            name = name_node.value.lstrip("-").replace("-", "_")
            default = None
            indirect = False
            for keyword in node.keywords:
                if keyword.arg == "default":
                    value, ok, indirect = self._resolve(keyword.value)
                    default = value if ok else None
            self.analysis.cli_arguments.append(
                CliArgument(
                    name=name,
                    default=default,
                    declared_type=None,
                    line=node.lineno,
                    quote=self.quotes.for_node(node),
                    indirect=indirect,
                )
            )

    def _record_dict_literals(self, node: ast.Call) -> None:
        """Capture string-keyed literal entries from dict literals."""
        for argument in list(node.args) + [kw.value for kw in node.keywords]:
            self._collect_dict_literals(argument)

    def _collect_dict_literals(self, node: ast.AST | None) -> None:
        """Capture ``config = {"learning_rate": 0.001}`` style dictionaries."""
        if not isinstance(node, ast.Dict):
            return
        for key_node, value_node in zip(node.keys, node.values):
            if not isinstance(key_node, ast.Constant) or not isinstance(key_node.value, str):
                continue
            value, ok, indirect = self._resolve(value_node)
            self.analysis.config_values.append(
                ConfigValue(
                    name=key_node.value,
                    value=value if ok else None,
                    line=key_node.lineno,
                    quote=self.quotes.for_node(value_node),
                    origin="dict_key",
                    indirect=indirect,
                )
            )

    def _record_loops(self, node: ast.Call) -> None:
        """Detect ``range(epochs)`` style iteration over an epoch count."""
        if node.args and _call_symbol(node) == "range" and len(node.args) == 1:
            argument = node.args[0]
            if isinstance(argument, ast.Name) and "epoch" in argument.id.lower():
                self._add_signal("epoch_loop", node.lineno, argument.id)
            elif isinstance(argument, ast.Attribute) and "epoch" in argument.attr.lower():
                self._add_signal("epoch_loop", node.lineno, argument.attr)

    def visit_For(self, node: ast.For) -> None:
        iterable = node.iter
        if isinstance(iterable, ast.Call) and _call_symbol(iterable) == "range":
            self._add_signal("range_loop", node.lineno, "range")
        self.generic_visit(node)

    # -- string literals ----------------------------------------------------- #
    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str):
            lowered = node.value.strip().lower()
            if lowered in METRIC_LITERALS and len(node.value.strip()) <= 40:
                self._add_signal("metric_literal", node.lineno, node.value.strip())
        self.generic_visit(node)

    # -- helpers -------------------------------------------------------------- #
    def _add_signal(
        self, name: str, line: int, detail: str | None, quote: str | None = None
    ) -> None:
        self.analysis.signals.append(
            SignalUsage(
                name=name,
                line=line,
                quote=quote or self.quotes.for_line(line),
                detail=detail,
            )
        )


def _dedupe_config_values(values: list[ConfigValue]) -> list[ConfigValue]:
    seen: set[tuple[str, int, str, str]] = set()
    output: list[ConfigValue] = []
    for value in values:
        key = (value.name, value.line, value.origin, repr(value.value))
        if key in seen:
            continue
        seen.add(key)
        output.append(value)
    return output


def analyze_python_source(path: str, source: str) -> PythonFileAnalysis:
    """Parse ``source`` and extract static facts. Never executes the module."""
    lines = split_source_lines(source)
    analysis = PythonFileAnalysis(path=path, lines=lines)
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        analysis.parse_error = f"SyntaxError at line {exc.lineno}"
        return analysis
    except (ValueError, RecursionError, MemoryError) as exc:  # pragma: no cover
        analysis.parse_error = type(exc).__name__
        return analysis

    quotes = _QuoteFactory(source, lines)
    visitor = _FileVisitor(analysis, source, quotes)
    try:
        visitor.visit(tree)
    except RecursionError:  # pragma: no cover - pathological input
        analysis.parse_error = "RecursionError"
        return analysis

    analysis.config_values = _dedupe_config_values(analysis.config_values)
    return analysis


def analyze_python_file(repository_file: RepositoryFile) -> PythonFileAnalysis | None:
    """Read and statically analyze one Python file, or return ``None``."""
    source = read_text_file(repository_file.absolute_path)
    if source is None:
        return None
    return analyze_python_source(repository_file.path, source)


def is_python_file(repository_file: RepositoryFile) -> bool:
    if repository_file.suffix == ".py":
        return True
    name = PurePosixPath(repository_file.path).name.lower()
    return name in {"setup.py", "conftest.py", "noxfile.py"}


def python_file_count(files: list[RepositoryFile]) -> int:
    return sum(1 for item in files if is_python_file(item))


def enforce_analysis_deadline(started_at: float) -> None:
    """Raise when the configured total analysis budget is exhausted."""
    import time

    if time.monotonic() - started_at > settings.max_analysis_seconds:
        logger.error("event=code_analysis_timeout")
        raise CodeAnalysisTimeoutError("Repository analysis exceeded the configured time budget.")
