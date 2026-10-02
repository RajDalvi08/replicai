"""Configuration for the Code Intelligence module (Part 2).

All values are conservative, deterministic defaults. Repository analysis treats
every input as untrusted, so limits are intentionally small and explicit.
"""

from __future__ import annotations

import os


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_csv(name: str, default: str) -> frozenset[str]:
    raw = os.getenv(name)
    source = raw if raw is not None and raw.strip() else default
    items = {part.strip().lower() for part in source.split(",") if part.strip()}
    return frozenset(items)


class CodeAnalysisSettings:
    """Runtime limits for untrusted repository analysis."""

    def __init__(self) -> None:
        # --- host / protocol policy -------------------------------------
        self.allowed_hosts = _env_csv("CODE_ALLOWED_HOSTS", "github.com")
        self.allowed_schemes = frozenset({"https"})

        # --- git execution policy ---------------------------------------
        self.git_executable = os.getenv("CODE_GIT_EXECUTABLE", "git")
        self.clone_timeout_seconds = _env_float("CODE_CLONE_TIMEOUT_SECONDS", 60.0)
        self.clone_depth = _env_int("CODE_CLONE_DEPTH", 1)

        # --- size / shape limits ----------------------------------------
        self.max_repo_bytes = _env_int("CODE_MAX_REPO_BYTES", 64 * 1024 * 1024)
        self.max_file_count = _env_int("CODE_MAX_FILE_COUNT", 2000)
        self.max_python_file_count = _env_int("CODE_MAX_PYTHON_FILE_COUNT", 400)
        self.max_file_bytes = _env_int("CODE_MAX_FILE_BYTES", 1024 * 1024)
        self.max_depth = _env_int("CODE_MAX_DEPTH", 12)
        self.max_file_line_length = _env_int("CODE_MAX_FILE_LINE_LENGTH", 5000)
        self.max_analysis_seconds = _env_float("CODE_MAX_ANALYSIS_SECONDS", 60.0)
        self.max_dependency_manifest_bytes = _env_int(
            "CODE_MAX_DEPENDENCY_MANIFEST_BYTES", 256 * 1024
        )

        # --- optional LLM assist (never required) -----------------------
        self.llm_enabled = _env_bool("CODE_LLM_ENABLED", True)

    @property
    def max_total_files_walked(self) -> int:
        return self.max_file_count


settings = CodeAnalysisSettings()

# Directory and file names that never contribute to static analysis.
IGNORED_DIRECTORY_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".idea",
        ".vscode",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".nox",
        ".eggs",
        "node_modules",
        "__pycache__",
        ".ipynb_checkpoints",
        ".venv",
        "venv",
        "env",
        "virtualenv",
        "site-packages",
        "dist",
        "build",
        "out",
        "target",
        "vendor",
        "third_party",
        "thirdparty",
        "external",
        "wheels",
        "ckpt",
        "checkpoints",
        "checkpoints_debug",
        "pretrained_checkpoints",
        "saved_models",
        "runs",
        "logs",
        "wandb",
        "mlruns",
        "outputs",
        "artifacts",
        "data",
        "datasets",
        "dataset",
        "samples",
        "assets",
        "media",
        "docs/_build",
        "coverage",
        "htmlcov",
        "eggs",
    }
)

IGNORED_FILE_SUFFIXES: frozenset[str] = frozenset(
    {
        # model weights / checkpoints
        ".pt",
        ".pth",
        ".ckpt",
        ".bin",
        ".onnx",
        ".pb",
        ".h5",
        ".hdf5",
        ".safetensors",
        ".tflite",
        ".params",
        ".msgpack",
        ".npy",
        ".npz",
        # datasets / archives
        ".zip",
        ".tar",
        ".gz",
        ".tgz",
        ".bz2",
        ".xz",
        ".7z",
        ".rar",
        ".parquet",
        ".arrow",
        ".feather",
        ".csv",
        ".tsv",
        ".h5py",
        # documents that are not source
        ".pdf",
        ".docx",
        ".doc",
        ".pptx",
        ".xls",
        ".xlsx",
        ".ico",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".tiff",
        ".webp",
        ".svg",
        ".mp4",
        ".mp3",
        ".wav",
        ".flac",
        ".ttf",
        ".otf",
        ".woff",
        ".woff2",
        ".so",
        ".dylib",
        ".dll",
        ".exe",
        ".o",
        ".a",
        ".class",
        ".jar",
        ".whl",
        ".pyd",
    }
)

DEPENDENCY_MANIFEST_NAMES: frozenset[str] = frozenset(
    {
        "requirements.txt",
        "requirements-dev.txt",
        "requirements_dev.txt",
        "pyproject.toml",
        "environment.yml",
        "environment.yaml",
        "setup.py",
        "setup.cfg",
        "conda.yaml",
        "poetry.lock",
        "uv.lock",
    }
)

DOCUMENTATION_NAMES: frozenset[str] = frozenset(
    {"readme.md", "readme.rst", "readme.txt", "readme", "usage.md", "reproduce.md"}
)
